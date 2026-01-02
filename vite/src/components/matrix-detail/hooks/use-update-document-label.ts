import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { toast } from 'sonner'
import { useQueryClient } from '@tanstack/react-query'
import { updateEntitySetMemberLabelApiV1EntitySetsEntitySetIdMembersMemberIdLabelPatch } from '@/client'
import { apiClient } from '@/lib/api'
import {throwApiError} from "@/lib/api-error.ts";

export function useUpdateDocumentLabel() {
  const { getToken } = useAuth()
  const [isUpdating, setIsUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const updateDocumentLabel = async (
    matrixId: number,
    entitySetId: number,
    memberId: number,
    label: string | null
  ) => {
    setIsUpdating(true)
    setError(null)

    try {
      const token = await getToken()

      const response = await updateEntitySetMemberLabelApiV1EntitySetsEntitySetIdMembersMemberIdLabelPatch({
        path: { entitySetId, memberId },
        body: { label },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to update document label')
      }

      const updatedMember = response.data

      // Invalidate matrix data to refetch entity sets
      queryClient.invalidateQueries({ queryKey: ['matrix', matrixId.toString()] })

      toast.success('Label updated successfully', {
        description: `Document label ${label ? `set to "${label}"` : 'removed'}`
      })

      return updatedMember
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update document label'
      setError(errorMessage)
      toast.error('Failed to update label', {
        description: errorMessage
      })
      throw err
    } finally {
      setIsUpdating(false)
    }
  }

  return {
    updateDocumentLabel,
    isUpdating,
    error,
  }
}