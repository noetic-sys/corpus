import { useMemo, useState } from 'react'
import { EntityHeader } from '../headers/entity-header'
import { EntitySetAddButton } from '../interactive/entity-set-add-button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { MatrixTileDataProvider } from '../cells/matrix-tile-data-provider'
import { MatrixCellFromTileCache } from '../cells/matrix-cell-from-tile-cache'
import { useMatrixContext } from '../context/matrix-context'
import { useReprocessCell } from '@/hooks/use-reprocess-cell'
import { useGridNavigation } from '@/hooks/use-grid-navigation'
import { calculateTiles, calculateTiles1D, buildTileIndex } from '../utils/tile-utils'
import { computeMatrixDimensions } from '../utils/matrix-dimensions'
import type { EntityRole, MatrixType } from '@/client/types.gen'


interface GridConfig {
  /** The 2 axes to display as the grid (rows × columns) */
  gridAxes: Array<{ role: EntityRole; entitySetId: number; entitySetName: string; count: number }>
  /** Optional filter for the 3rd dimension (the slice) */
  sliceFilter?: { entitySetId: number; entityIds: number[]; role: EntityRole }
}

interface MatrixGridProps {
  /** Configuration for how to render the 2D grid from the N-dimensional data */
  config?: GridConfig
}

export function MatrixGrid({ config }: MatrixGridProps) {
  const { matrixId, matrixType, entitySets, tileIndexRef } = useMatrixContext()
  const { reprocessCell } = useReprocessCell()
  const [detailSheetCell, setDetailSheetCell] = useState<{ row: number; col: number } | null>(null)

  const handleReprocessCell = async (cellId: number) => {
    await reprocessCell(matrixId, cellId)
  }

  // Compute dimensions for the matrix
  const dimensions = useMemo(() => {
    return computeMatrixDimensions(matrixType as MatrixType, entitySets)
  }, [matrixType, entitySets])

  // Compute default grid configuration if not provided
  const gridConfig = useMemo(() => {
    if (config) return config

    // Default: compute from matrix type
    return {
      gridAxes: dimensions.gridAxes,
      sliceFilter: undefined
    }
  }, [config, dimensions])

  // Check if this is a synopsis matrix (1D: single axis of questions)
  const isSynopsis = matrixType === 'synopsis'

  // Calculate all tiles upfront based on grid configuration
  const tiles = useMemo(() => {
    const { gridAxes, sliceFilter } = gridConfig

    // Synopsis matrices: 1D tiling (questions only - cells don't vary by document)
    if (isSynopsis) {
      // For synopsis, we tile by questions only (axis2 = questions)
      const questionAxis = gridAxes.find(a => a.role === 'question')
      const questionSet = entitySets?.find(es => es.id === questionAxis?.entitySetId)

      if (!questionSet) {
        console.warn('Missing question entity set for synopsis')
        return []
      }

      const questionEntityIds = questionSet.members?.map(m => m.entityId) || []

      const baseTiles = calculateTiles1D(
        questionSet.id,
        questionEntityIds,
        10 // questions per tile
      )

      console.log(
        `Matrix tiling (${matrixType}): ${baseTiles.length} tiles for ${questionEntityIds.length} questions`,
        'Tiles:', baseTiles
      )

      // Build tile index synchronously when tiles change
      const index = buildTileIndex(baseTiles, matrixId)
      console.log('[MatrixGrid] Built tile index with', index.size, 'cell keys')

      // Update ref immediately (synchronous, no re-render)
      tileIndexRef.current = index

      return baseTiles
    }

    // Standard 2D matrices: Grid axes define the 2D grid (DOC×QUESTION for standard, LEFT×RIGHT for correlation)
    if (gridAxes.length !== 2) {
      console.warn('Matrix must have exactly 2 grid axes')
      return []
    }

    const [axis1, axis2] = gridAxes

    const axis1Set = entitySets?.find(es => es.id === axis1.entitySetId)
    const axis2Set = entitySets?.find(es => es.id === axis2.entitySetId)

    if (!axis1Set || !axis2Set) {
      console.warn('Missing entity sets for grid axes')
      return []
    }

    // Use entity IDs - backend converts to member IDs internally
    const axis1EntityIds = axis1Set.members?.map(m => m.entityId) || []
    const axis2EntityIds = axis2Set.members?.map(m => m.entityId) || []

    const baseTiles = calculateTiles(
      axis1Set.id,
      axis2Set.id,
      axis1EntityIds,
      axis2EntityIds,
      axis1.role,
      axis2.role,
      {
        documentsPerTile: 5,
        questionsPerTile: 5
      }
    )

    // For correlation matrices with a slice filter, add the slice dimension to ALL tiles
    const finalTiles = sliceFilter
      ? baseTiles.map(tile => ({
          filters: [...tile.filters, sliceFilter]
        }))
      : baseTiles

    console.log(
      `Matrix tiling (${matrixType}): ${finalTiles.length} tiles for ${axis1EntityIds.length} ${axis1.role} × ${axis2EntityIds.length} ${axis2.role}${sliceFilter ? ' (with slice filter)' : ''}`,
      'Tiles:', finalTiles
    )

    // Build tile index synchronously when tiles change
    const index = buildTileIndex(finalTiles, matrixId)
    console.log('[MatrixGrid] Built tile index with', index.size, 'cell keys')

    // Update ref immediately (synchronous, no re-render)
    tileIndexRef.current = index

    return finalTiles
  }, [gridConfig, entitySets, matrixId, tileIndexRef, isSynopsis])

  // Extract grid axes and slice filter from config
  const { gridAxes, sliceFilter } = gridConfig
  const [axis1, axis2] = gridAxes
  const axis1Set = entitySets.find(es => es.id === axis1?.entitySetId)
  const axis2Set = axis2 ? entitySets.find(es => es.id === axis2?.entitySetId) : undefined

  const axis1MemberIds = axis1Set?.members?.map(m => m.entityId) || []
  const axis2MemberIds = axis2Set?.members?.map(m => m.entityId) || []

  // Get the current slice entity ID if we have a slice filter
  const currentSliceEntityId = sliceFilter?.entityIds[0]

  // Grid navigation with vim-style keyboard shortcuts
  // For synopsis, cols = 1 (single cell per question row)
  const { isSelected } = useGridNavigation(
    {
      rows: axis1MemberIds.length,
      cols: isSynopsis ? 1 : axis2MemberIds.length
    },
    {
      onOpenDetail: (position) => {
        setDetailSheetCell(position)
      }
    }
  )

  // Synopsis matrices: Questions as columns, Documents listed on side
  // ONE cell per question that synthesizes ALL documents
  if (isSynopsis) {
    // Calculate tile for synopsis (1D - questions only)
    const synopsisTile = tiles[0] // Synopsis uses single tile for all questions

    return (
      <div className="relative">
        <Table noWrapper>
          <TableHeader variant="blocky" className="sticky top-0 z-20">
            <TableRow variant="blocky" className="flex h-20 border-b border-border">
              {/* Corner cell - shows documents info */}
              <TableHead variant="blocky" className="w-48 sticky left-0 z-30 bg-muted border-r border-b border-border h-20 p-0">
                <span className="text-sm font-medium text-muted-foreground p-2">
                  {axis1?.entitySetName} ({axis1MemberIds.length})
                </span>
              </TableHead>

              {/* Question headers (columns) */}
              {axis2MemberIds.map((questionId) => (
                <TableHead variant="blocky"
                  key={questionId}
                  className="w-48 bg-muted border-r border-b border-border h-20 p-0"
                >
                  <EntityHeader
                    entityId={questionId}
                    entityType="question"
                    entitySetId={axis2Set?.id || 0}
                    role={axis2.role}
                    className="p-2 h-full flex flex-col justify-center"
                  />
                </TableHead>
              ))}

              {/* Add question button */}
              {axis2Set?.entityType && (
                <TableHead variant="blocky" className="w-24 p-0 bg-muted border-b border-border h-20">
                  <div className="p-2 h-full flex items-center justify-center">
                    <EntitySetAddButton
                      entityType={axis2Set.entityType}
                      entitySetId={axis2Set.id}
                    />
                  </div>
                </TableHead>
              )}
            </TableRow>
          </TableHeader>

          <TableBody variant="blocky">
            {/* Single row with cells - each cell synthesizes ALL documents */}
            {/* Only render cells if we have BOTH documents AND questions */}
            {axis1MemberIds.length > 0 && axis2MemberIds.length > 0 && (
            <TableRow variant="blocky" className="flex items-stretch border-b border-border">
              {/* Document list sidebar - shows all docs that feed into each cell */}
              <TableCell variant="blocky" className="w-48 sticky left-0 z-10 bg-muted border-r border-border p-0 flex flex-col">
                <div className="flex-1 flex flex-col">
                  {axis1MemberIds.map((docEntityId) => (
                    <div key={docEntityId} className="flex-1 border-b border-border last:border-b-0 flex items-center">
                      <EntityHeader
                        entityId={docEntityId}
                        entityType="document"
                        entitySetId={axis1Set?.id || 0}
                        role={axis1.role}
                      />
                    </div>
                  ))}
                </div>
              </TableCell>

              {/* Synopsis cells - one per question */}
              {axis2MemberIds.map((questionId, colIndex) => {
                // Cell entity refs for synopsis: only the question (docs are embedded in cell)
                const cellEntityRefs = [
                  { entitySetId: axis2Set!.id, entityId: questionId, role: axis2!.role }
                ]

                const isCellSelected = isSelected(0, colIndex)
                const isCellDetailOpen = detailSheetCell?.row === 0 && detailSheetCell?.col === colIndex

                // Load tile data on first cell
                const isFirstCell = colIndex === 0

                return (
                  <TableCell
                    variant="blocky"
                    key={questionId}
                    className="w-48 p-0 border-r border-border relative"
                  >
                    {isFirstCell && synopsisTile && (
                      <MatrixTileDataProvider
                        key={JSON.stringify(synopsisTile.filters)}
                        matrixId={matrixId}
                        filters={synopsisTile.filters}
                      />
                    )}
                    <MatrixCellFromTileCache
                      matrixId={matrixId}
                      entityRefs={cellEntityRefs}
                      isDiagonal={false}
                      isSelected={isCellSelected}
                      onReprocess={handleReprocessCell}
                      isDetailOpen={isCellDetailOpen}
                      onDetailOpenChange={(open) => {
                        if (open) {
                          setDetailSheetCell({ row: 0, col: colIndex })
                        } else {
                          setDetailSheetCell(null)
                        }
                      }}
                    />
                  </TableCell>
                )
              })}

              {/* Empty cell for add button column */}
              {axis2Set?.entityType && (
                <TableCell variant="blocky" className="w-24 bg-muted self-stretch border-r border-border" />
              )}
            </TableRow>
            )}

            {/* Add document row - always show if we have the entity type */}
            {axis1Set?.entityType && (
              <TableRow variant="blocky" className="flex border-b border-border">
                <TableCell variant="blocky" className="w-48 sticky left-0 z-10 bg-muted self-stretch border-r border-border">
                  <div className="p-2 min-h-[60px] flex items-center justify-center">
                    <EntitySetAddButton
                      entityType={axis1Set.entityType}
                      entitySetId={axis1Set.id}
                    />
                  </div>
                </TableCell>
                {/* Empty cells to align with questions */}
                {axis2MemberIds.map((questionId) => (
                  <TableCell variant="blocky" key={`add-${questionId}`} className="w-48 bg-muted self-stretch border-r border-border" />
                ))}
                {axis2Set?.entityType && (
                  <TableCell variant="blocky" className="w-24 bg-muted self-stretch border-r border-border" />
                )}
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    )
  }

  return (
    <div className="relative">
      <Table noWrapper>
        <TableHeader variant="blocky" className="sticky top-0 z-20">
          <TableRow variant="blocky" className="flex h-20 border-b border-border">
            {/* Corner cell - Display current slice item for correlation matrices, axis labels for standard */}
            <TableHead variant="blocky" className="w-48 sticky left-0 z-30 bg-muted border-r border-b border-border h-20 p-0">
              {sliceFilter && currentSliceEntityId ? (
                <EntityHeader
                  entityId={currentSliceEntityId}
                  entityType={sliceFilter.role === 'question' ? 'question' : 'document'}
                  entitySetId={sliceFilter.entitySetId}
                  role={sliceFilter.role}
                  className="p-2 h-full flex flex-col justify-center"
                />
              ) : (
                <span className="text-sm font-medium text-muted-foreground p-2">
                  {axis1?.entitySetName} / {axis2?.entitySetName}
                </span>
              )}
            </TableHead>

            {/* Axis2 headers (columns) - render based on entity type */}
            {axis2MemberIds.map((entityId) => (
              <TableHead variant="blocky"
                key={entityId}
                className="w-48 bg-muted border-r border-b border-border h-20 p-0"
              >
                <EntityHeader
                  entityId={entityId}
                  entityType={axis2Set?.entityType || 'document'}
                  entitySetId={axis2Set?.id || 0}
                  role={axis2.role}
                  className="p-2 h-full flex flex-col justify-center"
                />
              </TableHead>
            ))}

            {/* Add entity button column header */}
            {axis2Set?.entityType && (
              <TableHead variant="blocky" className="w-24 p-0 bg-muted border-b border-border h-20">
                <div className="p-2 h-full flex items-center justify-center">
                  <EntitySetAddButton
                    entityType={axis2Set.entityType}
                    entitySetId={axis2Set.id}
                  />
                </div>
              </TableHead>
            )}
          </TableRow>
        </TableHeader>

        <TableBody variant="blocky">
          {/* Axis1 rows (rows) - render based on entity type */}
          {axis1MemberIds.map((axis1EntityId, rowIndex) => {
            return (
              <TableRow key={axis1EntityId} variant="blocky" className="h-auto flex border-b border-border">
                <TableCell variant="blocky" className="w-48 sticky left-0 z-10 bg-muted self-stretch border-r border-border p-0">
                  <EntityHeader
                    entityId={axis1EntityId}
                    entityType={axis1Set?.entityType || 'document'}
                    entitySetId={axis1Set?.id || 0}
                    role={axis1.role}
                  />
                </TableCell>

                {/* Matrix cells - iterate by axis2 entity member IDs */}
                {axis2MemberIds.map((axis2EntityId, colIndex) => {
                  // Build all entity refs for this cell
                  const cellEntityRefs = [
                    { entitySetId: axis1Set!.id, entityId: axis1EntityId, role: axis1!.role },
                    { entitySetId: axis2Set!.id, entityId: axis2EntityId, role: axis2!.role },
                    // Include slice dimension for correlation matrices
                    ...(sliceFilter ? [{
                      entitySetId: sliceFilter.entitySetId,
                      entityId: sliceFilter.entityIds[0],
                      role: sliceFilter.role
                    }] : [])
                  ]

                  // Check if this cell is selected (vim-style navigation)
                  const isCellSelected = isSelected(rowIndex, colIndex)

                  // Check if this cell's detail sheet should be open
                  const isCellDetailOpen = detailSheetCell?.row === rowIndex && detailSheetCell?.col === colIndex

                  // Check if this is a diagonal cell: any 2 refs share same entitySetId AND entityId
                  const isDiagonal = (matrixType === 'cross_correlation' || matrixType === 'generic_correlation') &&
                    cellEntityRefs.some((ref1, i) =>
                      cellEntityRefs.some((ref2, j) =>
                        i !== j &&
                        ref1.entitySetId === ref2.entitySetId &&
                        ref1.entityId === ref2.entityId
                      )
                    )

                  // Find if this cell is a corner of any tile (must match role AND entity set)
                  const isTopLeft = tiles.find(t => {
                    const axis1Filter = t.filters.find(f => f.entitySetId === axis1Set?.id && f.role === axis1.role)
                    const axis2Filter = t.filters.find(f => f.entitySetId === axis2Set?.id && f.role === axis2.role)
                    return axis1Filter?.entityIds[0] === axis1EntityId &&
                           axis2Filter?.entityIds[0] === axis2EntityId
                  })
                  const isBottomRight = tiles.find(t => {
                    const axis1Filter = t.filters.find(f => f.entitySetId === axis1Set?.id && f.role === axis1.role)
                    const axis2Filter = t.filters.find(f => f.entitySetId === axis2Set?.id && f.role === axis2.role)
                    return axis1Filter?.entityIds[axis1Filter.entityIds.length - 1] === axis1EntityId &&
                           axis2Filter?.entityIds[axis2Filter.entityIds.length - 1] === axis2EntityId
                  })

                  return (
                    <TableCell variant="blocky"
                      key={`${axis1EntityId}-${axis2EntityId}`}
                      className="w-48 p-0 self-stretch border-r border-border relative"
                      data-cell-position={`${rowIndex}-${colIndex}`}
                    >
                      {/* Render tile providers at corners */}
                      {isTopLeft && (
                        <MatrixTileDataProvider
                          key={JSON.stringify(isTopLeft.filters)}
                          matrixId={matrixId}
                          filters={isTopLeft.filters}
                        />
                      )}
                      {isBottomRight && (
                        <MatrixTileDataProvider
                          key={JSON.stringify(isBottomRight.filters)}
                          matrixId={matrixId}
                          filters={isBottomRight.filters}
                        />
                      )}
                      <MatrixCellFromTileCache
                        matrixId={matrixId}
                        entityRefs={cellEntityRefs}
                        isDiagonal={isDiagonal}
                        isSelected={isCellSelected}
                        onReprocess={handleReprocessCell}
                        isDetailOpen={isCellDetailOpen}
                        onDetailOpenChange={(open) => {
                          if (open) {
                            setDetailSheetCell({ row: rowIndex, col: colIndex })
                          } else {
                            setDetailSheetCell(null)
                          }
                        }}
                      />
                    </TableCell>
                  )
                })}

                {/* Empty cell to align with axis2 add buttons */}
                {(axis2Set?.entityType === 'question' || axis2Set?.entityType === 'document') && (
                  <TableCell variant="blocky" className="w-24 bg-muted self-stretch border-r border-border">
                  </TableCell>
                )}
              </TableRow>
            )
          })}

          {/* Add entity row (if axis1 has an entity type) */}
          {axis1Set?.entityType && (
            <TableRow variant="blocky" className="flex border-b border-border">
              <TableCell variant="blocky" className="w-48 sticky left-0 z-10 bg-muted self-stretch border-r border-border">
                <div className="p-2 min-h-[60px] flex items-center justify-center">
                  <EntitySetAddButton
                    entityType={axis1Set.entityType}
                    entitySetId={axis1Set.id}
                  />
                </div>
              </TableCell>

              {/* Empty cells to align with axis2 */}
              {axis2MemberIds.map((entityId) => (
                <TableCell variant="blocky"
                  key={`add-${entityId}`}
                  className="w-48 bg-muted self-stretch border-r border-border"
                >
                </TableCell>
              ))}

              {/* Empty cell to align with axis2 add buttons */}
              {axis2Set?.entityType && (
                <TableCell variant="blocky" className="w-24 bg-muted self-stretch border-r border-border">
                </TableCell>
              )}
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}