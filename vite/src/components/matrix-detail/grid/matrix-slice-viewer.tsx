import { useRef, useEffect } from 'react'
import { toast } from 'sonner'
import { MatrixGrid } from './matrix-grid'
import { MatrixHeader } from '../matrix-header'
import { QuestionCreateClient } from '../interactive/question-create-client'
import { useSliceNavigation } from './use-slice-navigation'
import { useMatrixContext } from '../context/matrix-context'
import { computeMatrixDimensions } from '../utils/matrix-dimensions'
import type { MatrixType } from '@/client/types.gen'
import type { SliceItemComboboxHandle } from './slice-item-combobox'
import type { SliceAxisComboboxHandle } from './slice-axis-combobox'

/**
 * Unified matrix viewer with slicing support.
 *
 * All matrices are rendered as 2D grids. Correlation matrices have a slice axis for navigation.
 * Standard matrices have no slice axis (renders directly as 2D).
 *
 * Renders header + grid together so slice controls can be passed to header.
 */
export function MatrixSliceViewer() {
  const { matrixId, matrixType, entitySets, aiProviders, aiModels, sparseView, setSparseView } = useMatrixContext()
  const sliceItemComboboxRef = useRef<SliceItemComboboxHandle>(null)
  const sliceAxisComboboxRef = useRef<SliceAxisComboboxHandle>(null)

  // Don't render until we have data
  if (!matrixType || !entitySets || entitySets.length === 0) {
    return <div className="flex items-center justify-center h-full">Loading...</div>
  }

  const dimensions = computeMatrixDimensions(matrixType as MatrixType, entitySets)

  const {
    currentSliceIndex,
    setCurrentSliceIndex,
    activeSliceAxisRole,
    allAxes,
    canSwapAxes,
    currentSliceAxis,
    currentGridAxes,
    sliceFilter,
    sliceOptions,
    handleAxisChange
  } = useSliceNavigation()

  // Keyboard shortcuts for matrix operations
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only trigger if NOT in an input field or dialog
      const target = e.target as HTMLElement
      const isTyping = ['INPUT', 'TEXTAREA'].includes(target?.tagName) ||
                       target?.isContentEditable
      const inDialog = target?.closest('[role="dialog"]')

      if (isTyping || inDialog) return

      // Don't trigger if modifier keys are pressed
      if (e.metaKey || e.ctrlKey || e.altKey) return

      switch (e.key.toLowerCase()) {
        case 'd':
          // Toggle dense/sparse view
          e.preventDefault()
          setSparseView(!sparseView)
          toast.success(`Switched to ${!sparseView ? 'sparse' : 'dense'} view`)
          break

        case 'v':
          // Open slice value selector
          if (dimensions.sliceAxis && sliceItemComboboxRef.current) {
            e.preventDefault()
            sliceItemComboboxRef.current.open()
          }
          break

        case 's':
          // Open slice axis selector (only if can swap axes)
          if (dimensions.sliceAxis && canSwapAxes && sliceAxisComboboxRef.current) {
            e.preventDefault()
            sliceAxisComboboxRef.current.open()
          }
          break

        default:
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [sparseView, setSparseView, dimensions, canSwapAxes])

  // If no slice axis, render header + grid (standard matrix, no slice controls)
  if (!dimensions.sliceAxis) {
    return (
      <>
        <div className="flex-shrink-0">
          <MatrixHeader />
        </div>
        <div className="flex-1 min-h-0 overflow-auto">
          <div className="min-w-max">
            <MatrixGrid />
          </div>
        </div>
      </>
    )
  }

  // Has slice axis (correlation matrix) - show navigation
  if (!currentSliceAxis || currentSliceAxis.count === 0) {
    // Empty slice axis - show creation UI based on entity type
    if (currentSliceAxis?.role === 'question') {
      return (
        <>
          <div className="flex-shrink-0">
            <MatrixHeader />
          </div>
          <div className="flex-1 min-h-0 overflow-auto">
            {/* Grid-like layout matching standard matrix */}
            <div className="min-w-max">
              <table className="border-collapse">
                <thead>
                  <tr>
                    {/* Corner cell with question create */}
                    <th className="sticky left-0 z-20 border-r border-b border-border p-2 min-w-[180px]">
                      <QuestionCreateClient
                        matrixId={matrixId}
                        entitySetId={currentSliceAxis.entitySetId}
                        aiProviders={aiProviders}
                        aiModels={aiModels}
                      />
                    </th>
                    {/* Ghost column headers (questions will go here) */}
                    {[1, 2, 3].map((i) => (
                      <th key={i} className="border-r border-b border-border p-2 min-w-[200px] bg-muted/10">
                        <div className="h-8 flex items-center justify-center">
                          <div className="w-24 h-2 bg-muted-foreground/10 rounded" />
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {/* Ghost rows (documents will go here) */}
                  {[1, 2, 3].map((row) => (
                    <tr key={row}>
                      <td className="sticky left-0 z-10 bg-muted/10 border-r border-b border-border p-2">
                        <div className="h-10 flex items-center">
                          <div className="w-28 h-2 bg-muted-foreground/10 rounded" />
                        </div>
                      </td>
                      {[1, 2, 3].map((col) => (
                        <td key={col} className="border-r border-b border-border p-2 bg-background">
                          <div className="h-10 flex items-center justify-center">
                            <div className="w-32 h-2 bg-muted-foreground/5 rounded" />
                          </div>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )
    }

    return (
      <div className="p-4 text-muted-foreground">
        No {currentSliceAxis?.entitySetName.toLowerCase()} available for this correlation matrix.
      </div>
    )
  }

  // Render header with slice controls + grid
  return (
    <>
      <div className="flex-shrink-0">
        <MatrixHeader
          sliceControls={{
            canSwapAxes,
            allAxes: allAxes.filter((axis): axis is NonNullable<typeof axis> => axis !== null),
            activeSliceAxisRole,
            handleAxisChange,
            currentSliceAxis,
            sliceOptions,
            currentSliceIndex,
            setCurrentSliceIndex,
            sliceItemComboboxRef,
            sliceAxisComboboxRef
          }}
        />
      </div>
      <div className="flex-1 min-h-0 overflow-auto">
        <div className="min-w-max">
          <MatrixGrid
            config={{
              gridAxes: currentGridAxes.filter((axis): axis is NonNullable<typeof axis> => axis !== null),
              sliceFilter
            }}
          />
        </div>
      </div>
    </>
  )
}
