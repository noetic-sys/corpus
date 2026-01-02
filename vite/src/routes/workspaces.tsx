import { createFileRoute, Outlet } from '@tanstack/react-router'

export const Route = createFileRoute('/workspaces')({
  component: WorkspacesLayout,
})

function WorkspacesLayout() {
  return <Outlet />
}