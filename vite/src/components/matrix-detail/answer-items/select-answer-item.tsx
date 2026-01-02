import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { CitationList } from '../cells/citation-list'
import type { AnswerItemRendererProps } from './base-answer-item'

export function SelectAnswerItem({ answerData, className, citations, cellId }: AnswerItemRendererProps) {
  // For unified select, each SelectAnswerData represents a single option
  const optionValue = 'optionValue' in answerData
    ? answerData.optionValue
    : String(answerData)

  // For select, show badge with citations as a list after
  return (
    <div className={cn("inline-flex items-center gap-1", className)}>
      <Badge
        variant="outline"
        style="blocky"
        className="text-xs break-words whitespace-normal"
      >
        {optionValue}
      </Badge>
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