import { useState } from 'react'
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { FileText, CheckCircle, Clock, XCircle, ChevronDown, ChevronUp } from "lucide-react"
import type { DocumentResponse, DocumentMatchSnippetResponse } from '@/client'

interface DocumentSearchItemProps {
  document: DocumentResponse
  matchScore?: number
  matchType?: string
  snippets?: DocumentMatchSnippetResponse[]
  isSelected: boolean
  onToggle: (doc: DocumentResponse) => void
}

const getExtractionStatusBadge = (status: string) => {
  switch (status) {
    case 'completed':
      return <Badge variant="default" style="blocky" className="text-xs"><CheckCircle className="w-3 h-3 mr-1" />Complete</Badge>
    case 'processing':
      return <Badge variant="secondary" style="blocky" className="text-xs"><Clock className="w-3 h-3 mr-1" />Processing</Badge>
    case 'failed':
      return <Badge variant="destructive" style="blocky" className="text-xs"><XCircle className="w-3 h-3 mr-1" />Failed</Badge>
    default:
      return <Badge variant="outline" style="blocky" className="text-xs"><Clock className="w-3 h-3 mr-1" />Pending</Badge>
  }
}

export function DocumentSearchItem({
  document,
  snippets,
  isSelected,
  onToggle
}: DocumentSearchItemProps) {
  const [isSnippetsOpen, setIsSnippetsOpen] = useState(true)
  const hasSnippets = snippets && snippets.length > 0

  return (
    <div
      className={`p-3 rounded border transition-colors ${
        isSelected
          ? 'bg-primary/10 border-primary'
          : 'hover:bg-secondary/50'
      }`}
    >
      <div
        className="flex items-start justify-between cursor-pointer"
        onClick={() => onToggle(document)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 flex-shrink-0" />
            <span className="font-medium truncate">{document.filename}</span>
            {isSelected && <CheckCircle className="h-4 w-4 text-primary flex-shrink-0" />}
          </div>
          <div className="flex items-center gap-2 mt-1">
            {getExtractionStatusBadge(document.extractionStatus)}
            {document.contentType && (
              <Badge variant="outline" style="blocky" className="text-xs">
                {document.contentType}
              </Badge>
            )}
          </div>

          <p className="text-xs text-muted-foreground mt-2">
            Created: {new Date(document.createdAt).toLocaleDateString()}
          </p>
        </div>
      </div>

      {hasSnippets && (
        <div className="mt-3">
          <button
            onClick={(e) => {
              e.stopPropagation()
              setIsSnippetsOpen(!isSnippetsOpen)
            }}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {isSnippetsOpen ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
            <span>{snippets.length} matched snippet{snippets.length > 1 ? 's' : ''}</span>
          </button>

          {isSnippetsOpen && (
            <div className="mt-2 space-y-2">
              {snippets.map((snippet) => (
                <Card key={snippet.chunkId} variant="blocky" className="py-2 gap-0">
                  <CardContent className="px-3 py-2">
                    <p className="text-xs text-foreground/80 leading-relaxed">
                      "{snippet.content}"
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}