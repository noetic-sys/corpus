import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { softDeleteMatrixEntitiesApiV1MatricesMatrixIdSoftDeletePost, type EntityRole } from '@/client'
import { apiClient } from '@/lib/api'
import { invalidateByEntitySetFilter, invalidateAllTiles } from '../utils/cache-utils'
import {useMatrixContext} from "@/components/matrix-detail";
import {throwApiError} from "@/lib/api-error.ts";

export function useSoftDeleteDocument() {
  const { getToken } = useAuth()
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { triggerRefresh } = useMatrixContext()

  const softDeleteDocument = async (matrixId: number, _matrixDocumentId: number, documentId: number, entitySetId: number, role: EntityRole) => {
    setIsDeleting(true)
    setError(null)

    try {
      const token = await getToken()

      const response = await softDeleteMatrixEntitiesApiV1MatricesMatrixIdSoftDeletePost({
        path: { matrixId },
        body: {
          entitySetFilters: [{
            entitySetId,
            entityIds: [documentId],
            role
          }]
        },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to delete document')
      }

      const result = response.data

      // Invalidate tiles containing this entity slice
      if (entitySetId) {
        invalidateByEntitySetFilter(queryClient, matrixId, entitySetId, [documentId])
      } else {
        // Fallback: invalidate all tiles if entity set ID not provided
        invalidateAllTiles(queryClient, matrixId)
      }

      // Refresh documents, entity sets, and tiles - questions and matrix unchanged
      triggerRefresh(matrixId, { documents: true, entitySets: true, tiles: true, stats: true })

      toast.success('Document deleted successfully', {
        description: `${result.entitiesDeleted} document and ${result.cellsDeleted} related cells deleted`
      })

      return result
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete document'
      setError(errorMessage)
      toast.error('Failed to delete document', {
        description: errorMessage
      })
      throw err
    } finally {
      setIsDeleting(false)
    }
  }

  return {
    softDeleteDocument,
    isDeleting,
    error,
  }
}