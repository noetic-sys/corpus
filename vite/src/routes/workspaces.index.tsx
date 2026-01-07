import { createFileRoute, redirect } from '@tanstack/react-router'
import { WorkspaceList, WorkspaceCreateButton } from '@/components/workspace-list'

export const Route = createFileRoute('/workspaces/')({
  beforeLoad: async ({ context }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({
        to: '/landing',
      })
    }
  },
  component: WorkspacesPage,
})

// Copied directly from frontend/app/workspaces/page.tsx
function WorkspacesPage() {
  return (
    <div className="min-h-screen p-8 bg-muted">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl font-semibold text-text-primary">Workspaces</h1>
          <WorkspaceCreateButton />
        </div>
        <p className="text-sm text-muted-foreground mb-6">
          Organize work by project, deal, or client.
        </p>
        <WorkspaceList />
      </div>
    </div>
  )
}