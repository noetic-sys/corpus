import { DocumentHeaderOverlay } from './document-header-overlay'
import { DocumentHeader } from './document-header'
import { QuestionHeaderOverlay } from './question-header-overlay'
import { QuestionTypeHeader } from './question-type-header'
import { useMatrixContext } from '../context/matrix-context'
import type { EntityRole, EntityType } from '@/client/types.gen'

interface EntityHeaderProps {
  entityId: number
  entityType: EntityType
  entitySetId: number
  role: EntityRole
  className?: string
}

/**
 * Generic entity header that resolves to the appropriate header component
 * based on entity type (question or document).
 *
 * Looks up the entity set member internally to get the member's label,
 * which overrides the entity's own label in this matrix context.
 */
export function EntityHeader({ entityId, entityType, entitySetId, role, className }: EntityHeaderProps) {
  const { matrixId, aiProviders, aiModels, documentMap, questionMap, entitySets } = useMatrixContext()

  // Look up the member to get its ID and label
  const entitySet = entitySets?.find(es => es.id === entitySetId)
  const member = entitySet?.members?.find(m => m.entityId === entityId)

  if (entityType === 'question') {
    const question = questionMap.get(entityId)
    if (!question || !member) return null

    // Use member label (per-matrix context) if available, otherwise fall back to question's label
    const displayLabel = member.label ?? question.label

    return (
      <QuestionHeaderOverlay
        question={question}
        matrixId={matrixId}
        entitySetId={entitySetId}
        memberId={member.id}
        role={role}
        aiProviders={aiProviders}
        aiModels={aiModels}
      >
        <div className={className || "p-2 h-full flex flex-col justify-center"}>
          <QuestionTypeHeader
            questionTypeId={question.questionTypeId}
            questionText={question.questionText}
            label={displayLabel}
            matrixId={matrixId}
          />
        </div>
      </QuestionHeaderOverlay>
    )
  }

  if (entityType === 'document') {
    const document = documentMap.get(entityId)
    if (!document || !member) return null

    // Use member label (per-matrix context) if available, otherwise fall back to document's label
    const displayLabel = member.label ?? document.label

    return (
      <DocumentHeaderOverlay
        document={document}
        matrixId={matrixId}
        entitySetId={entitySetId}
        memberId={member.id}
        role={role}
      >
        <DocumentHeader
          filename={document.document.filename}
          label={displayLabel}
        />
      </DocumentHeaderOverlay>
    )
  }

  return null
}
