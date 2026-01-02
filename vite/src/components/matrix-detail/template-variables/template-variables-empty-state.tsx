import { Variable } from 'lucide-react'

export function TemplateVariablesEmptyState() {
  return (
    <div className="text-center py-8 text-muted-foreground">
      <Variable className="h-8 w-8 mx-auto mb-2 opacity-50" />
      <p className="text-sm">No template variables defined</p>
      <p className="text-xs mt-1">Add variables to use in your questions with ${'${{variableName}}'} syntax</p>
    </div>
  )
}