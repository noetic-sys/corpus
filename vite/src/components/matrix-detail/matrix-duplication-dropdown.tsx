import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Copy } from "lucide-react"
import { cn } from "@/lib/utils"
import { useDuplicateMatrix } from './hooks/use-duplicate-matrix'
import { MatrixDuplicationForm } from './matrix-duplication-form'
import { useMatrixContext } from './context/matrix-context'

interface MatrixDuplicationDropdownProps {
  matrixId: number
  matrixName: string
}

export function MatrixDuplicationDropdown({ matrixId, matrixName }: MatrixDuplicationDropdownProps) {
  const [isFormOpen, setIsFormOpen] = useState(false)
  const { duplicateMatrix, isDuplicating } = useDuplicateMatrix()
  const { entitySets } = useMatrixContext()

  const handleDuplicate = async (formData: {
    entitySetIds: number[]
    name: string
    description?: string
    templateVariableOverrides?: Array<{
      templateVariableId: number
      newValue: string
    }>
  }) => {
    await duplicateMatrix(matrixId, {
      name: formData.name,
      description: formData.description,
      entitySetIds: formData.entitySetIds,
      templateVariableOverrides: formData.templateVariableOverrides,
    })
    setIsFormOpen(false)
  }

  return (
    <>
      <Button
        variant="outline"
        style="blocky"
        size="sm"
        disabled={isDuplicating}
        className="h-8"
        onClick={() => setIsFormOpen(true)}
      >
        <Copy className={cn("mr-2 h-4 w-4", isDuplicating && "animate-pulse")} />
        Duplicate
      </Button>

      <MatrixDuplicationForm
        open={isFormOpen}
        onOpenChange={setIsFormOpen}
        matrixId={matrixId}
        matrixName={matrixName}
        entitySets={entitySets}
        onSubmit={handleDuplicate}
        isLoading={isDuplicating}
      />
    </>
  )
}