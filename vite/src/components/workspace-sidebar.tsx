import { useState, useEffect, useImperativeHandle, forwardRef } from 'react'
import { ChevronLeft, ChevronRight, Grid3x3, Workflow, Calendar, LayoutGrid, Settings, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import type { MatrixResponse } from '@/client/types.gen'

interface WorkspaceSidebarProps {
  workspaceName: string
  matrices: MatrixResponse[]
  activeView: 'workflows' | number
  onViewChange: (view: 'workflows' | number) => void
  onAddMatrix: () => void
}

export interface WorkspaceSidebarHandle {
  toggle: () => void
}

const SIDEBAR_COLLAPSED_KEY = 'workspace-sidebar-collapsed'

export const WorkspaceSidebar = forwardRef<WorkspaceSidebarHandle, WorkspaceSidebarProps>(({
  workspaceName,
  matrices,
  activeView,
  onViewChange,
  onAddMatrix
}, ref) => {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
    return stored ? stored === 'true' : false
  })

  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, isCollapsed.toString())
  }, [isCollapsed])

  // Expose toggle function via ref
  useImperativeHandle(ref, () => ({
    toggle: () => setIsCollapsed(prev => !prev)
  }))

  // Keyboard shortcut: Cmd/Ctrl + \
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only trigger if NOT in an input field or dialog
      const target = e.target as HTMLElement
      const isTyping = ['INPUT', 'TEXTAREA'].includes(target?.tagName) ||
                       target?.isContentEditable
      const inDialog = target?.closest('[role="dialog"]')

      if (!isTyping && !inDialog && (e.metaKey || e.ctrlKey) && e.key === '\\') {
        e.preventDefault()
        setIsCollapsed(prev => !prev)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const NavButton = ({
    active,
    onClick,
    icon: Icon,
    label,
    disabled = false,
    badge
  }: {
    active?: boolean
    onClick: () => void
    icon: any
    label: string
    disabled?: boolean
    badge?: string
  }) => {
    const button = (
      <Button
        variant={active ? 'secondary' : 'ghost'}
        size="sm"
        onClick={onClick}
        disabled={disabled}
        className={cn(
          'w-full justify-start',
          isCollapsed && 'justify-center px-2',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <Icon className="h-4 w-4 flex-shrink-0" />
        {!isCollapsed && <span className="ml-2 truncate">{label}</span>}
        {!isCollapsed && badge && (
          <span className="ml-auto text-xs text-muted-foreground">{badge}</span>
        )}
      </Button>
    )

    if (isCollapsed) {
      return (
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              {button}
            </TooltipTrigger>
            <TooltipContent side="right">
              <p>{label}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )
    }

    return button
  }

  return (
    <div
      className={cn(
        'h-full bg-background border-r transition-all duration-200 flex flex-col',
        isCollapsed ? 'w-12' : 'w-56'
      )}
    >
      {/* Header */}
      <div className="h-10 border-b flex items-center justify-between px-3 flex-shrink-0">
        {!isCollapsed && (
          <span className="text-sm font-medium truncate">{workspaceName}</span>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 flex-shrink-0 ml-auto"
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Navigation */}
      <ScrollArea className="flex-1">
        <nav className="p-2 space-y-1">
          {/* Matrices Section */}
          <div>
            {!isCollapsed && (
              <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                Matrices
              </div>
            )}
            {matrices.map((matrix) => (
              <NavButton
                key={matrix.id}
                active={activeView === matrix.id}
                onClick={() => onViewChange(matrix.id)}
                icon={Grid3x3}
                label={matrix.name}
              />
            ))}
            <NavButton
              onClick={onAddMatrix}
              icon={Plus}
              label="New Matrix"
            />
          </div>

          <Separator className="my-2" />

          {/* Workflows */}
          <NavButton
            active={activeView === 'workflows'}
            onClick={() => onViewChange('workflows')}
            icon={Workflow}
            label="Workflows"
          />

          {/* Future: Timeline */}
          <NavButton
            disabled
            onClick={() => {}}
            icon={Calendar}
            label="Timeline"
            badge="Soon"
          />

          {/* Future: Board */}
          <NavButton
            disabled
            onClick={() => {}}
            icon={LayoutGrid}
            label="Board"
            badge="Soon"
          />
        </nav>
      </ScrollArea>

      {/* Footer */}
      <div className="border-t p-2 flex-shrink-0">
        <NavButton
          onClick={() => {}}
          icon={Settings}
          label="Settings"
        />
      </div>
    </div>
  )
})

WorkspaceSidebar.displayName = 'WorkspaceSidebar'
