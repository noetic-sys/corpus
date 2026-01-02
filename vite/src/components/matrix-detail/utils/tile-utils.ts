/**
 * Utility functions for matrix tiling system.
 * Tiles are rectangular blocks of cells that are fetched together.
 *
 * Updated for entity-ref based architecture:
 * - Uses entity_set_filters instead of document_ids/question_ids
 * - Supports N-dimensional matrices via role-based filters
 */

import type { EntitySetFilter, EntityRole } from '@/client/types.gen'

export interface TileConfig {
  documentsPerTile: number
  questionsPerTile: number
}

export interface Tile {
  filters: EntitySetFilter[]
}

/**
 * Split an array into chunks of specified size
 */
function chunk<T>(array: T[], size: number): T[][] {
  const chunks: T[][] = []
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size))
  }
  return chunks
}

/**
 * Calculate all tiles needed to cover the complete matrix.
 * This ensures complete coverage with no gaps or overlaps.
 *
 * @param documentEntitySetId - Entity set ID for documents
 * @param questionEntitySetId - Entity set ID for questions
 * @param documentMemberIds - Complete list of document member IDs
 * @param questionMemberIds - Complete list of question member IDs
 * @param documentRole - Role for document entities (DOCUMENT for standard, LEFT/RIGHT for correlation)
 * @param questionRole - Role for question entities (always QUESTION)
 * @param config - Tile size configuration
 * @returns Array of tiles covering the entire matrix
 */
export function calculateTiles(
  documentEntitySetId: number,
  questionEntitySetId: number,
  documentMemberIds: number[],
  questionMemberIds: number[],
  documentRole: EntityRole,
  questionRole: EntityRole,
  config: TileConfig = { documentsPerTile: 10, questionsPerTile: 5 }
): Tile[] {
  const tiles: Tile[] = []

  // Split member IDs into chunks
  const documentChunks = chunk(documentMemberIds, config.documentsPerTile)
  const questionChunks = chunk(questionMemberIds, config.questionsPerTile)

  // Create a tile for every combination of document chunk × question chunk
  for (const docChunk of documentChunks) {
    for (const questionChunk of questionChunks) {
      tiles.push({
        filters: [
          {
            entitySetId: documentEntitySetId,
            entityIds: docChunk,
            role: documentRole
          },
          {
            entitySetId: questionEntitySetId,
            entityIds: questionChunk,
            role: questionRole
          }
        ]
      })
    }
  }

  return tiles
}

/**
 * Generate a stable cache key for a tile based on entity set filters.
 * Uses structured objects instead of string parsing for robustness.
 */
export function getTileKey(matrixId: number, filters: EntitySetFilter[]): unknown[] {
  // Sort filters by entity_set_id and role for consistent ordering
  const sortedFilters = [...filters].sort((a, b) => {
    if (a.entitySetId !== b.entitySetId) {
      return a.entitySetId - b.entitySetId
    }
    return (a.role || '').localeCompare(b.role || '')
  })

  // Build structured key parts from each filter
  const filterKeys = sortedFilters.map(f => ({
    entitySetId: f.entitySetId,
    role: f.role,
    entityIds: [...f.entityIds].sort((a, b) => a - b) // Sort for consistency
  }))

  return ['matrix-tile', matrixId, ...filterKeys]
}

/**
 * Build an index mapping cell keys to tile query keys.
 * This allows O(1) lookup instead of O(tiles) iteration per cell.
 *
 * @param tiles - Array of tile filter configurations
 * @param matrixId - Matrix ID for generating tile keys
 * @returns Map of cellKey -> array of tile query keys containing that cell
 */
export function buildTileIndex(
  tiles: Array<{ filters: EntitySetFilter[] }>,
  matrixId: number
): Map<string, (readonly unknown[])[]> {
  const index = new Map<string, (readonly unknown[])[]>()

  for (const tile of tiles) {
    const tileKey = getTileKey(matrixId, tile.filters)

    // Generate all cell combinations contained in this tile
    const cellKeys = generateCellKeysFromFilters(tile.filters)

    for (const cellKey of cellKeys) {
      if (!index.has(cellKey)) {
        index.set(cellKey, [])
      }
      index.get(cellKey)!.push(tileKey)
    }
  }

  return index
}

/**
 * Generate all possible cell keys from a set of tile filters.
 * For example, filters [{entityIds: [1,2]}, {entityIds: [3,4]}] generates:
 * cell keys for (1,3), (1,4), (2,3), (2,4)
 *
 * @param filters - Tile filters
 * @returns Generator of cell keys
 */
export function* generateCellKeysFromFilters(
  filters: EntitySetFilter[]
): Generator<string> {
  // Convert filters to sets of entity refs
  const refSets = filters.map(f =>
    f.entityIds.map(entityId => ({
      entitySetId: f.entitySetId,
      entityId,
      role: f.role
    }))
  )

  // Generate all combinations
  function* combinations(sets: typeof refSets, current: any[] = []): Generator<any[]> {
    if (current.length === sets.length) {
      yield current
      return
    }
    for (const item of sets[current.length]) {
      yield* combinations(sets, [...current, item])
    }
  }

  // Convert each combination to a cell key
  for (const refs of combinations(refSets)) {
    const cellKey = refs
      .map(ref => `${ref.entitySetId}:${ref.entityId}:${ref.role}`)
      .sort()
      .join('|')
    yield cellKey
  }
}

/**
 * Find which tile contains a specific cell based on its entity refs
 */
export function findTileForCell(
  tiles: Tile[],
  entityRefs: Array<{ entitySetId: number; entitySetMemberId: number }>
): Tile | null {
  return tiles.find(tile => {
    // Cell is in tile if ALL its entity refs match the tile's filters
    return entityRefs.every(ref => {
      // Find the filter for this entity set
      const filter = tile.filters.find(f => f.entitySetId === ref.entitySetId)
      if (!filter) return false

      // Check if this member ID is in the filter's entity IDs
      return filter.entityIds.includes(ref.entitySetMemberId)
    })
  }) ?? null
}

/**
 * Validate that tiles provide complete coverage with no gaps or overlaps.
 * This is useful for development/testing.
 *
 * For 2D matrices (standard): validates document × question coverage
 */
export function validateTileCoverage(
  tiles: Tile[],
  allMemberIdsByEntitySet: Map<number, number[]>
): { valid: true } | { valid: false; errors: string[] } {
  const errors: string[] = []
  const covered = new Set<string>()


  // Check for overlaps and track coverage
  for (const tile of tiles) {
    // Generate all cell coordinates for this tile
    const tileCoords = generateCellCoordinates(tile.filters)

    for (const coordKey of tileCoords) {
      if (covered.has(coordKey)) {
        errors.push(`Cell ${coordKey} is covered by multiple tiles`)
      }
      covered.add(coordKey)
    }
  }

  // Check for gaps - generate all expected coordinates
  const allExpectedCoords = generateAllCoordinates(allMemberIdsByEntitySet)

  for (const coordKey of allExpectedCoords) {
    if (!covered.has(coordKey)) {
      errors.push(`Cell ${coordKey} is not covered by any tile`)
    }
  }

  return errors.length === 0
    ? { valid: true }
    : { valid: false, errors }
}

/**
 * Generate all cell coordinate keys for a tile's filters
 */
function generateCellCoordinates(
  filters: EntitySetFilter[],
): string[] {
  // Cartesian product of all filter entity IDs
  const coords: string[] = []

  // Sort filters for consistent ordering
  const sortedFilters = [...filters].sort((a, b) => a.entitySetId - b.entitySetId)

  // Recursive cartesian product
  function buildCoords(filterIdx: number, current: number[]) {
    if (filterIdx === sortedFilters.length) {
      coords.push(current.join('-'))
      return
    }

    const filter = sortedFilters[filterIdx]
    for (const memberId of filter.entityIds) {
      buildCoords(filterIdx + 1, [...current, memberId])
    }
  }

  buildCoords(0, [])
  return coords
}

/**
 * Generate all possible cell coordinates from all member IDs
 */
function generateAllCoordinates(
  allMemberIdsByEntitySet: Map<number, number[]>
): string[] {
  const entitySetIds = Array.from(allMemberIdsByEntitySet.keys()).sort((a, b) => a - b)
  const coords: string[] = []

  function buildCoords(setIdx: number, current: number[]) {
    if (setIdx === entitySetIds.length) {
      coords.push(current.join('-'))
      return
    }

    const entitySetId = entitySetIds[setIdx]
    const memberIds = allMemberIdsByEntitySet.get(entitySetId) || []

    for (const memberId of memberIds) {
      buildCoords(setIdx + 1, [...current, memberId])
    }
  }

  buildCoords(0, [])
  return coords
}
