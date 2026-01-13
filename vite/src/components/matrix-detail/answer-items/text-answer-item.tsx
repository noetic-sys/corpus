import { cn } from '@/lib/utils'
import { processTextWithCitations } from './citation-utils'
import { useMatrixContext } from '../context/matrix-context'
import type { AnswerItemRendererProps } from './base-answer-item'

export function TextAnswerItem({ answerData, className, citations, cellId }: AnswerItemRendererProps) {
  const { documentMap } = useMatrixContext()
  const textValue = 'value' in answerData ? answerData.value : String(answerData)

  // Process both citations [[cite:N]] and document references [document:ID]
  const processedContent = citations && cellId ?
    processTextWithCitations(textValue, citations, cellId, documentMap) :
    processTextWithCitations(textValue, [], cellId || 0, documentMap)

  return (
    <div className={cn("text-xs text-text-secondary break-words whitespace-normal flex-1", className)}>
      {processedContent}
    </div>
  )
}