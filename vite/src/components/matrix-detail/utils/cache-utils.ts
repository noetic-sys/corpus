import { QueryClient } from '@tanstack/react-query'
import type { MatrixCellType } from '../types'

/**
 * Parsed entity set filter from query key
 */
interface ParsedEntitySetFilter {
  entitySetId: number
  entityIds: number[]
}

/**
 * Parse entity set filter from query key part.
 * Format: 'set5-1,2,3' -> {entitySetId: 5, entityIds: [1,2,3]}
 */
function parseEntitySetFilterFromKey(keyPart: string): ParsedEntitySetFilter | null {
  const match = keyPart.match(/^set(\d+)-(.+)$/)
  if (!match) return null

  const entitySetId = Number(match[1])
  const entityIds = match[2].split(',').map(Number)

  return { entitySetId, entityIds }
}

/**
 * Check if a cell matches the given entity set filter.
 * A cell matches if it has an entity ref with the matching entitySetId and entityId.
 */
function cellMatchesEntityFilter(
  cell: MatrixCellType,
  entitySetId: number,
  entityIds: number[]
): boolean {
  return cell.entityRefs?.some(ref =>
    ref.entitySetId === entitySetId && entityIds.includes(ref.entityId)
  ) || false
}

/**
 * Optimistically update cells in tile caches to pending state based on entity set filter.
 */
export function optimisticallyUpdateCellsToPending(
  queryClient: QueryClient,
  matrixId: number,
  entitySetId: number,
  entityIds: number[]
) {
  // Get all tile queries and update matching cells to pending
  queryClient.getQueryCache().getAll().forEach((query) => {
    const queryKey = query.queryKey

    // Check if this is a matrix tile query
    if (
      queryKey[0] === 'matrix-tile' &&
      queryKey[1] === matrixId
    ) {
      queryClient.setQueryData(queryKey, (oldData: MatrixCellType[] | undefined) => {
        if (!oldData) return oldData

        // Update cells that match the entity filter
        return oldData.map(cell => {
          if (cellMatchesEntityFilter(cell, entitySetId, entityIds)) {
            return {
              ...cell,
              status: 'pending' as const,
              currentAnswer: null,
              currentAnswerSetId: null
            }
          }
          return cell
        })
      })
    }
  })
}

/**
 * Invalidate tiles containing entities from the specified entity set filter.
 * Checks both tile data and query key bounds.
 */
export function invalidateByEntitySetFilter(
  queryClient: QueryClient,
  matrixId: number,
  entitySetId: number,
  entityIds: number[]
) {
  queryClient.invalidateQueries({
    predicate: (query) => {
      const queryKey = query.queryKey

      if (
        queryKey[0] !== 'matrix-tile' ||
        queryKey[1] !== matrixId
      ) {
        return false
      }

      // First check if any cell in the tile data matches
      const data = query.state.data as MatrixCellType[] | undefined
      if (data) {
        return data.some(cell => cellMatchesEntityFilter(cell, entitySetId, entityIds))
      }

      // If no data, check tile bounds from query key
      // Query key format: ['matrix-tile', matrixId, 'set5-1,2,3', 'set6-4,5,6', ...]
      const filterParts = queryKey.slice(2) as string[]

      for (const filterPart of filterParts) {
        const parsed = parseEntitySetFilterFromKey(filterPart)
        if (!parsed) continue

        // If this filter matches our entity set, check if any entity IDs overlap
        if (parsed.entitySetId === entitySetId) {
          const hasOverlap = parsed.entityIds.some(id => entityIds.includes(id))
          if (hasOverlap) return true
        }
      }

      return false
    }
  })
}

/**
 * Invalidate all tiles in the matrix.
 * Useful for matrix-wide changes like adding/removing entity sets.
 */
export function invalidateAllTiles(
  queryClient: QueryClient,
  matrixId: number
) {
  queryClient.invalidateQueries({
    predicate: (query) => {
      const queryKey = query.queryKey
      return queryKey[0] === 'matrix-tile' && queryKey[1] === matrixId
    }
  })
}