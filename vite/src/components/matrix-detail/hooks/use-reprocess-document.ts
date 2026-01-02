import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {type EntityRole, reprocessMatrixCellsApiV1MatricesMatrixIdReprocessPost} from '@/client'
import { apiClient } from '@/lib/api'
import { optimisticallyUpdateCellsToPending, invalidateByEntitySetFilter } from '../utils/cache-utils'
import {throwApiError} from "@/lib/api-error.ts";
import {useMatrixContext} from "@/components/matrix-detail";

export function useReprocessDocument() {
  const { getToken } = useAuth()
  const [isReprocessing, setIsReprocessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { triggerRefresh } = useMatrixContext()

  const reprocessDocument = async (matrixId: number, documentId: number, entitySetId: number, role: string) => {
    setIsReprocessing(true)
    setError(null)

    try {
      const token = await getToken()

      const response = await reprocessMatrixCellsApiV1MatricesMatrixIdReprocessPost({
        path: { matrixId },
        body: {
          entitySetFilters: [
            {
              entitySetId: entitySetId,
              entityIds: [documentId],
              role: role as EntityRole
            }
          ],
          wholeMatrix: false
        },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to reprocess document')
      }

      // Optimistically update cells for this entity to pending
      optimisticallyUpdateCellsToPending(
        queryClient,
        matrixId,
        entitySetId,
        [documentId]
      )

      // Invalidate tiles containing this entity slice to refetch
      invalidateByEntitySetFilter(
        queryClient,
        matrixId,
        entitySetId,
        [documentId]
      )

      // Refresh stats since cells are now pending
      triggerRefresh(matrixId, { stats: true })

      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to reprocess document'
      setError(errorMessage)
      toast.error('Failed to reprocess document', {
        description: errorMessage
      })
      return false
    } finally {
      setIsReprocessing(false)
    }
  }

  return {
    reprocessDocument,
    isReprocessing,
    error,
  }
}