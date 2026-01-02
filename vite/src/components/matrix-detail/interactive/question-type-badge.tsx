import { Badge } from "@/components/ui/badge"
import { getQuestionTypeIconById, getQuestionTypeBadgeName } from "@/lib/question-types"

const QUESTION_TYPE_COLORS = {
  1: 'bg-blue-100 text-blue-800 border-blue-300', // SHORT_ANSWER
  2: 'bg-green-100 text-green-800 border-green-300', // LONG_ANSWER
  3: 'bg-purple-100 text-purple-800 border-purple-300', // DATE
  4: 'bg-yellow-100 text-yellow-800 border-yellow-300', // CURRENCY
  5: 'bg-orange-100 text-orange-800 border-orange-300', // SINGLE_SELECT
} as const

interface QuestionTypeBadgeProps {
  questionTypeId: number
  className?: string
  showIcon?: boolean
}

export function QuestionTypeBadge({ 
  questionTypeId, 
  className = '', 
  showIcon = true 
}: QuestionTypeBadgeProps) {
  const colorClass = QUESTION_TYPE_COLORS[questionTypeId as keyof typeof QUESTION_TYPE_COLORS] || QUESTION_TYPE_COLORS[1]
  const displayName = getQuestionTypeBadgeName(questionTypeId)
  const Icon = getQuestionTypeIconById(questionTypeId)

  return (
    <Badge variant="outline" className={`${colorClass} text-xs border ${className}`}>
      <div className="flex items-center gap-1">
        {showIcon && <Icon className="h-3 w-3" />}
        {displayName}
      </div>
    </Badge>
  )
}