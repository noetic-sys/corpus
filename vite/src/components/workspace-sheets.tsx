import { useState, Suspense, useRef, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getWorkspaceApiV1WorkspacesWorkspaceIdGet,
  getMatricesByWorkspace,
} from '@/client'
import { apiClient } from '@/lib/api'
import { MatrixTabContent } from '@/components/matrix-tab-content'
import { MatrixCreateDialog } from '@/components/workspaces/matrix-create-dialog'
import { useWorkspaceTabs } from '@/components/workspaces/use-workspace-tabs'
import { WorkflowsTabContent } from '@/components/workflows/workflows-tab-content'
import { WorkspaceGettingStarted } from '@/components/workspaces/workspace-getting-started'
import { WorkspaceSidebar, type WorkspaceSidebarHandle } from '@/components/workspace-sidebar'
import { CommandPalette } from '@/components/command-palette'

interface WorkspaceSheetsProps {
  workspaceId: string
}

// Keep track of recently viewed tabs (last 3)
const MAX_MOUNTED_TABS = 3

export function WorkspaceSheets({ workspaceId }: WorkspaceSheetsProps) {
  const { getToken } = useAuth()
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const queryClient = useQueryClient()
  const mountedTabsRef = useRef<number[]>([])
  const sidebarRef = useRef<WorkspaceSidebarHandle>(null)

  console.log(`[WorkspaceSheets] RENDER - workspaceId: ${workspaceId} at ${performance.now().toFixed(2)}ms`)

  const { data: workspace, isLoading: isWorkspaceLoading } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: async () => {
      const token = await getToken()
      const response = await getWorkspaceApiV1WorkspacesWorkspaceIdGet({
        path: { workspaceId: parseInt(workspaceId) },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })
      return response.data
    }
  })

  const { data: matrices = [], isLoading: isMatricesLoading } = useQuery({
    queryKey: ['matrices', workspaceId],
    queryFn: async () => {
      const token = await getToken()
      const response = await getMatricesByWorkspace({
        path: { workspaceId: parseInt(workspaceId) },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })
      return response.data || []
    }
  })

  const { activeTab, handleTabChange } = useWorkspaceTabs({ matrices })

  // Track which tabs to keep mounted (active + last 2 visited)
  useEffect(() => {
    if (!activeTab || activeTab === 'workflows') return

    // TypeScript now knows activeTab is a number here
    const matrixId = activeTab as number

    // Add current tab to front of list (only for matrix tabs, not workflows)
    const updated = [matrixId, ...mountedTabsRef.current.filter(id => id !== matrixId)]

    // Keep only last MAX_MOUNTED_TABS
    const toKeep = updated.slice(0, MAX_MOUNTED_TABS)
    const toUnmount = mountedTabsRef.current.filter(id => !toKeep.includes(id))

    mountedTabsRef.current = toKeep

    // Clean up cache for unmounted tabs aggressively
    toUnmount.forEach(matrixId => {
      // Remove tile cache for old tabs
      queryClient.removeQueries({
        predicate: (query) => {
          const key = query.queryKey
          return key[0] === 'matrix-tile' && key[1] === matrixId
        }
      })
    })
  }, [activeTab, queryClient])

  const handleAddMatrix = () => {
    setIsCreateDialogOpen(true)
  }

  const handleToggleSidebar = () => {
    sidebarRef.current?.toggle()
  }

  const shouldMountView = (matrixId: number) => {
    return mountedTabsRef.current.includes(matrixId) || matrixId === activeTab
  }

  if (isWorkspaceLoading || isMatricesLoading) {
    return <div className="flex items-center justify-center h-full">Loading workspace...</div>
  }

  if (!workspace) {
    return <div className="flex items-center justify-center h-full">Workspace not found</div>
  }

  return (
    <>
      <div className="h-full flex">
        {/* Sidebar */}
        <WorkspaceSidebar
          ref={sidebarRef}
          workspaceName={workspace.name}
          matrices={matrices}
          activeView={activeTab}
          onViewChange={handleTabChange}
          onAddMatrix={handleAddMatrix}
        />

        {/* Content Area */}
        <div className="flex-1 min-h-0 overflow-hidden">
          {activeTab === 'workflows' && matrices.length === 0 && (
            <WorkspaceGettingStarted onCreateMatrix={handleAddMatrix} />
          )}
          {activeTab === 'workflows' && matrices.length > 0 && (
            <WorkflowsTabContent workspaceId={parseInt(workspaceId)} />
          )}
          {matrices.map((matrix: any) => {
            const shouldMount = shouldMountView(matrix.id)
            const isActive = activeTab === matrix.id

            if (!shouldMount) return null

            return (
              <div
                key={matrix.id}
                className={isActive ? 'h-full' : 'hidden'}
              >
                <Suspense
                  fallback={<div className="flex items-center justify-center h-full">Loading matrix...</div>}
                >
                  <MatrixTabContent matrixId={matrix.id} />
                </Suspense>
              </div>
            )
          })}
        </div>
      </div>

      {/* Command Palette */}
      <CommandPalette
        matrices={matrices}
        workspaceId={workspaceId}
        onToggleSidebar={handleToggleSidebar}
        onCreateMatrix={handleAddMatrix}
      />

      <MatrixCreateDialog
        workspace={workspace}
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
      />
    </>
  )
}