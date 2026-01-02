import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { AnswerItemRenderer } from "../answer-items/answer-item-renderer"
import type { MatrixCellType } from '../types'
import { FileText, MessageSquare } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { useMatrixContext } from '../context/matrix-context'

interface MatrixCellDetailSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  cell: MatrixCellType
}

export function MatrixCellDetailSheet({ open, onOpenChange, cell }: MatrixCellDetailSheetProps) {
  const { questionMap, documentMap } = useMatrixContext()
  const currentAnswer = cell.currentAnswer

  if (!currentAnswer) {
    return null
  }

  const { answers, answerFound, questionTypeId, confidence } = currentAnswer
  const confidencePercent = Math.round((confidence ?? 1.0) * 100)

  // Find the question entity ref from the cell's entity refs
  const questionRef = cell.entityRefs?.find(ref => ref.role === 'question')
  const questionId = questionRef?.entityId

  // Look up the question from the matrix context
  const question = questionId ? questionMap.get(questionId) : undefined
  const rawQuestionText = question?.questionText || 'Question not found'

  // Resolve template variables in question text
  const resolveTemplateVariables = (text: string) => {
    let resolvedText = text

    // Find all entity refs that might be template variables (LEFT, RIGHT, DOCUMENT, etc.)
    cell.entityRefs?.forEach(ref => {
      if (ref.role === 'left' || ref.role === 'right' || ref.role === 'document') {
        const doc = documentMap.get(ref.entityId)
        if (doc) {
          const rolePlaceholder = `@{{${ref.role.toUpperCase()}}}`
          resolvedText = resolvedText.replace(
            new RegExp(rolePlaceholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'),
            doc.document.filename
          )
        }
      }
    })

    return resolvedText
  }

  const questionText = resolveTemplateVariables(rawQuestionText)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[600px] sm:w-[700px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Cell Details
          </SheetTitle>
        </SheetHeader>

        <div className="mt-4 space-y-4 overflow-y-auto h-[calc(100vh-100px)]">
          {/* Question */}
          <div>
            <div className="text-xs font-medium text-text-tertiary uppercase tracking-wide mb-2">Question</div>
            <div className="text-sm bg-surface p-2 border-[1px] border-border">
              {questionText}
            </div>
          </div>

          {/* Answer */}
          {answerFound && answers && answers.length > 0 ? (
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs font-medium text-text-tertiary uppercase tracking-wide">
                  {answers.length === 1 ? 'Answer' : `Answers (${answers.length})`}
                </div>
                <Badge
                  variant={confidencePercent >= 70 ? "default" : "secondary"}
                  style="blocky"
                  className="text-xs"
                >
                  {confidencePercent}% Confidence
                </Badge>
              </div>
              <div className="space-y-3">
                {answers.map((answer, index) => (
                  <div key={index}>
                    <div className="bg-surface p-2 border-[1px] border-border">
                      {answers.length > 1 && (
                        <Badge variant="default" style="blocky" className="text-xs mb-2">
                          Answer {index + 1}
                        </Badge>
                      )}
                      <div className="text-sm">
                        <AnswerItemRenderer
                          answerData={answer.answerData}
                          questionTypeId={questionTypeId}
                          citations={answer.citations}
                          cellId={cell.id}
                        />
                      </div>
                    </div>

                    {/* Citations */}
                    {answer.citations && answer.citations.length > 0 && (
                      <div className="mt-3 border-t-[1px] border-border pt-3">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-2">
                          <FileText className="h-3 w-3" />
                          References
                        </div>
                        <div className="space-y-2">
                          {answer.citations.map((citation, citationIndex) => {
                            const citationDoc = documentMap.get(citation.documentId)
                            const documentName = citationDoc?.document.filename || 'Unknown document'

                            return (
                              <div key={citationIndex} className="flex gap-2 text-xs">
                                <span className="text-text-tertiary font-mono flex-shrink-0">[{citation.citationOrder}]</span>
                                <div className="flex-1">
                                  <span className="text-text-secondary italic">"{citation.quoteText}"</span>
                                  <div className="mt-1">
                                    <span className="text-text-tertiary">— {documentName}</span>
                                  </div>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <div className="text-xs font-medium text-text-tertiary uppercase tracking-wide mb-2">Answer</div>
              <div className="bg-surface p-2 border-[1px] border-border text-center">
                <p className="text-sm text-text-tertiary">Answer not found in document</p>
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
