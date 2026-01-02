import { Variable } from 'lucide-react'

interface TemplateVariablesLoadingStateProps {
  className?: string
}

export function TemplateVariablesLoadingState({ className = '' }: TemplateVariablesLoadingStateProps) {
  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center gap-2">
        <Variable className="h-5 w-5" />
        <h3 className="text-lg font-semibold">Template Variables</h3>
      </div>
      <div className="space-y-2">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-16 bg-muted/20 rounded animate-pulse" />
        ))}
      </div>
    </div>
  )
}