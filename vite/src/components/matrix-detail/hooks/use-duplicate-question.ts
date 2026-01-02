import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { duplicateQuestionApiV1QuestionsQuestionIdDuplicatePost } from '@/client'
import { apiClient } from '@/lib/api'
import {throwApiError} from "@/lib/api-error.ts";

export const useDuplicateQuestion = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  const [isDuplicating, setIsDuplicating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const duplicateQuestion = async (matrixId: number, questionId: number) => {
    try {
      setIsDuplicating(true)
      setError(null)

      const token = await getToken()

      const response = await duplicateQuestionApiV1QuestionsQuestionIdDuplicatePost({
        path: {
          questionId: questionId
        },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to duplicate question')
      }

      const duplicatedQuestion = response.data

      toast.success(`Question duplicated successfully: "${duplicatedQuestion.questionText.substring(0, 50)}${duplicatedQuestion.questionText.length > 50 ? '...' : ''}"`)

      // Invalidate matrix data to refetch questions and cells
      queryClient.invalidateQueries({ queryKey: ['matrix', matrixId.toString()] })

      return duplicatedQuestion
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to duplicate question'
      setError(errorMessage)
      toast.error(`Failed to duplicate question: ${errorMessage}`)
      throw err
    } finally {
      setIsDuplicating(false)
    }
  }

  return {
    duplicateQuestion,
    isDuplicating,
    error,
  }
}