import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useRouter, useLocation } from '@tanstack/react-router'
import { toast } from 'sonner'
import { duplicateMatrixApiV1MatricesMatrixIdDuplicatePost } from '@/client'
import { apiClient } from '@/lib/api'
import {throwApiError} from "@/lib/api-error.ts";

export const useDuplicateMatrix = () => {
  const { getToken } = useAuth()
  const router = useRouter()
  const location = useLocation()
  const [isDuplicating, setIsDuplicating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const duplicateMatrix = async (
    matrixId: number,
    options: {
      name?: string
      description?: string
      entitySetIds: number[]
      templateVariableOverrides?: Array<{
        templateVariableId: number
        newValue: string
      }>
    }
  ) => {
    try {
      setIsDuplicating(true)
      setError(null)

      const token = await getToken()

      const requestBody = {
        name: options.name || `Matrix ${matrixId} (Copy)`,
        description: options.description || undefined,
        entitySetIds: options.entitySetIds,
        templateVariableOverrides: options.templateVariableOverrides || undefined
      }

      const response = await duplicateMatrixApiV1MatricesMatrixIdDuplicatePost({
        path: {
          matrixId: matrixId
        },
        headers: {
          authorization: `Bearer ${token}`
        },
        body: requestBody,
        client: apiClient
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to duplicate matrix')
      }

      const result = response.data

      const entitySetLabel = options.entitySetIds.length === 0
        ? 'All Entity Sets'
        : `${options.entitySetIds.length} Entity Set${options.entitySetIds.length === 1 ? '' : 's'}`

      toast.success(`Matrix duplicated successfully (${entitySetLabel})`)

      // Navigate to the new matrix using TanStack Router - stay on current page, update search
      router.navigate({
        to: location.pathname,
        search: { ...location.search, matrix: result.duplicateMatrixId },
        replace: true
      })

      return result
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to duplicate matrix'
      setError(errorMessage)
      toast.error(`Failed to duplicate matrix: ${errorMessage}`)
      throw err
    } finally {
      setIsDuplicating(false)
    }
  }

  return {
    duplicateMatrix,
    isDuplicating,
    error,
  }
}