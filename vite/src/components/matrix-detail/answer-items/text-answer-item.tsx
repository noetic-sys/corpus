import { cn } from '@/lib/utils'
import { processTextWithCitations } from './citation-utils'
import { useMatrixContext } from '../context/matrix-context'
import type { AnswerItemRendererProps } from './base-answer-item'

// Filter out answer not found placeholder that may leak from AI responses
const ANSWER_NOT_FOUND_PATTERN = /<<ANSWER_NOT_FOUND>>/gi

function isAnswerNotFound(text: string): boolean {
  return ANSWER_NOT_FOUND_PATTERN.test(text.trim())
}

export function TextAnswerItem({ answerData, className, citations, cellId }: AnswerItemRendererProps) {
  const { documentMap } = useMatrixContext()
  const textValue = 'value' in answerData ? answerData.value : String(answerData)

  // Check if the answer is just the ANSWER_NOT_FOUND placeholder
  if (isAnswerNotFound(textValue)) {
    return (
      <div className={cn("text-xs text-text-tertiary italic break-words whitespace-normal flex-1", className)}>
        Answer not found in document
      </div>
    )
  }

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