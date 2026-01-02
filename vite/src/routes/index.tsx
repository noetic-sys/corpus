import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    // Mimic frontend/app/page.tsx - redirect to workspaces
    throw redirect({
      to: '/workspaces'
    })
  },
})