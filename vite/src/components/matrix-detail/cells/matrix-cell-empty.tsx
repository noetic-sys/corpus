import { AlertTriangle } from "lucide-react"
import { cn } from "@/lib/utils"

interface MatrixCellEmptyProps {
  onRetry?: () => void
  isSelected?: boolean
}

export function MatrixCellEmpty({ onRetry, isSelected = false }: MatrixCellEmptyProps) {
  return (
    <div
      className={cn(
        "w-full h-full bg-muted/10 p-2 relative cursor-pointer hover:bg-muted/20 transition-colors",
        isSelected && "ring-2 ring-blue-500 ring-inset"
      )}
      onClick={onRetry}
      title="Click to retry loading cell"
    >
      {/* Warning icon in upper right */}
      <div className="absolute top-1 right-1">
        <AlertTriangle className="h-3 w-3 text-yellow-600" />
      </div>
      <div className="w-full h-full" />
    </div>
  )
}
