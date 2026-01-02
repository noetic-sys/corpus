import { memo } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useQuery } from '@tanstack/react-query'
import {
  getMatrix,
  getDocumentsByMatrix,
  getQuestionsByMatrix,
  getAvailableProvidersApiV1AiProvidersGet,
  getAvailableModelsApiV1AiModelsGet,
  getMatrixEntitySets,
} from '@/client'
import { apiClient } from '@/lib/api'
import { MatrixPageWrapper } from '@/components/matrix-detail'
import { MatrixDetail } from '@/components/matrix-detail'
import type { MatrixDocument, Question } from '@/components/matrix-detail/types'
import type { AiProviderResponse, AiModelResponse, MatrixEntitySetsResponse } from '@/client'

interface MatrixBasic {
  id: number
  name: string
  description?: string | null
  createdAt: string
  updatedAt: string
}

interface MatrixTabContentProps {
  matrixId: number
}

export const MatrixTabContent = memo(function MatrixTabContent({ matrixId }: MatrixTabContentProps) {
  console.log(`[MatrixTabContent] RENDER - matrixId: ${matrixId} at ${performance.now().toFixed(2)}ms`)
  const { getToken } = useAuth()

  const { data: matrix, isLoading: isMatrixLoading } = useQuery({
    queryKey: ['matrix', matrixId],
    queryFn: async (): Promise<MatrixBasic | null> => {
      try {
        const token = await getToken()
        const response = await getMatrix({
          path: { matrixId: matrixId },
          headers: {
            authorization: `Bearer ${token}`
          },
          client: apiClient
        })
        return response.data || null
      } catch (error) {
        console.error('Error fetching matrix:', error)
        return null
      }
    }
  })

  const { data: documents = [], isLoading: isDocumentsLoading } = useQuery({
    queryKey: ['matrix-documents', matrixId],
    queryFn: async (): Promise<MatrixDocument[]> => {
      try {
        const token = await getToken()
        const response = await getDocumentsByMatrix({
          path: { matrixId: matrixId },
          headers: {
            authorization: `Bearer ${token}`
          },
          client: apiClient
        })
        return response.data || []
      } catch (error) {
        console.error('Error fetching documents:', error)
        return []
      }
    }
  })

  const { data: questions = [], isLoading: isQuestionsLoading } = useQuery({
    queryKey: ['matrix-questions', matrixId],
    queryFn: async (): Promise<Question[]> => {
      try {
        const token = await getToken()
        const response = await getQuestionsByMatrix({
          path: { matrixId: matrixId },
          headers: {
            authorization: `Bearer ${token}`
          },
          client: apiClient
        })
        // Map QuestionResponse to Question, providing a default value for questionTypeId
        return (response.data || []).map((q: any) => ({
          ...q,
          questionTypeId: q.questionTypeId ?? 1 // Default to 1 if null or undefined
        })) as Question[]
      } catch (error) {
        console.error('Error fetching questions:', error)
        return []
      }
    }
  })

  const { data: aiProviders = [], isLoading: isProvidersLoading } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: async (): Promise<AiProviderResponse[]> => {
      try {
        const token = await getToken()
        const response = await getAvailableProvidersApiV1AiProvidersGet({
          client: apiClient,
          headers: {
            authorization: `Bearer ${token}`
          },
        })
        return response.data || []
      } catch (error) {
        console.error('Error fetching AI providers:', error)
        return []
      }
    }
  })

  const { data: aiModels = [], isLoading: isModelsLoading } = useQuery({
    queryKey: ['ai-models'],
    queryFn: async (): Promise<AiModelResponse[]> => {
      try {
        const token = await getToken()
        const response = await getAvailableModelsApiV1AiModelsGet({
          client: apiClient,
          headers: {
            authorization: `Bearer ${token}`
          },
        })
        return response.data || []
      } catch (error) {
        console.error('Error fetching AI models:', error)
        return []
      }
    }
  })

  const { data: entitySets, isLoading: isEntitySetsLoading } = useQuery({
    queryKey: ['matrix-entity-sets', matrixId],
    queryFn: async (): Promise<MatrixEntitySetsResponse | null> => {
      try {
        const token = await getToken()
        const response = await getMatrixEntitySets({
          path: { matrixId },
          headers: {
            authorization: `Bearer ${token}`
          },
          client: apiClient
        })
        return response.data || null
      } catch (error) {
        console.error('Error fetching entity sets:', error)
        return null
      }
    }
  })

  const isLoading = isMatrixLoading || isDocumentsLoading || isQuestionsLoading || isProvidersLoading || isModelsLoading || isEntitySetsLoading

  console.log('[MatrixTabContent] Loading states:', {
    matrixId,
    isMatrixLoading,
    isDocumentsLoading,
    isQuestionsLoading,
    isProvidersLoading,
    isModelsLoading,
    isEntitySetsLoading
  })

  if (isLoading) {
    return <div className="flex items-center justify-center h-full">Loading matrix...</div>
  }

  if (!matrix || !entitySets) {
    return <div className="flex items-center justify-center h-full">Failed to load matrix</div>
  }

  console.log('[MatrixTabContent] entitySets:', entitySets)
  console.log('[MatrixTabContent] matrix_type:', entitySets.matrixType)

  return (
    <MatrixPageWrapper
      matrix={matrix}
      matrixId={matrixId}
      matrixType={entitySets?.matrixType || 'standard'}
      documents={documents || []}
      questions={questions || []}
      entitySets={entitySets?.entitySets || []}
      aiProviders={aiProviders || []}
      aiModels={aiModels || []}
    >
      <div className="h-full flex flex-col p-4 bg-muted">
        <MatrixDetail />
      </div>
    </MatrixPageWrapper>
  )
})