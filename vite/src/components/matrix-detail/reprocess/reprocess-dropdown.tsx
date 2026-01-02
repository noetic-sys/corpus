import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import { RefreshCw } from "lucide-react"
import type { ReactNode } from "react"

export interface ReprocessAction {
  id: string
  label: string
  onClick: () => void | Promise<void>
  disabled?: boolean
  isLoading?: boolean
  icon?: ReactNode
}

interface ReprocessDropdownProps {
  children: ReactNode
  actions: ReprocessAction[]
}

export function ReprocessDropdown({ children, actions }: ReprocessDropdownProps) {
  // Wrapper to properly handle async onClick handlers
  const handleClick = (action: ReprocessAction) => {
    const result = action.onClick()
    // If onClick returns a promise, catch any rejections
    // The hooks already handle errors with toast, this just ensures the promise is handled
    if (result instanceof Promise) {
      result.catch(() => {
        // Error already handled by hook's catch block with toast
      })
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {children}
      </DropdownMenuTrigger>
      <DropdownMenuContent variant="blocky">
        {actions.map((action) => {
          const IconComponent = action.icon || <RefreshCw className={cn("mr-2 h-4 w-4", action.isLoading && "animate-spin")} />

          return (
            <DropdownMenuItem
              key={action.id}
              onClick={() => handleClick(action)}
              disabled={action.disabled}
            >
              {action.isLoading && action.icon ? (
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                IconComponent
              )}
              {action.isLoading ? `${action.label}...` : action.label}
            </DropdownMenuItem>
          )
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}