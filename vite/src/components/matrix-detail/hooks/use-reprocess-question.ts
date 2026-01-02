import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {type EntityRole, reprocessMatrixCellsApiV1MatricesMatrixIdReprocessPost} from '@/client'
import { apiClient } from '@/lib/api'
import { invalidateByEntitySetFilter } from '../utils/cache-utils'
import {throwApiError} from "@/lib/api-error.ts";
import {useMatrixContext} from "@/components/matrix-detail";

export function useReprocessQuestion() {
  const { getToken } = useAuth()
  const [isReprocessing, setIsReprocessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { triggerRefresh } = useMatrixContext()

  const reprocessQuestion = async (matrixId: number, questionId: number, entitySetId: number, role: string) => {
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
              entityIds: [questionId],
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
        throwApiError(response.error, 'Failed to reprocess question')
      }

      // Invalidate tiles containing this entity slice
      invalidateByEntitySetFilter(queryClient, matrixId, entitySetId, [questionId])

      // Refresh stats since cells are now pending
      triggerRefresh(matrixId, { stats: true })

      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to reprocess question'
      setError(errorMessage)
      toast.error('Failed to reprocess question', {
        description: errorMessage
      })
      return false
    } finally {
      setIsReprocessing(false)
    }
  }

  return {
    reprocessQuestion,
    isReprocessing,
    error,
  }
}