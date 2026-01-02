import { useState, useCallback, useRef, useTransition } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { toast } from 'sonner'
import { hybridSearchDocumentsApiV1DocumentsSearchHybridGet } from '@/client'
import { apiClient } from '@/lib/api'
import type { DocumentSearchHitResponse } from '@/client'

interface HybridDocumentSearchResult {
  results: DocumentSearchHitResponse[]
  totalCount: number
  skip: number
  limit: number
  hasMore: boolean
}

const DEBOUNCE_DELAY = 500 // Wait for user to stop typing

export function useDocumentSearch() {
  const { getToken } = useAuth()
  const [searchResults, setSearchResults] = useState<HybridDocumentSearchResult | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const debounceTimerRef = useRef<number | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const [, startTransition] = useTransition()

  const searchDocuments = useCallback(async (query: string = '') => {
    if (!query || query.trim().length === 0) {
      setSearchResults(null)
      setIsSearching(false)
      return
    }

    // Cancel any ongoing search
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    abortControllerRef.current = new AbortController()

    // Use transition to avoid blocking input
    startTransition(() => {
      setIsSearching(true)
    })

    try {
      const token = await getToken()
      const response = await hybridSearchDocumentsApiV1DocumentsSearchHybridGet({
        query: {
          q: query,
          limit: 50,
          snippetsPerDoc: 3
        },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        throw new Error('Failed to search documents')
      }

      const data: HybridDocumentSearchResult = response.data

      // Use transition for non-blocking updates
      startTransition(() => {
        setSearchResults(data)
      })
    } catch (error) {
      // Ignore abort errors
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }
      console.error('Search error:', error)
      toast.error('Failed to search documents')
    } finally {
      startTransition(() => {
        setIsSearching(false)
      })
    }
  }, [getToken])

  const handleSearchInputChange = useCallback((query: string) => {
    // Update query immediately (never blocked)
    setSearchQuery(query)

    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    // Check if query ends with a space (immediate search trigger)
    const endsWithSpace = query.length > 0 && query[query.length - 1] === ' '

    if (endsWithSpace && query.trim().length > 0) {
      // Trigger search immediately on space
      searchDocuments(query.trim())
    } else {
      // Debounced search after user stops typing
      debounceTimerRef.current = setTimeout(() => {
        searchDocuments(query)
      }, DEBOUNCE_DELAY)
    }
  }, [searchDocuments])

  return {
    searchResults,
    isSearching,
    searchQuery,
    searchDocuments,
    handleSearchInputChange,
    setSearchQuery
  }
}