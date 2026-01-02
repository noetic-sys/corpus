import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { getQuestionOptionSetApiV1QuestionsQuestionIdOptionSetsGet } from '@/client'
import { apiClient } from '@/lib/api'
import {throwApiError} from "@/lib/api-error.ts";

interface QuestionOption {
  id: number
  value: string
  optionSetId: number
  createdAt: string
  updatedAt: string
}

interface QuestionOptionSet {
  id: number
  questionId: number
  createdAt: string
  updatedAt: string
  options: QuestionOption[]
}

export function useQuestionOptions(questionId: number, enabled: boolean = true) {
  const { getToken } = useAuth()

  return useQuery({
    queryKey: ['question-options', questionId],
    queryFn: async (): Promise<QuestionOptionSet | null> => {
      const token = await getToken()

      const response = await getQuestionOptionSetApiV1QuestionsQuestionIdOptionSetsGet({
        path: { questionId },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        if (response.response?.status === 404) {
          // No option set exists for this question
          return null
        }
        throwApiError(response.error, 'Failed to fetch question options')
      }

      // Map the API response to match local interface
      return {
        ...response.data,
        options: response.data.options || [] // Handle undefined options
      } as QuestionOptionSet
    },
    // Enable the query only if we have a valid questionId AND it's explicitly enabled
    enabled: !!questionId && questionId > 0 && enabled,
  })
}