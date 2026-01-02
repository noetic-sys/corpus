import { useRouter } from '@tanstack/react-router'
import { Button } from './button'
import { ArrowLeft } from 'lucide-react'

interface BackButtonProps {
  /** Custom behavior - if not provided, defaults to going back in history */
  onClick?: () => void
  /** Custom label - defaults to "Back to Matrices" */
  label?: string
  /** Force navigation to matrices list instead of browser back */
  toMatricesList?: boolean
}

export function BackButton({ onClick, label = "Back to Matrices", toMatricesList = false }: BackButtonProps) {
  const router = useRouter()

  const handleClick = () => {
    if (onClick) {
      onClick()
    } else if (toMatricesList) {
      router.navigate({ to: '/workspaces' })
    } else {
      router.history.back()
    }
  }

  return (
    <Button 
      onClick={handleClick} 
      variant="ghost" 
      size="sm"
      className="h-7 text-xs"
    >
      <ArrowLeft className="mr-1 h-3 w-3" />
      {label}
    </Button>
  )
}