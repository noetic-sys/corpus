import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import {
  createWorkflowApiV1WorkflowsPost,
  updateWorkflowApiV1WorkflowsWorkflowIdPatch,
  uploadInputFileApiV1WorkflowsWorkflowIdInputFilesPost,
  type WorkflowCreate,
  type WorkflowUpdate,
  type WorkflowResponse,
} from '@/client'
import { apiClient } from '@/lib/api'
import { toast } from 'sonner'
import { WorkflowInputFiles } from './workflow-input-files'
import { WorkflowInputFilesEdit } from './workflow-input-files-edit'

interface WorkflowCreateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  workspaceId: number
  editWorkflow?: WorkflowResponse
}

export function WorkflowCreateDialog({
  open,
  onOpenChange,
  workspaceId,
  editWorkflow,
}: WorkflowCreateDialogProps) {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  const isEditing = !!editWorkflow

  const [name, setName] = useState(editWorkflow?.name || '')
  const [description, setDescription] = useState(editWorkflow?.description || '')
  const [triggerType, setTriggerType] = useState<string>(editWorkflow?.triggerType || 'manual')
  const [outputType, setOutputType] = useState<string>(editWorkflow?.outputType || 'excel')
  const [inputFiles, setInputFiles] = useState<File[]>([])

  const createMutation = useMutation({
    mutationFn: async (workflow: WorkflowCreate) => {
      const token = await getToken()

      // Step 1: Create workflow
      const response = await createWorkflowApiV1WorkflowsPost({
        body: workflow,
        client: apiClient,
        headers: {
          authorization: `Bearer ${token}`,
        },
      })

      const createdWorkflow = response.data
      if (!createdWorkflow) {
        throw new Error('Failed to create workflow')
      }

      // Step 2: Upload input files if any
      if (inputFiles.length > 0) {
        for (const file of inputFiles) {
          await uploadInputFileApiV1WorkflowsWorkflowIdInputFilesPost({
            path: { workflowId: createdWorkflow.id },
            body: { file },
            client: apiClient,
            headers: {
              authorization: `Bearer ${token}`,
            },
          })
        }
      }

      return createdWorkflow
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
      const fileCount = inputFiles.length
      toast.success('Workflow Created', {
        description: fileCount > 0
          ? `Workflow created with ${fileCount} input file${fileCount > 1 ? 's' : ''}`
          : 'Your workflow has been created successfully',
      })
      onOpenChange(false)
      resetForm()
    },
    onError: (error) => {
      console.error('Error creating workflow:', error)
      toast.error('Create Failed', {
        description: 'Failed to create workflow',
      })
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, workflow }: { id: number; workflow: WorkflowUpdate }) => {
      const token = await getToken()
      const response = await updateWorkflowApiV1WorkflowsWorkflowIdPatch({
        path: { workflowId: id },
        body: workflow,
        client: apiClient,
        headers: {
          authorization: `Bearer ${token}`,
        },
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
      toast.success('Workflow Updated', {
        description: 'Your workflow has been updated successfully',
      })
      onOpenChange(false)
    },
    onError: (error) => {
      console.error('Error updating workflow:', error)
      toast.error('Update Failed', {
        description: 'Failed to update workflow',
      })
    },
  })

  const resetForm = () => {
    setName('')
    setDescription('')
    setTriggerType('manual')
    setOutputType('excel')
    setInputFiles([])
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim()) {
      toast.error('Validation Error', {
        description: 'Workflow name is required',
      })
      return
    }

    if (isEditing && editWorkflow) {
      const workflow: WorkflowUpdate = {
        name: name.trim(),
        description: description.trim() || undefined,
        triggerType: triggerType,
        outputType: outputType,
      }
      updateMutation.mutate({ id: editWorkflow.id, workflow })
    } else {
      const workflow: WorkflowCreate = {
        name: name.trim(),
        description: description.trim() || undefined,
        triggerType: triggerType,
        workspaceId: workspaceId,
        outputType: outputType,
      }
      createMutation.mutate(workflow)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]" variant="blocky">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{isEditing ? 'Edit Workflow' : 'Create Workflow'}</DialogTitle>
            <DialogDescription>
              {isEditing
                ? 'Update your workflow configuration'
                : 'Create a new automated workflow for your workspace'}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Weekly Report Generator"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="description">Instructions</Label>
              <p className="text-sm text-muted-foreground">
                Tell the agent what to do. It will have access to your matrix data.
              </p>
              <Textarea
                id="description"
                placeholder="e.g., Generate a summary report comparing payment terms across all contracts..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="trigger">Trigger Type</Label>
              <Select value={triggerType} onValueChange={setTriggerType}>
                <SelectTrigger id="trigger">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="manual">Manual</SelectItem>
                  <SelectItem value="scheduled">Scheduled</SelectItem>
                  <SelectItem value="webhook">Webhook</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="output">Output Type</Label>
              <Select value={outputType} onValueChange={setOutputType}>
                <SelectTrigger id="output">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="excel">Excel (.xlsx)</SelectItem>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="docx">Word Document (.docx)</SelectItem>
                  <SelectItem value="csv">CSV</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Separator className="my-2" />
            {isEditing && editWorkflow ? (
              <WorkflowInputFilesEdit workflowId={editWorkflow.id} />
            ) : (
              <WorkflowInputFiles onFilesChange={setInputFiles} />
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                onOpenChange(false)
                resetForm()
              }}
              style="blocky"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              style="blocky"
            >
              {isEditing
                ? updateMutation.isPending
                  ? 'Updating...'
                  : 'Update Workflow'
                : createMutation.isPending
                  ? 'Creating...'
                  : 'Create Workflow'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
