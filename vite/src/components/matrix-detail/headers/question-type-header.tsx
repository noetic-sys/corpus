import { getQuestionTypeIconById } from "@/lib/question-types"
import { useTemplateVariables } from "../hooks/use-template-variables"
import { formatQuestionTextForDisplay } from "../utils/document-placeholder-display"

interface QuestionTypeHeaderProps {
  questionTypeId: number
  questionText: string
  label?: string | null
  className?: string
  matrixId?: number
}

export function QuestionTypeHeader({ 
  questionTypeId, 
  questionText,
  label,
  className = '',
  matrixId
}: QuestionTypeHeaderProps) {
  const Icon = getQuestionTypeIconById(questionTypeId)
  const { data: templateVariables = [] } = useTemplateVariables(matrixId || 0)
  
  // Resolve template variables in question text (handles ID-based patterns)
  const resolveTemplateVariables = (text: string) => {
    if (!matrixId) return text
    let resolvedText = text
    templateVariables.forEach(variable => {
      // Replace ID-based pattern: #{{123}} with the actual value
      const idPattern = `#{{${variable.id}}}`
      resolvedText = resolvedText.replace(
        new RegExp(idPattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), 
        variable.value
      )
    })
    return resolvedText
  }

  const displayText = label || formatQuestionTextForDisplay(resolveTemplateVariables(questionText))

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        <span className="text-xs font-medium break-words whitespace-normal">
          {displayText}
        </span>
      </div>
    </div>
  )
}