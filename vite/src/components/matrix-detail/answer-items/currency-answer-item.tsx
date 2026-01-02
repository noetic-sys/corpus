import { cn } from '@/lib/utils'
import { CitationList } from '../cells/citation-list'
import type { AnswerItemRendererProps } from './base-answer-item'

export function CurrencyAnswerItem({ answerData, className, citations, cellId }: AnswerItemRendererProps) {
  const currencyValue = ('currency' in answerData && 'amount' in answerData && answerData.currency && answerData.amount)
    ? `${answerData.currency} ${answerData.amount.toLocaleString()}`
    : ('value' in answerData ? answerData.value : String(answerData))

  // For currency, show citations as a list after the value
  return (
    <div className={cn("flex items-center gap-1 text-xs text-text-secondary break-words whitespace-normal flex-1", className)}>
      <span>{currencyValue}</span>
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