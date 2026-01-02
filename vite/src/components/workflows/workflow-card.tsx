import { Play, Trash2, Edit, History } from 'lucide-react'
import { type WorkflowResponse } from '@/client'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

interface WorkflowCardProps {
  workflow: WorkflowResponse
  isExecuting: boolean
  onExecute: () => void
  onViewExecutions: () => void
  onEdit: () => void
  onDelete: () => void
}

export function WorkflowCard({
  workflow,
  isExecuting,
  onExecute,
  onViewExecutions,
  onEdit,
  onDelete,
}: WorkflowCardProps) {
  return (
    <Card className="flex flex-col" variant="blocky">
      <CardHeader>
        <div className="space-y-1">
          <CardTitle className="text-lg">{workflow.name}</CardTitle>
          {workflow.description && (
            <CardDescription className="line-clamp-2">
              {workflow.description}
            </CardDescription>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 space-y-4">
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Trigger:</span>
            <span className="font-medium">{workflow.triggerType}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Output:</span>
            <span className="font-medium">{workflow.outputType}</span>
          </div>
        </div>

        <div className="space-y-2 pt-4 border-t">
          <Button
            size="sm"
            className="w-full"
            onClick={onExecute}
            disabled={isExecuting}
            style="blocky"
          >
            <Play className="h-4 w-4 mr-2" />
            {isExecuting ? 'Starting...' : 'Execute'}
          </Button>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              className="flex-1"
              onClick={onViewExecutions}
              style="blocky"
            >
              <History className="h-4 w-4 mr-2" />
              Executions
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={onEdit}
              style="blocky"
            >
              <Edit className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={onDelete}
              style="blocky"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
