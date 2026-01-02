import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { getMatrixTemplateVariablesApiV1MatricesMatrixIdTemplateVariablesGet } from '@/client'
import { apiClient } from '@/lib/api'
import type { MatrixTemplateVariableResponse } from '@/client'
import {throwApiError} from "@/lib/api-error.ts";

export const useMatrixTemplateVariables = (matrixId: number) => {
  const { getToken } = useAuth()

  return useQuery({
    queryKey: ['matrix-template-variables', matrixId],
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
        throwApiError(response.error, 'Failed to fetch template variables')
      }

      return response.data || []
    },
    enabled: !!matrixId,
  })
}