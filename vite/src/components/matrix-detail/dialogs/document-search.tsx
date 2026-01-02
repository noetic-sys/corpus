import { useMemo } from 'react'
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Loader2 } from "lucide-react"
import { DocumentSearchItem } from './components/document-search-item'
import type { DocumentResponse, DocumentSearchHitResponse } from '@/client'

interface DocumentSearchProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  isSearching: boolean
  searchResults: {
    results: DocumentSearchHitResponse[]
    totalCount: number
    skip: number
    limit: number
    hasMore: boolean
  } | null
  selectedDocuments: DocumentResponse[]
  onToggleSelection: (doc: DocumentResponse) => void
}


export function DocumentSearch({
  searchQuery,
  onSearchChange,
  isSearching,
  searchResults,
  selectedDocuments,
  onToggleSelection
}: DocumentSearchProps) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="search-input" className="flex items-center gap-2">
          Search Documents
          {isSearching && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
        </Label>
        <Input
          id="search-input"
          type="text"
          variant="blocky"
          placeholder="Search by filename or content..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="mt-2"
        />
      </div>
      
      {selectedDocuments.length > 0 && (
        <div className="bg-secondary/20 p-3 rounded border">
          <p className="text-sm font-medium mb-2">
            {selectedDocuments.length} document(s) selected
          </p>
          <div className="flex flex-wrap gap-1">
            {selectedDocuments.map(doc => (
              <Badge key={doc.id} variant="secondary" style="blocky" className="text-xs">
                {doc.filename}
                <button
                  onClick={() => onToggleSelection(doc)}
                  className="ml-1 hover:text-destructive"
                >
                  ×
                </button>
              </Badge>
            ))}
          </div>
        </div>
      )}
      
      <ScrollArea className="h-96 border rounded">
        {useMemo(() => {
          if (searchResults) {
            if (searchResults.results.length === 0) {
              return (
                <div className="text-center text-muted-foreground py-8">
                  No documents found
                </div>
              )
            }

            return (
              <div className="p-4 space-y-2">
                {searchResults.results.map(hit => (
                  <DocumentSearchItem
                    key={hit.document.id}
                    document={hit.document}
                    matchScore={hit.matchScore}
                    matchType={hit.matchType}
                    snippets={hit.snippets}
                    isSelected={selectedDocuments.some(d => d.id === hit.document.id)}
                    onToggle={onToggleSelection}
                  />
                ))}
              </div>
            )
          }

          return (
            <div className="flex items-center justify-center h-32 text-muted-foreground">
              Start typing to search documents
            </div>
          )
        }, [searchResults, selectedDocuments, onToggleSelection])}
      </ScrollArea>
    </div>
  )
}