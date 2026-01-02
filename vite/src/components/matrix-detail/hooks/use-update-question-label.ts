import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { toast } from 'sonner'
import { useQueryClient } from '@tanstack/react-query'
import { updateQuestionLabelApiV1QuestionsQuestionIdLabelPatch } from '@/client'
import { apiClient } from '@/lib/api'
import {throwApiError} from "@/lib/api-error.ts";

export function useUpdateQuestionLabel() {
  const { getToken } = useAuth()
  const [isUpdating, setIsUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const updateQuestionLabel = async (matrixId: number, questionId: number, label: string | null) => {
    setIsUpdating(true)
    setError(null)

    try {
      const token = await getToken()

      const response = await updateQuestionLabelApiV1QuestionsQuestionIdLabelPatch({
        path: { questionId },
        body: { label },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to update question label')
      }

      const updatedQuestion = response.data

      // Invalidate matrix data to refetch questions list
      queryClient.invalidateQueries({ queryKey: ['matrix', matrixId.toString()] })

      toast.success('Label updated successfully', {
        description: `Question label ${label ? `set to "${label}"` : 'removed'}`
      })

      return updatedQuestion
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update question label'
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
    updateQuestionLabel,
    isUpdating,
    error,
  }
}