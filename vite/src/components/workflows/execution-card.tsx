import { useAuth } from "@/hooks/useAuth";
import { useQuery } from "@tanstack/react-query";
import {
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Download,
  FileText,
} from "lucide-react";
import {
  listExecutionFilesApiV1WorkflowsWorkflowIdExecutionsExecutionIdFilesGet,
  downloadExecutionFileApiV1WorkflowsWorkflowIdExecutionsExecutionIdFilesFileIdDownloadGet,
  type ExecutionResponse,
  type ExecutionFileResponse,
} from "@/client";
import { apiClient } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner";

interface ExecutionCardProps {
  execution: ExecutionResponse;
  workflowId: number;
}

export function ExecutionCard({ execution, workflowId }: ExecutionCardProps) {
  const { getToken } = useAuth();

  const { data: files = [] } = useQuery({
    queryKey: ["execution-files", execution.id],
    queryFn: async (): Promise<ExecutionFileResponse[]> => {
      const token = await getToken();
      const response =
        await listExecutionFilesApiV1WorkflowsWorkflowIdExecutionsExecutionIdFilesGet(
          {
            path: {
              workflowId,
              executionId: execution.id,
            },
            client: apiClient,
            headers: {
              authorization: `Bearer ${token}`,
            },
          },
        );
      return response.data || [];
    },
    enabled: execution.status === "completed",
    refetchInterval: false,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  });

  const handleDownload = async (file: ExecutionFileResponse) => {
    try {
      const token = await getToken();

      const response =
        await downloadExecutionFileApiV1WorkflowsWorkflowIdExecutionsExecutionIdFilesFileIdDownloadGet(
          {
            path: {
              workflowId,
              executionId: execution.id,
              fileId: file.id,
            },
            headers: {
              authorization: `Bearer ${token}`,
            },
            client: apiClient,
            parseAs: "blob",
          },
        );

      if (response.error) {
        throw new Error("Download failed");
      }

      const blob = response.data as Blob;
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = file.name;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(a);

      toast.success("Download Started", {
        description: file.name,
      });
    } catch (error) {
      console.error("Error downloading file:", error);
      toast.error("Download Failed", {
        description: "Failed to download file",
      });
    }
  };

  const getStatusIcon = () => {
    switch (execution.status) {
      case "completed":
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case "failed":
        return <XCircle className="h-5 w-5 text-red-500" />;
      case "running":
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusBadge = () => {
    const variants: Record<string, "default" | "secondary" | "destructive"> = {
      completed: "default",
      failed: "destructive",
      running: "secondary",
      pending: "secondary",
    };
    return (
      <Badge variant={variants[execution.status] || "secondary"} style="blocky">
        {execution.status}
      </Badge>
    );
  };

  const formatDuration = () => {
    if (!execution.completedAt) return null;
    const start = new Date(execution.startedAt).getTime();
    const end = new Date(execution.completedAt).getTime();
    const durationMs = end - start;
    const seconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(seconds / 60);
    if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    }
    return `${seconds}s`;
  };

  const outputFiles = files.filter((f) => f.fileType === "output");

  return (
    <Card variant="blocky">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {getStatusIcon()}
            <div>
              <p className="font-medium">Execution #{execution.id}</p>
              <p className="text-sm text-muted-foreground">
                {new Date(execution.startedAt).toLocaleString()}
              </p>
            </div>
          </div>
          {getStatusBadge()}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {execution.completedAt && (
          <div className="text-sm text-muted-foreground">
            Duration: {formatDuration()}
          </div>
        )}

        {execution.errorMessage && (
          <Alert variant="destructive">
            <AlertDescription>{execution.errorMessage}</AlertDescription>
          </Alert>
        )}

        {outputFiles.length > 0 && (
          <>
            <Separator />
            <div className="space-y-2">
              <p className="text-sm font-medium">Output Files</p>
              {outputFiles.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center justify-between rounded-md border p-2"
                >
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">{file.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {(file.fileSize / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDownload(file)}
                    style="blocky"
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
