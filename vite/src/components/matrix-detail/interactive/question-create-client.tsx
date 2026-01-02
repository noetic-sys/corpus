import { QuestionCreateInline } from './question-create-inline'
import { TableHead } from "@/components/ui/table"
import type { QuestionResponse, AiProviderResponse, AiModelResponse } from '@/client'
import {useMatrixContext} from "@/components/matrix-detail";

interface QuestionCreateClientProps {
  matrixId: number
  entitySetId: number
  aiProviders: AiProviderResponse[]
  aiModels: AiModelResponse[]
}

export function QuestionCreateClient({ matrixId, entitySetId, aiProviders, aiModels }: QuestionCreateClientProps) {
  const { triggerRefresh } = useMatrixContext()

  const handleQuestionCreated = (question: QuestionResponse) => {
    console.log('Question created:', question)
    // Only refresh questions, entity sets, and tiles - documents and matrix unchanged
    triggerRefresh(matrixId, { questions: true, entitySets: true, tiles: true, stats: true })
  }

  return (
    <TableHead variant="blocky" className={`w-16 p-0 transition-all duration-200 border-b border-border bg-muted h-20`}>
      <QuestionCreateInline
        matrixId={matrixId}
        entitySetId={entitySetId}
        onQuestionCreated={handleQuestionCreated}
        className="border-0"
        aiProviders={aiProviders}
        aiModels={aiModels}
      />
    </TableHead>
  )
}