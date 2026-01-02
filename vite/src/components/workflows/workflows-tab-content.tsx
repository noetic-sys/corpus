import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import {
  listWorkflowsApiV1WorkspacesWorkspaceIdWorkflowsGet,
  executeWorkflowApiV1WorkflowsWorkflowIdExecutePost,
  deleteWorkflowApiV1WorkflowsWorkflowIdDelete,
  type WorkflowResponse,
  type ExecutionStartedResponse,
} from '@/client'
import { apiClient } from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
} from '@/components/ui/card'
import { toast } from 'sonner'
import { WorkflowCreateDialog } from './workflow-create-dialog'
import { WorkflowExecutionsSheet } from './workflow-executions-sheet'
import { WorkflowCard } from './workflow-card'

interface WorkflowsTabContentProps {
  workspaceId: number
}

export function WorkflowsTabContent({ workspaceId }: WorkflowsTabContentProps) {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  const [executingWorkflowId, setExecutingWorkflowId] = useState<number | null>(null)
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [editingWorkflow, setEditingWorkflow] = useState<WorkflowResponse | null>(null)
  const [executionsSheetWorkflow, setExecutionsSheetWorkflow] = useState<WorkflowResponse | null>(null)

  const { data: workflows = [], isLoading } = useQuery({
    queryKey: ['workflows', workspaceId],
    queryFn: async (): Promise<WorkflowResponse[]> => {
      try {
        const token = await getToken()
        const response = await listWorkflowsApiV1WorkspacesWorkspaceIdWorkflowsGet({
          path: { workspaceId },
          client: apiClient,
          headers: {
            authorization: `Bearer ${token}`,
          },
        })
        return response.data || []
      } catch (error) {
        console.error('Error fetching workflows:', error)
        return []
      }
    },
  })

  const executeMutation = useMutation({
    mutationFn: async (workflowId: number) => {
      const token = await getToken()
      const response = await executeWorkflowApiV1WorkflowsWorkflowIdExecutePost({
        path: { workflowId },
        body: { triggerContext: {} },
        client: apiClient,
        headers: {
          authorization: `Bearer ${token}`,
        },
      })
      return response.data
    },
    onSuccess: (data: ExecutionStartedResponse | undefined) => {
      toast.success('Workflow Execution Started', {
        description: `Execution ID: ${data?.executionId}`,
      })
      setExecutingWorkflowId(null)
      // Invalidate executions to immediately show the new execution
      if (data?.workflowId) {
        queryClient.invalidateQueries({ queryKey: ['workflow-executions', data.workflowId] })
      }
    },
    onError: (error) => {
      console.error('Error executing workflow:', error)
      toast.error('Execution Failed', {
        description: 'Failed to start workflow execution',
      })
      setExecutingWorkflowId(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (workflowId: number) => {
      const token = await getToken()
      await deleteWorkflowApiV1WorkflowsWorkflowIdDelete({
        path: { workflowId },
        client: apiClient,
        headers: {
          authorization: `Bearer ${token}`,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows', workspaceId] })
      toast.success('Workflow Deleted', {
        description: 'Workflow has been deleted successfully',
      })
    },
    onError: (error) => {
      console.error('Error deleting workflow:', error)
      toast.error('Delete Failed', {
        description: 'Failed to delete workflow',
      })
    },
  })

  const handleExecute = (workflowId: number) => {
    setExecutingWorkflowId(workflowId)
    executeMutation.mutate(workflowId)
  }

  const handleDelete = (workflowId: number) => {
    if (confirm('Are you sure you want to delete this workflow?')) {
      deleteMutation.mutate(workflowId)
    }
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-full">Loading workflows...</div>
  }

  return (
    <>
      <div className="h-full overflow-auto p-6">
        <div className="max-w-6xl mx-auto space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold tracking-tight">Workflows</h2>
              <p className="text-muted-foreground">
                Manage and execute your automated workflows
              </p>
            </div>
            <Button onClick={() => setIsCreateDialogOpen(true)} style="blocky">
              <Plus className="h-4 w-4 mr-2" />
              Create Workflow
            </Button>
          </div>

        {workflows.length === 0 ? (
          <Card variant="blocky">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <p className="text-muted-foreground mb-4">No workflows created yet</p>
              <Button onClick={() => setIsCreateDialogOpen(true)} style="blocky">
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Workflow
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {workflows.map((workflow) => (
              <WorkflowCard
                key={workflow.id}
                workflow={workflow}
                isExecuting={executingWorkflowId === workflow.id}
                onExecute={() => handleExecute(workflow.id)}
                onViewExecutions={() => setExecutionsSheetWorkflow(workflow)}
                onEdit={() => setEditingWorkflow(workflow)}
                onDelete={() => handleDelete(workflow.id)}
              />
            ))}
          </div>
        )}
        </div>
      </div>

      <WorkflowCreateDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        workspaceId={workspaceId}
      />

      {editingWorkflow && (
        <WorkflowCreateDialog
          open={true}
          onOpenChange={(open) => !open && setEditingWorkflow(null)}
          workspaceId={workspaceId}
          editWorkflow={editingWorkflow}
        />
      )}

      {executionsSheetWorkflow && (
        <WorkflowExecutionsSheet
          workflowId={executionsSheetWorkflow.id}
          workflowName={executionsSheetWorkflow.name}
          open={true}
          onOpenChange={(open) => !open && setExecutionsSheetWorkflow(null)}
        />
      )}
    </>
  )
}
