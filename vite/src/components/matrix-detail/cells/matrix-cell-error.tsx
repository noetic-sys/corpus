import { RotateCw } from "lucide-react"
import { cn } from "@/lib/utils"

interface MatrixCellErrorProps {
  onRetry?: () => void
  isSelected?: boolean
}

export function MatrixCellError({ onRetry, isSelected = false }: MatrixCellErrorProps) {
  return (
    <div className={cn(
      "w-full h-full bg-status-error-bg/20 flex items-center justify-center",
      isSelected && "ring-2 ring-blue-500 ring-inset"
    )}>
      <button
        onClick={onRetry}
        className="p-1 hover:bg-status-error-bg/40 rounded-sm transition-colors"
        title="Retry loading cell"
      >
        <RotateCw className="h-3 w-3 text-status-error" />
      </button>
    </div>
  )
}
