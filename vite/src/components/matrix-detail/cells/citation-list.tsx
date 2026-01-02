import { CitationLink } from './citation-link'
import type { Citation } from '../types'

interface CitationListProps {
  citationIds: number[]
  citations: Citation[]
  cellId: number
}

export function CitationList({ citationIds, citations, cellId }: CitationListProps) {
  if (citationIds.length === 0) return null

  return (
    <span className="inline-flex flex-wrap gap-0.5 items-center">
      {citationIds.map((citationId: number) => {
        const citation = citations.find(c => c.citationOrder === citationId)
        return citation ? (
          <CitationLink
            key={`citation-${citationId}`}
            citation={citation}
            citationNumber={citationId}
            cellId={cellId}
          />
        ) : null
      })}
    </span>
  )
}