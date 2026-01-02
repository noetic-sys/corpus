import { useEffect, useRef, useState, useMemo } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useQuery } from '@tanstack/react-query'
import { getMatrixCellsBatch } from '@/client'
import { apiClient } from '@/lib/api'
import { queueRequest } from '@/lib/request-queue'
import type { MatrixCellType } from '../types'
import type { EntitySetFilter } from '@/client/types.gen'
import { getTileKey } from '../utils/tile-utils'

interface MatrixTileDataProviderProps {
  matrixId: number
  filters: EntitySetFilter[]
}

/**
 * Invisible component that prefetches all cells for a tile (rectangular block)
 * when it comes into view. Stores data in React Query cache for individual
 * cells to consume.
 *
 * Uses the batch endpoint: POST /api/v1/matrices/{id}/cells/batch
 */
export function MatrixTileDataProvider({
  matrixId,
  filters,
}: MatrixTileDataProviderProps) {
  const { getToken } = useAuth()
  const triggerRef = useRef<HTMLDivElement>(null)
  const [hasBeenSeen, setHasBeenSeen] = useState(false)

  const tileKey = getTileKey(matrixId, filters)
  console.log('[MatrixTileDataProvider] Tile key computed:', tileKey, 'hasBeenSeen:', hasBeenSeen)

  // Reset hasBeenSeen when tile key changes (e.g., slice navigation)
  // This ensures IntersectionObserver re-checks visibility for new tiles
  // Use tileKey (already properly memoized) instead of JSON.stringify to avoid infinite loops
  const tileKeyString = useMemo(() => JSON.stringify(tileKey), [tileKey])
  useEffect(() => {
    console.log('[MatrixTileDataProvider] Tile key changed, resetting hasBeenSeen. Tile key:', tileKey, 'Filters:', filters)
    setHasBeenSeen(false)
  }, [tileKeyString])

  useQuery({
    queryKey: tileKey,
    queryFn: async (): Promise<MatrixCellType[]> => {
      console.log('[MatrixTileDataProvider] *** QUERY FN EXECUTING *** for key:', tileKey)
      try {
        const token = await getToken()

        // Only queue the HTTP call itself, not the entire function
        const response = await queueRequest(() => getMatrixCellsBatch({
          path: {
            matrixId
          },
          body: {
            entitySetFilters: filters
          },
          headers: {
            authorization: `Bearer ${token}`
          },
          client: apiClient
        }))

        console.log('[MatrixTileDataProvider] *** RESPONSE RECEIVED *** for key:', tileKey, 'Response:', response)

        if (response.error) {
          console.error('Error fetching tile cells:', response.error)
          return []
        }

        console.log('[MatrixTileDataProvider] *** RETURNING DATA *** cells count:', response.data?.length)
        return (response.data || []) as MatrixCellType[]
      } catch (err) {
        console.error('Error fetching tile cells:', err)
        return []
      }
    },
    enabled: hasBeenSeen,
    placeholderData: (previousData) => previousData,
    staleTime: (query) => {
      const data = query.state.data as MatrixCellType[] | undefined
      // If any cell is pending or processing, don't cache
      const hasActiveCells = data?.some(cell =>
        cell.status === 'pending' || cell.status === 'processing'
      )
      return hasActiveCells ? 0 : 5 * 60 * 1000
    },
    refetchInterval: (query) => {
      const data = query.state.data as MatrixCellType[] | undefined
      // Poll if any cell is pending or processing
      const hasActiveCells = data?.some(cell =>
        cell.status === 'pending' || cell.status === 'processing'
      )
      return hasActiveCells ? 10 * 1000 : false
    },
    gcTime: 30 * 1000, // 30 seconds - aggressively clean up old tiles when navigating away
  })

  // Intersection Observer to trigger fetch when tile comes into view
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          console.log('[MatrixTileDataProvider] Tile became visible, setting hasBeenSeen=true. Tile key:', tileKey)
          setHasBeenSeen(true)
        }
      },
      {
        threshold: 0,
        rootMargin: '500px' // Load tiles 500px before they become visible
      }
    )

    const currentRef = triggerRef.current
    if (currentRef) {
      observer.observe(currentRef)
    }

    return () => {
      if (currentRef) {
        observer.unobserve(currentRef)
      }
      observer.disconnect()
    }
  }, [])

  // Invisible trigger element
  return <div ref={triggerRef} className="absolute top-0 left-0 w-1 h-1 pointer-events-none" />
}
