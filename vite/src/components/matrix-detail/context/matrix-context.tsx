import { createContext, useContext, useMemo, useState, useCallback, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { MatrixDocument, Question } from '../types'
import type {EntitySetResponse, AiProviderResponse, AiModelResponse, MatrixType} from '@/client'

interface RefreshOptions {
  documents?: boolean
  questions?: boolean
  entitySets?: boolean
  tiles?: boolean
  matrix?: boolean
  stats?: boolean
}

interface MatrixContextValue {
  // Matrix metadata
  matrix: {
    id: number
    name: string
    description?: string | null
    createdAt: string
    updatedAt: string
  }
  matrixId: number
  matrixType: MatrixType

  // Data (clean arrays, no nested structures)
  documents: MatrixDocument[]
  questions: Question[]
  entitySets: EntitySetResponse[]
  aiProviders: AiProviderResponse[]
  aiModels: AiModelResponse[]

  // Computed/optimized lookups
  documentMap: Map<number, MatrixDocument>
  questionMap: Map<number, Question>

  // Tile index for O(1) cell -> tile lookups (ref to avoid re-render loops)
  tileIndexRef: React.MutableRefObject<Map<string, (readonly unknown[])[]>>

  // View preferences
  sparseView: boolean
  setSparseView: (sparse: boolean) => void

  // Actions
  triggerRefresh: (matrixId: number, options?: RefreshOptions) => void
}

const MatrixContext = createContext<MatrixContextValue | null>(null)

interface MatrixProviderProps {
  children: React.ReactNode
  matrix: {
    id: number
    name: string
    description?: string | null
    createdAt: string
    updatedAt: string
  }
  matrixType: MatrixType
  documents?: MatrixDocument[]
  questions?: Question[]
  entitySets?: EntitySetResponse[]
  aiProviders?: AiProviderResponse[]
  aiModels?: AiModelResponse[]
}

export function MatrixProvider({
  children,
  matrix,
  matrixType,
  documents = [],
  questions = [],
  entitySets = [],
  aiProviders = [],
  aiModels = []
}: MatrixProviderProps) {
  const queryClient = useQueryClient()
  const [sparseView, setSparseView] = useState(false)

  // Tile index ref - stable across renders, updates don't trigger re-renders
  const tileIndexRef = useRef<Map<string, (readonly unknown[])[]>>(new Map())

  // Create optimized lookup maps
  const documentMap = useMemo(() => {
    return new Map(documents.map(d => [d.document.id, d]))
  }, [documents])

  const questionMap = useMemo(() => {
    return new Map(questions.map(q => [q.id, q]))
  }, [questions])

  const triggerRefresh = useCallback((matrixId: number, options?: RefreshOptions) => {
    // Default: only invalidate what's explicitly requested
    const {
      documents = false,
      questions = false,
      entitySets = false,
      tiles = false,
      matrix = false,
      stats = false
    } = options || {}

    // If no options provided, invalidate everything (backwards compat)
    const invalidateAll = !options

    if (matrix || invalidateAll) {
      queryClient.invalidateQueries({ queryKey: ['matrix', matrixId] })
    }
    if (documents || invalidateAll) {
      queryClient.invalidateQueries({ queryKey: ['matrix-documents', matrixId] })
    }
    if (questions || invalidateAll) {
      queryClient.invalidateQueries({ queryKey: ['matrix-questions', matrixId] })
    }
    if (entitySets || invalidateAll) {
      queryClient.invalidateQueries({ queryKey: ['matrix-entity-sets', matrixId] })
    }
    if (tiles || invalidateAll) {
      // Just invalidate tiles, don't remove them - let placeholderData keep old data visible
      queryClient.invalidateQueries({
        predicate: (query) => {
          const queryKey = query.queryKey
          return queryKey[0] === 'matrix-tile' && queryKey[1] === matrixId
        }
      })
    }
    if (stats || invalidateAll) {
      queryClient.invalidateQueries({ queryKey: ['matrix-stats', matrixId] })
    }
  }, [queryClient])

  const value = useMemo(
    () => ({
      matrix,
      matrixId: matrix.id,
      matrixType,
      documents,
      questions,
      entitySets,
      aiProviders,
      aiModels,
      documentMap,
      questionMap,
      tileIndexRef,
      sparseView,
      setSparseView,
      triggerRefresh
    }),
    [matrix, matrixType, documents, questions, entitySets, aiProviders, aiModels, documentMap, questionMap, sparseView, triggerRefresh]
  )

  return <MatrixContext.Provider value={value}>{children}</MatrixContext.Provider>
}

export function useMatrixContext() {
  const context = useContext(MatrixContext)
  if (!context) {
    throw new Error('useMatrixContext must be used within a MatrixProvider')
  }
  return context
}

/**
 * Hook to get a document by ID from the matrix context
 */
export function useDocument(documentId: number): MatrixDocument | undefined {
  const { documentMap } = useMatrixContext()
  return documentMap.get(documentId)
}