import { CellLoadingSpinner } from "./cell-loading-spinner"
import { cn } from "@/lib/utils"

interface MatrixCellLoadingProps {
  isSelected?: boolean
}

export function MatrixCellLoading({ isSelected = false }: MatrixCellLoadingProps) {
  return (
    <div className={cn(
      "w-full h-full p-2 relative bg-muted/10",
      isSelected && "ring-2 ring-blue-500 ring-inset"
    )}>
      <div className="absolute top-1 right-1">
        <CellLoadingSpinner />
      </div>
      <div className="w-full h-full" />
    </div>
  )
}
