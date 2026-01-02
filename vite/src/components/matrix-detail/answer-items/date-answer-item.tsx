import { cn } from '@/lib/utils'
import { CitationList } from '../cells/citation-list'
import type { AnswerItemRendererProps } from './base-answer-item'

export function DateAnswerItem({ answerData, className, citations, cellId }: AnswerItemRendererProps) {
  const dateValue = ('parsedDate' in answerData && answerData.parsedDate)
    ? answerData.parsedDate
    : ('value' in answerData ? answerData.value : String(answerData))

  // For dates, show citations as a list after the value
  return (
    <div className={cn("flex items-center gap-1 text-xs text-text-secondary break-words whitespace-normal flex-1", className)}>
      <span>{dateValue}</span>
      {citations && citations.length > 0 && cellId && (
        <CitationList
          citationIds={citations.map(c => c.citationOrder)}
          citations={citations}
          cellId={cellId}
        />
      )}
    </div>
  )
}