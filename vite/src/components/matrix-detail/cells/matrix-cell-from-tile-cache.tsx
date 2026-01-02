import { useQueryClient, useQueries } from '@tanstack/react-query'
import { MatrixCell } from './matrix-cell'
import type { MatrixCellType } from '../types'
import { useMemo } from 'react'
import { useMatrixContext } from '../context/matrix-context'

interface EntityRefInput {
  entitySetId: number
  entityId: number
  role: string
}

interface MatrixCellFromTileCacheProps {
  matrixId: number
  entityRefs: EntityRefInput[]
  isDiagonal?: boolean
  isSelected?: boolean
  onReprocess?: (cellId: number) => void
  isReprocessing?: boolean
  isDetailOpen?: boolean
  onDetailOpenChange?: (open: boolean) => void
}

/**
 * Cell component that reads data from the tile cache.
 * Expects MatrixTileDataProvider to have prefetched the tile data.
 * Matches cells by entity refs.
 */
export function MatrixCellFromTileCache({
  matrixId,
  entityRefs,
  isDiagonal = false,
  isSelected = false,
  onReprocess,
  isReprocessing = false,
  isDetailOpen = false,
  onDetailOpenChange
}: MatrixCellFromTileCacheProps) {
  const queryClient = useQueryClient()
  const { tileIndexRef } = useMatrixContext()

  // Create stable cell key from entityRefs
  const cellKey = useMemo(
    () => entityRefs.map(r => `${r.entitySetId}:${r.entityId}:${r.role}`).sort().join('|'),
    [entityRefs]
  )

  // O(1) lookup in tile index ref instead of O(tiles) cache iteration
  const tileQueryKeys: (readonly unknown[])[] = useMemo(() => {
    return tileIndexRef.current.get(cellKey) || []
  }, [tileIndexRef, cellKey])

  // Subscribe to all tiles that contain this cell using useQueries
  const tileQueries = useQueries({
    queries: tileQueryKeys.map(queryKey => ({
      queryKey,
      enabled: false, // Don't fetch, just subscribe to cache
    }))
  })

  // Extract cell data from the tile queries by matching entity refs
  const { cell, hasData, isFetching } = useMemo(() => {
    let foundCell: MatrixCellType | null = null
    let tileHasData = false
    let tileFetching = false

    for (const query of tileQueries) {
      if (query.data) {
        tileHasData = true
        const cells = query.data as MatrixCellType[]
        // Match cells by comparing entity IDs AND roles (critical for cross-correlation matrices)
        const match = cells.find(c => {
          return entityRefs.every(inputRef =>
            c.entityRefs?.some(cellRef =>
              cellRef.entitySetId === inputRef.entitySetId &&
              cellRef.entityId === inputRef.entityId &&
              cellRef.role === inputRef.role
            )
          )
        })
        if (match) {
          foundCell = match
        }
      }

      if (query.isFetching) {
        tileFetching = true
      }
    }

    return {
      cell: foundCell,
      hasData: tileHasData,
      isFetching: tileFetching
    }
  }, [tileQueries, entityRefs])

  const handleReprocess = async (cellId: number) => {
    if (onReprocess) {
      onReprocess(cellId)
    }

    // Optimistically update the cell in all tiles that contain it
    const allTiles = queryClient.getQueriesData({
      predicate: (query) => {
        const queryKey = query.queryKey
        return queryKey[0] === 'matrix-tile' && queryKey[1] === matrixId
      }
    })

    for (const [queryKey] of allTiles) {
      queryClient.setQueryData(
        queryKey,
        (oldData: MatrixCellType[] | undefined) => {
          if (oldData) {
            return oldData.map(c => {
              // Match by all entity refs including roles (critical for cross-correlation matrices)
              const matches = entityRefs.every(inputRef =>
                c.entityRefs?.some(cellRef =>
                  cellRef.entitySetId === inputRef.entitySetId &&
                  cellRef.entityId === inputRef.entityId &&
                  cellRef.role === inputRef.role
                )
              )
              return matches
                ? {
                    ...c,
                    status: 'pending' as const,
                    currentAnswer: null,
                    currentAnswerSetId: null
                  }
                : c
            })
          }
          return oldData
        }
      )
    }

    // Invalidate all tiles containing this cell
    queryClient.invalidateQueries({
      predicate: (query) => {
        const queryKey = query.queryKey
        if (queryKey[0] !== 'matrix-tile' || queryKey[1] !== matrixId) {
          return false
        }

        const filterParts = queryKey.slice(2) as Array<{
          entitySetId: number
          role: string
          entityIds: number[]
        }>

        // Check if tile includes all entity IDs AND roles
        const hasAllRefs = entityRefs.every(ref => {
          return filterParts.some(filterPart => {
            return filterPart.entitySetId === ref.entitySetId &&
                   filterPart.role === ref.role &&
                   filterPart.entityIds.includes(ref.entityId)
          })
        })

        return hasAllRefs
      }
    })
  }

  const handleRetry = () => {
    // Invalidate all tiles containing this cell
    queryClient.invalidateQueries({
      predicate: (query) => {
        const queryKey = query.queryKey
        if (queryKey[0] !== 'matrix-tile' || queryKey[1] !== matrixId) {
          return false
        }

        const filterParts = queryKey.slice(2) as Array<{
          entitySetId: number
          role: string
          entityIds: number[]
        }>

        // Check if tile includes all entity IDs AND roles
        const hasAllRefs = entityRefs.every(ref => {
          return filterParts.some(filterPart => {
            return filterPart.entitySetId === ref.entitySetId &&
                   filterPart.role === ref.role &&
                   filterPart.entityIds.includes(ref.entityId)
          })
        })

        return hasAllRefs
      }
    })
  }

  // Only show loading if we have NO data at all
  // If we have data (even placeholder), show it - don't show loading spinner
  const showLoading = !hasData && isFetching

  // Not yet loaded if no tile has been fetched yet
  const isNotYetLoaded = !hasData && !isFetching

  return (
    <MatrixCell
      cell={cell}
      isLoading={showLoading}
      isNotYetLoaded={isNotYetLoaded}
      isError={false}
      isDiagonal={isDiagonal}
      isSelected={isSelected}
      onRetry={handleRetry}
      matrixId={matrixId}
      onReprocess={handleReprocess}
      isReprocessing={isReprocessing}
      isDetailOpen={isDetailOpen}
      onDetailOpenChange={onDetailOpenChange}
    />
  )
}
