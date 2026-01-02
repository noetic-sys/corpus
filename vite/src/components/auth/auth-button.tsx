import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { LogIn, LogOut, User } from 'lucide-react'

export function AuthButton() {
  const { user, isLoading, login, logout } = useAuth()

  if (isLoading) {
    return (
      <Button variant="ghost" disabled>
        Loading...
      </Button>
    )
  }

  if (user) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 text-sm">
          <User className="w-4 h-4" />
          <span>{user.name || user.email}</span>
        </div>
        <Button
          variant="outline"
          style="blocky"
          size="sm"
          onClick={() => logout()}
        >
          <LogOut className="w-4 h-4 mr-2" />
          Log out
        </Button>
      </div>
    )
  }

  return (
    <Button style="blocky" onClick={() => login()}>
      <LogIn className="w-4 h-4 mr-2" />
      Sign in with Google
    </Button>
  )
}
