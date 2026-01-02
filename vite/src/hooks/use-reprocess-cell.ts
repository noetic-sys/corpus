import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { reprocessMatrixCellsApiV1MatricesMatrixIdReprocessPost } from '@/client'
import { apiClient } from '@/lib/api'
import { throwApiError } from '@/lib/api-error'

interface UseReprocessCellResult {
  reprocessCell: (matrixId: number, cellId: number) => Promise<boolean>
  isReprocessing: boolean
  error: string | null
}

export function useReprocessCell(): UseReprocessCellResult {
  const { getToken } = useAuth()
  const [isReprocessing, setIsReprocessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reprocessCell = async (matrixId: number, cellId: number): Promise<boolean> => {
    setIsReprocessing(true)
    setError(null)

    try {
      const token = await getToken()

      const response = await reprocessMatrixCellsApiV1MatricesMatrixIdReprocessPost({
        client: apiClient,
        path: {
          matrixId: matrixId
        },
        body: {
          cellIds: [cellId],
          wholeMatrix: false
        },
        headers: {
          authorization: `Bearer ${token}`
        }
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to reprocess cell')
      }

      console.log('Cell reprocessing started:', response.data)
      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error reprocessing cell:', errorMessage)
      return false
    } finally {
      setIsReprocessing(false)
    }
  }

  return {
    reprocessCell,
    isReprocessing,
    error,
  }
}