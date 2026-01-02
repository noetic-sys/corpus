import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Edit2, X } from 'lucide-react'
import type { MatrixTemplateVariableResponse } from '@/client'

interface TemplateVariableCardProps {
  variable: MatrixTemplateVariableResponse
  isSubmitting: boolean
  onEdit: (variable: MatrixTemplateVariableResponse) => void
  onDelete: (variableId: number, templateString: string) => void
}

export function TemplateVariableCard({ 
  variable, 
  isSubmitting, 
  onEdit, 
  onDelete 
}: TemplateVariableCardProps) {
  return (
    <Card variant="blocky" className="p-4 border-[1px]">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <code className="text-sm rounded-none">
              ${`{{${variable.templateString}}}`}
            </code>
            <span className="text-muted-foreground">→</span>
            <span className="text-sm">{variable.value}</span>
          </div>
        </div>
        <div className="flex gap-1">
          <Button
            size="sm"
            variant="ghost"
            style="blocky"
            onClick={() => onEdit(variable)}
            disabled={isSubmitting}
            className="h-8 w-8 p-0 border-[1px]"
          >
            <Edit2 className="h-3 w-3" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            style="blocky"
            onClick={() => onDelete(variable.id, variable.templateString)}
            disabled={isSubmitting}
            className="h-8 w-8 p-0 text-destructive hover:text-destructive border-[1px]"
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </Card>
  )
}