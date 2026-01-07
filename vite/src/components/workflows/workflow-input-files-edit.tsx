import { useAuth } from '@/hooks/useAuth'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, Trash2, Download, FileText } from 'lucide-react'
import {
  listInputFilesApiV1WorkflowsWorkflowIdInputFilesGet,
  uploadInputFileApiV1WorkflowsWorkflowIdInputFilesPost,
  deleteInputFileApiV1WorkflowsWorkflowIdInputFilesFileIdDelete,
  downloadInputFileApiV1WorkflowsWorkflowIdInputFilesFileIdDownloadGet,
  type InputFileResponse,
} from '@/client'
import { apiClient } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { useRef, useState } from 'react'
import { DeleteConfirmationDialog } from '@/components/matrix-detail/dialogs/delete-confirmation-dialog'

interface WorkflowInputFilesEditProps {
  workflowId: number
}

export function WorkflowInputFilesEdit({ workflowId }: WorkflowInputFilesEditProps) {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [fileToDelete, setFileToDelete] = useState<{ id: number; name: string } | null>(null)

  const { data: files = [], isLoading } = useQuery({
    queryKey: ['workflow-input-files', workflowId],
    queryFn: async (): Promise<InputFileResponse[]> => {
      const token = await getToken()
      const response = await listInputFilesApiV1WorkflowsWorkflowIdInputFilesGet({
        path: { workflowId },
        client: apiClient,
        headers: {
          authorization: `Bearer ${token}`,
        },
      })
      return response.data || []
    },
  })

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const token = await getToken()

      const response = await uploadInputFileApiV1WorkflowsWorkflowIdInputFilesPost({
        path: { workflowId },
        body: { file },
        client: apiClient,
        headers: {
          authorization: `Bearer ${token}`,
        },
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-input-files', workflowId] })
      toast.success('File Uploaded', {
        description: 'Input file has been uploaded successfully',
      })
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    },
    onError: (error) => {
      console.error('Error uploading file:', error)
      toast.error('Upload Failed', {
        description: 'Failed to upload input file',
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (fileId: number) => {
      const token = await getToken()
      await deleteInputFileApiV1WorkflowsWorkflowIdInputFilesFileIdDelete({
        path: { workflowId, fileId },
        client: apiClient,
        headers: {
          authorization: `Bearer ${token}`,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-input-files', workflowId] })
      toast.success('File Deleted', {
        description: 'Input file has been deleted successfully',
      })
    },
    onError: (error) => {
      console.error('Error deleting file:', error)
      toast.error('Delete Failed', {
        description: 'Failed to delete input file',
      })
    },
  })

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadMutation.mutate(file)
    }
  }

  const handleDownload = async (file: InputFileResponse) => {
    try {
      const token = await getToken()

      const response = await downloadInputFileApiV1WorkflowsWorkflowIdInputFilesFileIdDownloadGet({
        path: {
          workflowId,
          fileId: file.id,
        },
        headers: {
          authorization: `Bearer ${token}`,
        },
        client: apiClient,
        parseAs: 'blob',
      })

      if (response.error) {
        throw new Error('Download failed')
      }

      const blob = response.data as Blob
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = file.name
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(downloadUrl)
      document.body.removeChild(a)

      toast.success('Download Started', {
        description: file.name,
      })
    } catch (error) {
      console.error('Error downloading file:', error)
      toast.error('Download Failed', {
        description: 'Failed to download file',
      })
    }
  }

  const handleDelete = (fileId: number, fileName: string) => {
    setFileToDelete({ id: fileId, name: fileName })
    setDeleteDialogOpen(true)
  }

  const confirmDelete = () => {
    if (fileToDelete) {
      deleteMutation.mutate(fileToDelete.id)
      setDeleteDialogOpen(false)
      setFileToDelete(null)
    }
  }

  return (
    <>
      <DeleteConfirmationDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={confirmDelete}
        title="Delete Input File"
        description={`Are you sure you want to delete ${fileToDelete?.name}? This action cannot be undone.`}
        isDeleting={deleteMutation.isPending}
      />

      <div className="grid gap-2">
        <Label>Reference Files (Optional)</Label>
        <div className="text-sm text-muted-foreground mb-2">
          Upload templates or style references for the output. Not for source documents—those go in your matrix.
        </div>

        <div className="space-y-2">
        {isLoading ? (
          <div className="text-sm text-muted-foreground">Loading files...</div>
        ) : files.length === 0 ? (
          <div className="text-sm text-muted-foreground">No input files uploaded yet</div>
        ) : (
          <div className="space-y-2">
            {files.map((file) => (
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
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    type="button"
                    onClick={() => handleDownload(file)}
                    style="blocky"
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    type="button"
                    onClick={() => handleDelete(file.id, file.name)}
                    disabled={deleteMutation.isPending}
                    style="blocky"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            className="hidden"
            id={`file-upload-${workflowId}`}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadMutation.isPending}
            style="blocky"
          >
            <Upload className="h-4 w-4 mr-2" />
            {uploadMutation.isPending ? 'Uploading...' : 'Upload File'}
          </Button>
        </div>
      </div>
    </div>
    </>
  )
}
