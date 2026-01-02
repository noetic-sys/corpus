import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Save } from 'lucide-react'

interface EditingVariable {
  id?: number
  templateString: string
  value: string
  isNew?: boolean
}

interface TemplateVariableFormProps {
  variable: EditingVariable
  index: number
  isSubmitting: boolean
  onUpdate: (index: number, field: keyof EditingVariable, value: string) => void
  onSave: (variable: EditingVariable, index: number) => void
  onCancel: (index: number) => void
}

export function TemplateVariableForm({
  variable,
  index,
  isSubmitting,
  onUpdate,
  onSave,
  onCancel
}: TemplateVariableFormProps) {
  const isValid = variable.templateString.trim() && variable.value.trim()
  const saveButtonText = variable.isNew ? 'Create' : 'Save'
  const cardClassName = variable.isNew ? 'p-4 border-dashed' : 'p-4'

  return (
    <Card variant="blocky" className={`${cardClassName} border-[1px]`}>
      <div className="space-y-3">
        <div className="flex gap-2">
          <div className="flex-1">
            <label className="text-xs text-muted-foreground mb-1 block">
              Variable Name
            </label>
            <Input
              variant="blocky"
              placeholder="variableName"
              value={variable.templateString}
              onChange={(e) => onUpdate(index, 'templateString', e.target.value)}
              className="text-sm border-[1px]"
              disabled={isSubmitting}
            />
          </div>
          <div className="flex-1">
            <label className="text-xs text-muted-foreground mb-1 block">
              Value
            </label>
            <Input
              variant="blocky"
              placeholder="Variable value"
              value={variable.value}
              onChange={(e) => onUpdate(index, 'value', e.target.value)}
              className="text-sm border-[1px]"
              disabled={isSubmitting}
            />
          </div>
        </div>
        <div className="flex gap-2">
          <Button 
            size="sm" 
            style="blocky"
            onClick={() => onSave(variable, index)}
            disabled={isSubmitting || !isValid}
            className="gap-1 border-[1px]"
          >
            <Save className="h-3 w-3" />
            {saveButtonText}
          </Button>
          <Button 
            size="sm" 
            variant="outline"
            style="blocky"
            onClick={() => onCancel(index)}
            disabled={isSubmitting}
            className="border-[1px]"
          >
            Cancel
          </Button>
        </div>
      </div>
    </Card>
  )
}