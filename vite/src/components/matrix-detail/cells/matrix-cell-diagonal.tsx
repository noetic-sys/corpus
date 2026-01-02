import { Minus } from "lucide-react"
import { cn } from "@/lib/utils"

interface MatrixCellDiagonalProps {
  isSelected?: boolean
}

export function MatrixCellDiagonal({ isSelected = false }: MatrixCellDiagonalProps) {
  return (
    <div className={cn(
      "w-full h-full bg-surface-subtle flex items-center justify-center",
      isSelected && "ring-2 ring-blue-500 ring-inset"
    )}>
      <Minus className="h-4 w-4 text-text-tertiary" />
    </div>
  )
}
