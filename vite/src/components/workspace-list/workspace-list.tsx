import { Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { getWorkspacesApiV1WorkspacesGet } from '@/client'
import { apiClient } from '@/lib/api'
import { WorkspaceListItem } from './workspace-list-item'
import type { WorkspaceResponse } from '@/client'

// Convert from server-side to client-side with TanStack Query
function useWorkspaces() {
  const { getToken, isAuthenticated } = useAuth()

  return useQuery({
    queryKey: ['workspaces'],
    queryFn: async (): Promise<WorkspaceResponse[]> => {
      try {
        // Get Auth0 access token
        const token = await getToken()

        const response = await getWorkspacesApiV1WorkspacesGet({
          headers: {
            authorization: `Bearer ${token}`
          },
          client: apiClient
        })

        if (response.error) {
          console.error('API error:', response.error)
          return []
        }

        return response.data || []
      } catch (error) {
        console.error('Error fetching workspaces:', error)
        return []
      }
    },
    enabled: isAuthenticated // Only run query when user is authenticated
  })
}

export function WorkspaceList() {
  const { data: workspaces = [], isLoading, error } = useWorkspaces()

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground text-lg">Loading workspaces...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive text-lg">Error loading workspaces</p>
      </div>
    )
  }

  if (workspaces.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground text-lg">No workspaces found</p>
      </div>
    )
  }

  return (
    <div className="grid gap-2">
      {workspaces.map((workspace) => (
        <Link
          key={workspace.id}
          to="/workspaces/$workspaceId"
          params={{ workspaceId: workspace.id.toString() }}
          className="block"
        >
          <WorkspaceListItem workspace={workspace} />
        </Link>
      ))}
    </div>
  )
}