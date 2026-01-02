import { createFileRoute, redirect } from '@tanstack/react-router'
import { z } from 'zod'
import { WorkspaceSheets } from '@/components/workspace-sheets'

export const workspaceSearchSchema = z.object({
  matrix: z.number().optional(),
})

export type WorkspaceSearch = z.infer<typeof workspaceSearchSchema>

export const Route = createFileRoute('/workspaces/$workspaceId')({
  validateSearch: workspaceSearchSchema,
  beforeLoad: async ({ context }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({
        to: '/landing',
      })
    }
  },
  component: WorkspaceDetail,
})

function WorkspaceDetail() {
  const { workspaceId } = Route.useParams()

  return (
    <div className="h-screen flex flex-col bg-muted">
      <div className="flex-1 overflow-hidden">
        <WorkspaceSheets workspaceId={workspaceId} />
      </div>
    </div>
  )
}