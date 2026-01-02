import { type QuestionResponse, type AiProviderResponse, type AiModelResponse } from '@/client'
import { QuestionFormBase } from './question-form-base'

interface QuestionCreateFormProps {
  matrixId: number
  entitySetId: number
  onQuestionCreated: (question: QuestionResponse) => void
  onCancel: () => void
  className?: string
  aiProviders?: AiProviderResponse[]
  aiModels?: AiModelResponse[]
}

export function QuestionCreateForm({
  matrixId,
  entitySetId,
  onQuestionCreated,
  onCancel,
  className = '',
  aiProviders = [],
  aiModels = []
}: QuestionCreateFormProps) {
  return (
    <QuestionFormBase
      matrixId={matrixId}
      mode="create"
      questionEntitySetId={entitySetId}
      onSuccess={onQuestionCreated}
      onCancel={onCancel}
      className={className}
      aiProviders={aiProviders}
      aiModels={aiModels}
    />
  )
}