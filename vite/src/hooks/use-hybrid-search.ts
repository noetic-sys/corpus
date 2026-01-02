import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { hybridSearchChunks } from '@/client'
import { apiClient } from '@/lib/api'
import type { ChunkSearchResponse } from '@/client'

interface UseHybridSearchOptions {
  query: string
  documentIds?: number[]
  matrixId?: number
  entitySetId?: number
  skip?: number
  limit?: number
  useVector?: boolean
  enabled?: boolean
}

/**
 * Hook for hybrid chunk search (BM25 + vector similarity).
 *
 * Uses TanStack Query for caching and automatic refetching.
 * The search combines keyword matching with semantic similarity
 * to return the most relevant chunks ranked by relevance.
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useHybridSearch({
 *   query: "What is the revenue?",
 *   documentIds: [1, 2, 3],
 *   limit: 10,
 * })
 * ```
 */
export function useHybridSearch({
  query,
  documentIds,
  matrixId,
  entitySetId,
  skip = 0,
  limit = 10,
  useVector = true,
  enabled = true,
}: UseHybridSearchOptions) {
  const { getToken } = useAuth()

  return useQuery<ChunkSearchResponse, Error>({
    queryKey: [
      'hybrid-search',
      query,
      documentIds,
      matrixId,
      entitySetId,
      skip,
      limit,
      useVector,
    ],
    queryFn: async () => {
      const token = await getToken()

      const response = await hybridSearchChunks({
        client: apiClient,
        query: {
          query,
          document_ids: documentIds,
          matrix_id: matrixId,
          entity_set_id: entitySetId,
          skip,
          limit,
          use_vector: useVector,
        },
        headers: {
          authorization: `Bearer ${token}`,
        },
      })

      if (response.error) {
        throw new Error(`Search failed: ${JSON.stringify(response.error)}`)
      }

      return response.data!
    },
    enabled: enabled && !!query && query.trim().length > 0,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
  })
}
