import React from 'react'
import { CitationLink } from '../cells/citation-link'
import type { Citation, MatrixDocument } from '../types'

// Helper function to process text with citations and document references
export function processTextWithCitations(
  text: string,
  citations: Citation[],
  cellId: number,
  documentMap?: Map<number, MatrixDocument>
): React.ReactNode {
  // Combined pattern: [[cite:1]] or [[document:123]]
  const combinedPattern = /(\[\[cite:(\d+)\]\]|\[\[document:(\d+)\]\])/g
  const parts = []
  let lastIndex = 0
  let match

  while ((match = combinedPattern.exec(text)) !== null) {
    // Add text before match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }

    // Check if it's a citation [[cite:N]]
    if (match[2]) {
      const citationNumber = parseInt(match[2])
      const citation = citations.find(c => c.citationOrder === citationNumber)

      if (citation) {
        parts.push(
          <CitationLink
            key={`citation-${citationNumber}-${match.index}`}
            citation={citation}
            citationNumber={citationNumber}
            cellId={cellId}
          />
        )
      } else {
        parts.push(`[${citationNumber}]`)
      }
    }
    // Check if it's a document reference [[document:ID]]
    else if (match[3] && documentMap) {
      const docId = parseInt(match[3])
      const doc = documentMap.get(docId)

      if (doc) {
        parts.push(
          <strong key={`doc-${docId}-${match.index}`}>
            {doc.document.filename}
          </strong>
        )
      } else {
        parts.push(
          <span key={`doc-missing-${docId}-${match.index}`} className="text-text-tertiary">
            [Document not found]
          </span>
        )
      }
    }

    lastIndex = combinedPattern.lastIndex
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return parts.length > 1 ? <>{parts}</> : text
}