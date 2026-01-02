import { QuestionCreateClient } from './question-create-client'
import { DocumentUploadClient } from './document-upload-client'
import { useMatrixContext } from '../context/matrix-context'
import type { EntityType } from '@/client/types.gen'

interface EntitySetAddButtonProps {
  entityType: EntityType
  entitySetId: number
}

/**
 * Generic add button that resolves to the appropriate create/upload component
 * based on entity type (question or document).
 */
export function EntitySetAddButton({ entityType, entitySetId }: EntitySetAddButtonProps) {
  const { matrixId, aiProviders, aiModels } = useMatrixContext()

  if (entityType === 'question') {
    return (
      <QuestionCreateClient
        matrixId={matrixId}
        entitySetId={entitySetId}
        aiProviders={aiProviders}
        aiModels={aiModels}
      />
    )
  }

  if (entityType === 'document') {
    return (
      <DocumentUploadClient
        matrixId={matrixId}
        entitySetId={entitySetId}
      />
    )
  }

  return null
}
