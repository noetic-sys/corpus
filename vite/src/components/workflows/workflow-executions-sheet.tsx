import { useAuth } from "@/hooks/useAuth";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import {
  listExecutionsApiV1WorkflowsWorkflowIdExecutionsGet,
  type ExecutionResponse,
} from "@/client";
import { apiClient } from "@/lib/api";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ExecutionCard } from "./execution-card";

interface WorkflowExecutionsSheetProps {
  workflowId: number;
  workflowName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function WorkflowExecutionsSheet({
  workflowId,
  workflowName,
  open,
  onOpenChange,
}: WorkflowExecutionsSheetProps) {
  const { getToken } = useAuth();

  const { data: executions = [], isLoading } = useQuery({
    queryKey: ["workflow-executions", workflowId],
    queryFn: async (): Promise<ExecutionResponse[]> => {
      const token = await getToken();
      const response =
        await listExecutionsApiV1WorkflowsWorkflowIdExecutionsGet({
          path: { workflowId },
          client: apiClient,
          headers: {
            authorization: `Bearer ${token}`,
          },
        });
      return response.data || [];
    },
    enabled: open,
    // Only poll if there are running executions
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasRunning =
        Array.isArray(data) &&
        data.some((e) => e.status === "running" || e.status === "pending");
      return hasRunning ? 5000 : false;
    },
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>Executions - {workflowName}</SheetTitle>
          <SheetDescription>
            View execution history and download generated files
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-8rem)] mt-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : executions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <p className="text-muted-foreground">No executions yet</p>
              <p className="text-sm text-muted-foreground mt-2">
                Execute this workflow to see results here
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {executions.map((execution) => (
                <ExecutionCard
                  key={execution.id}
                  execution={execution}
                  workflowId={workflowId}
                />
              ))}
            </div>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

