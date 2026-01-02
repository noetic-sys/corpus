import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { getMatrixTemplateVariablesApiV1MatricesMatrixIdTemplateVariablesGet } from '@/client'
import { apiClient } from '@/lib/api'
import type { MatrixTemplateVariableResponse } from '@/client'

export function useTemplateVariables(matrixId: number) {
  const { getToken } = useAuth()

  return useQuery({
    queryKey: ['template-variables', matrixId],
    queryFn: async (): Promise<MatrixTemplateVariableResponse[]> => {
      const token = await getToken()
      const response = await getMatrixTemplateVariablesApiV1MatricesMatrixIdTemplateVariablesGet({
        path: { matrixId },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        throw new Error(`Failed to fetch template variables: ${response.error.detail || 'Unknown error'}`)
      }

      return response.data || []
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}