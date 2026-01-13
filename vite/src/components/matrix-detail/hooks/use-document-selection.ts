import { useState, useCallback } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { toast } from 'sonner'
import { associateExistingDocumentWithMatrixApiV1MatricesMatrixIdDocumentsDocumentIdAssociatePost } from '@/client'
import { apiClient } from '@/lib/api'
import type { DocumentResponse } from '@/client'

export function useDocumentSelection(
  matrixId: number,
  entitySetId: number,
  onDocumentAssociated: (doc: DocumentResponse) => void
) {
  const { getToken } = useAuth()
  const [selectedDocuments, setSelectedDocuments] = useState<DocumentResponse[]>([])
  const [isAssociating, setIsAssociating] = useState(false)

  const toggleDocumentSelection = useCallback((doc: DocumentResponse) => {
    setSelectedDocuments(prev => {
      const isSelected = prev.some(d => d.id === doc.id)
      if (isSelected) {
        return prev.filter(d => d.id !== doc.id)
      } else {
        return [...prev, doc]
      }
    })
  }, [])

  const associateSelectedDocuments = useCallback(async () => {
    if (selectedDocuments.length === 0) return

    setIsAssociating(true)

    const token = await getToken()

    const promises = selectedDocuments.map(doc =>
      associateExistingDocumentWithMatrixApiV1MatricesMatrixIdDocumentsDocumentIdAssociatePost({
        path: {
          matrixId,
          documentId: doc.id
        },
        query: {
          entitySetId
        },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })
    )

    const responses = await Promise.all(promises)

    // Process each response
    let successful = 0
    for (let i = 0; i < responses.length; i++) {
      const response = responses[i]
      const doc = selectedDocuments[i]

      if (response.error) {
        const errorMessage = response.error.detail || 'Association failed'

        toast.error("Failed to associate document", {
          description: `${doc.filename}: ${errorMessage}`
        })
      } else {
        onDocumentAssociated(doc)
        successful++
      }
    }

    // Show success message if any succeeded
    if (successful > 0) {
      toast.success(`Successfully associated ${successful} document(s)`)
    }

    setSelectedDocuments([])
    setIsAssociating(false)
  }, [selectedDocuments, matrixId, entitySetId, onDocumentAssociated, getToken])

  const clearSelection = useCallback(() => {
    setSelectedDocuments([])
  }, [])

  return {
    selectedDocuments,
    isAssociating,
    toggleDocumentSelection,
    associateSelectedDocuments,
    clearSelection
  }
}