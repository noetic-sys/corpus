import { useEffect } from 'react'
import { createRootRouteWithContext, Outlet, useNavigate, useLocation } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'
import { Toaster } from 'sonner'
import { AuthHeader } from '@/components/auth'
import { ChatProvider, Chat } from '@/components/chat'
import { useAuth } from '@/hooks/useAuth'
import type { AuthContextType } from '@/hooks/useAuth'

interface RouterContext {
  auth: AuthContextType
}

function RootComponent() {
  const { isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (isLoading) return

    const isOnLanding = location.pathname === '/landing' || location.pathname === '/'
    const isOnProtectedRoute = location.pathname.startsWith('/workspaces')

    if (isAuthenticated && isOnLanding) {
      navigate({ to: '/workspaces' })
    } else if (!isAuthenticated && isOnProtectedRoute) {
      navigate({ to: '/landing' })
    }
  }, [isAuthenticated, isLoading, location.pathname, navigate])

  return (
    <ChatProvider>
      <AuthHeader />
      <Outlet />
      <Chat />
      <Toaster />
      {import.meta.env.DEV && <TanStackRouterDevtools />}
    </ChatProvider>
  )
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootComponent,
})