import { type QuestionResponse, type AiProviderResponse, type AiModelResponse } from '@/client'
import { QuestionFormBase } from './question-form-base'
import type { Question } from '../types'

interface QuestionOption {
  value: string
}

interface QuestionEditFormProps {
  matrixId: number
  question: Question
  questionEntitySetId?: number
  existingOptions?: QuestionOption[]
  onQuestionUpdated: (question: QuestionResponse) => void
  onCancel: () => void
  className?: string
  aiProviders?: AiProviderResponse[]
  aiModels?: AiModelResponse[]
}

export function QuestionEditForm({
  matrixId,
  question,
  questionEntitySetId,
  existingOptions = [],
  onQuestionUpdated,
  onCancel,
  className = '',
  aiProviders = [],
  aiModels = []
}: QuestionEditFormProps) {
  return (
    <QuestionFormBase
      matrixId={matrixId}
      mode="edit"
      question={question}
      questionEntitySetId={questionEntitySetId}
      existingOptions={existingOptions}
      onSuccess={onQuestionUpdated}
      onCancel={onCancel}
      className={className}
      aiProviders={aiProviders}
      aiModels={aiModels}
    />
  )
}