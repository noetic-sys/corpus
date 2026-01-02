import { useState, useEffect, useCallback } from 'react'

interface GridDimensions {
  rows: number
  cols: number
}

interface GridPosition {
  row: number
  col: number
}

interface NavigationOptions {
  verticalPageSize?: number
  horizontalPageSize?: number
  onNavigate?: (position: GridPosition) => void
  onOpenDetail?: (position: GridPosition) => void
  autoScroll?: boolean
  cellSelector?: (row: number, col: number) => string
}

const DEFAULT_OPTIONS: Required<NavigationOptions> = {
  verticalPageSize: 10,
  horizontalPageSize: 10,
  onNavigate: () => {},
  onOpenDetail: () => {},
  autoScroll: true,
  cellSelector: (row, col) => `[data-cell-position="${row}-${col}"]`
}

export function useGridNavigation(
  dimensions: GridDimensions,
  options: NavigationOptions = {}
) {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  const [selectedCell, setSelectedCell] = useState<GridPosition | null>(null)
  const [lastKey, setLastKey] = useState<string | null>(null)

  // Auto-scroll selected cell into view
  useEffect(() => {
    if (selectedCell && opts.autoScroll) {
      const cellElement = document.querySelector(
        opts.cellSelector(selectedCell.row, selectedCell.col)
      )
      if (cellElement) {
        cellElement.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
          inline: 'center'
        })
      }
    }
  }, [selectedCell, opts])

  // Call onNavigate callback
  useEffect(() => {
    if (selectedCell) {
      opts.onNavigate(selectedCell)
    }
  }, [selectedCell, opts])

  const handleNavigation = useCallback((e: KeyboardEvent) => {
    const target = e.target as HTMLElement
    const isTyping = ['INPUT', 'TEXTAREA'].includes(target?.tagName) ||
                     target?.isContentEditable
    const inDialog = target?.closest('[role="dialog"]')

    if (isTyping || inDialog) return

    const key = e.key
    const maxRow = dimensions.rows - 1
    const maxCol = dimensions.cols - 1

    // Initialize selection to (0, 0) if none selected
    const current = selectedCell || { row: 0, col: 0 }
    let newRow = current.row
    let newCol = current.col
    let handled = false

    // Handle 'gg' for first row (must come before other g handling)
    if (lastKey === 'g' && key === 'g') {
      e.preventDefault()
      newRow = 0
      handled = true
      setLastKey(null)
    }
    // Track 'g' key for 'gg' sequence
    else if (key === 'g' && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault()
      setLastKey('g')
      setTimeout(() => setLastKey(null), 1000) // Reset after 1s
      return // Don't process further
    }
    // G (shift+g) - go to last row
    else if (key === 'G' && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault()
      newRow = maxRow
      handled = true
      setLastKey(null)
    }
    // Basic navigation (no Ctrl/Meta/Alt)
    else if (!e.metaKey && !e.ctrlKey && !e.altKey) {
      switch (key) {
        case 'h': // left
          newCol = Math.max(0, current.col - 1)
          handled = true
          break
        case 'j': // down
          newRow = Math.min(maxRow, current.row + 1)
          handled = true
          break
        case 'k': // up
          newRow = Math.max(0, current.row - 1)
          handled = true
          break
        case 'l': // right
          newCol = Math.min(maxCol, current.col + 1)
          handled = true
          break
        case '0': // first column
          newCol = 0
          handled = true
          break
        case '$': // last column (shift+4)
          newCol = maxCol
          handled = true
          break
        case 'w': // page right
          newCol = Math.min(maxCol, current.col + opts.horizontalPageSize)
          handled = true
          break
        case 'b': // page left
          newCol = Math.max(0, current.col - opts.horizontalPageSize)
          handled = true
          break
        case 'W': // big jump right (shift+w)
          newCol = Math.min(maxCol, current.col + opts.horizontalPageSize * 2)
          handled = true
          break
        case 'B': // big jump left (shift+b)
          newCol = Math.max(0, current.col - opts.horizontalPageSize * 2)
          handled = true
          break
        case 'Enter':
        case ' ': // Space key
          // Open detail for current cell
          e.preventDefault()
          opts.onOpenDetail(current)
          setLastKey(null)
          return // Don't update position
      }

      if (handled) {
        e.preventDefault()
        setLastKey(null)
      }
    }
    // Vertical page jumps (Ctrl+d/u/f/b)
    else if (e.ctrlKey && !e.metaKey && !e.altKey) {
      switch (key.toLowerCase()) {
        case 'd': // page down
          newRow = Math.min(maxRow, current.row + opts.verticalPageSize)
          handled = true
          break
        case 'u': // page up
          newRow = Math.max(0, current.row - opts.verticalPageSize)
          handled = true
          break
        case 'f': // full page down
          newRow = Math.min(maxRow, current.row + opts.verticalPageSize * 2)
          handled = true
          break
        case 'b': // full page up
          newRow = Math.max(0, current.row - opts.verticalPageSize * 2)
          handled = true
          break
      }

      if (handled) {
        e.preventDefault()
        setLastKey(null)
      }
    }

    if (handled) {
      setSelectedCell({ row: newRow, col: newCol })
    }
  }, [selectedCell, lastKey, dimensions, opts.verticalPageSize, opts.horizontalPageSize, opts.onOpenDetail])

  // Register keyboard event listener
  useEffect(() => {
    window.addEventListener('keydown', handleNavigation)
    return () => window.removeEventListener('keydown', handleNavigation)
  }, [handleNavigation])

  return {
    selectedCell,
    setSelectedCell,
    isSelected: (row: number, col: number) =>
      selectedCell?.row === row && selectedCell?.col === col
  }
}
