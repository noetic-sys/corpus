import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { softDeleteMatrixEntitiesApiV1MatricesMatrixIdSoftDeletePost, type EntityRole } from '@/client'
import { apiClient } from '@/lib/api'
import { invalidateByEntitySetFilter, invalidateAllTiles } from '../utils/cache-utils'
import {useMatrixContext} from "@/components/matrix-detail";
import {throwApiError} from "@/lib/api-error.ts";

export function useSoftDeleteQuestion() {
  const { getToken } = useAuth()
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { triggerRefresh } = useMatrixContext()

  const softDeleteQuestion = async (matrixId: number, questionId: number, entitySetId: number, role: EntityRole) => {
    setIsDeleting(true)
    setError(null)

    try {
      const token = await getToken()

      const response = await softDeleteMatrixEntitiesApiV1MatricesMatrixIdSoftDeletePost({
        path: { matrixId },
        body: {
          entitySetFilters: [{
            entitySetId,
            entityIds: [questionId],
            role
          }]
        },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to delete question')
      }

      const result = response.data

      // Invalidate tiles containing this entity slice
      if (entitySetId) {
        invalidateByEntitySetFilter(queryClient, matrixId, entitySetId, [questionId])
      } else {
        // Fallback: invalidate all tiles if entity set ID not provided
        invalidateAllTiles(queryClient, matrixId)
      }

      // Refresh questions, entity sets, and tiles - documents and matrix unchanged
      triggerRefresh(matrixId, { questions: true, entitySets: true, tiles: true, stats: true })

      toast.success('Question deleted successfully', {
        description: `${result.entitiesDeleted} question and ${result.cellsDeleted} related cells deleted`
      })

      return result
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete question'
      setError(errorMessage)
      toast.error('Failed to delete question', {
        description: errorMessage
      })
      throw err
    } finally {
      setIsDeleting(false)
    }
  }

  return {
    softDeleteQuestion,
    isDeleting,
    error,
  }
}