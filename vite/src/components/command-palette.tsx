import { useEffect, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Grid3x3, Workflow, Plus, PanelLeftClose } from 'lucide-react'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import type { MatrixResponse } from '@/client/types.gen'

interface CommandPaletteProps {
  matrices?: MatrixResponse[]
  workspaceId?: string
  onToggleSidebar?: () => void
  onCreateMatrix?: () => void
}

export function CommandPalette({
  matrices = [],
  workspaceId,
  onToggleSidebar,
  onCreateMatrix
}: CommandPaletteProps) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      // Only trigger if NOT in an input field
      const target = e.target as HTMLElement
      const isTyping = ['INPUT', 'TEXTAREA'].includes(target?.tagName) ||
                       target?.isContentEditable

      if (!isTyping && (e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen(prev => !prev)
      }
    }

    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [])

  const handleNavigateToMatrix = (matrixId: number) => {
    if (workspaceId) {
      navigate({
        to: '/workspaces/$workspaceId',
        params: { workspaceId },
        search: { matrix: matrixId }
      })
    }
    setOpen(false)
  }

  const handleNavigateToWorkflows = () => {
    if (workspaceId) {
      navigate({
        to: '/workspaces/$workspaceId',
        params: { workspaceId },
        search: {}
      })
    }
    setOpen(false)
  }

  const handleCreateMatrix = () => {
    onCreateMatrix?.()
    setOpen(false)
  }

  const handleToggleSidebar = () => {
    onToggleSidebar?.()
    setOpen(false)
  }

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search matrices, actions..." autoFocus />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {/* Matrices */}
        {matrices.length > 0 && (
          <CommandGroup heading="Matrices">
            {matrices.map((matrix) => (
              <CommandItem
                key={matrix.id}
                onSelect={() => handleNavigateToMatrix(matrix.id)}
                value={`matrix ${matrix.name}`}
              >
                <Grid3x3 />
                <span>{matrix.name}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {/* Navigation */}
        <CommandGroup heading="Navigation">
          <CommandItem
            onSelect={handleNavigateToWorkflows}
            value="workflows navigation"
          >
            <Workflow />
            <span>Go to Workflows</span>
          </CommandItem>
        </CommandGroup>

        {/* Actions */}
        <CommandGroup heading="Actions">
          {onCreateMatrix && (
            <CommandItem
              onSelect={handleCreateMatrix}
              value="create new matrix action"
            >
              <Plus />
              <span>Create New Matrix</span>
            </CommandItem>
          )}
          {onToggleSidebar && (
            <CommandItem
              onSelect={handleToggleSidebar}
              value="toggle sidebar action"
            >
              <PanelLeftClose />
              <span>Toggle Sidebar</span>
            </CommandItem>
          )}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
