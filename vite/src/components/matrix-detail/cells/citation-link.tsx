import { useAuth } from '@/hooks/useAuth'
import { getHighlightedDocumentForCellApiV1DocumentsDocumentIdHighlightedMatrixCellIdGet } from '@/client'
import { apiClient } from '@/lib/api'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useDocument } from '../context/matrix-context'
import type { Citation } from '../types'

interface CitationLinkProps {
  citation: Citation
  citationNumber: number
  cellId: number
}

export function CitationLink({ citation, citationNumber, cellId }: CitationLinkProps) {
  const { getToken } = useAuth()
  const document = useDocument(citation.documentId)

  const handleClick = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()

    try {
      const token = await getToken()

      const response = await getHighlightedDocumentForCellApiV1DocumentsDocumentIdHighlightedMatrixCellIdGet({
        path: {
          documentId: citation.documentId,
          matrixCellId: cellId
        },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient,
        parseAs: 'blob' // Get the raw binary data
      })

      if (response.error) {
        console.error('Error fetching highlighted document:', response.error)
        return
      }

      // The response.data should be a Blob
      const blob = response.data as Blob

      // Get content type from response headers or blob
      const contentType = response.response?.headers.get('Content-Type') || blob.type || 'application/octet-stream'

      // Create a new blob with correct content type
      const typedBlob = new Blob([blob], { type: contentType })
      const url = URL.createObjectURL(typedBlob)

      window.open(url, '_blank')

      // Clean up the object URL after a delay
      setTimeout(() => URL.revokeObjectURL(url), 100)
    } catch (error) {
      console.error('Failed to load highlighted document:', error)
    }
  }

  return (
    <TooltipProvider>
      <Tooltip delayDuration={300}>
        <TooltipTrigger asChild>
          <a
            href="#"
            onClick={handleClick}
            className="align-super text-[0.75em] text-blue-600 hover:text-blue-800 font-medium cursor-pointer no-underline hover:underline"
          >
            [{citationNumber}]
          </a>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-md">
          {document && (
            <p className="text-xs font-semibold mb-1 text-muted-foreground">
              {document.label || document.document.filename}
            </p>
          )}
          <p className="text-sm">{citation.quoteText}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}