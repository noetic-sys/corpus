import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { useState } from "react"
import type { EntitySetResponse } from "@/client"

interface EntitySetSelectorDialogProps {
  isOpen: boolean
  onClose: () => void
  entitySets: EntitySetResponse[]
  title: string
  description: string
  onSelect: (entitySetId: number) => void
}

export function EntitySetSelectorDialog({
  isOpen,
  onClose,
  entitySets,
  title,
  description,
  onSelect
}: EntitySetSelectorDialogProps) {
  const [selectedEntitySetId, setSelectedEntitySetId] = useState<number | null>(
    entitySets.length > 0 ? entitySets[0].id : null
  )

  const handleSubmit = () => {
    if (selectedEntitySetId !== null) {
      onSelect(selectedEntitySetId)
      onClose()
    }
  }

  const handleCancel = () => {
    setSelectedEntitySetId(entitySets.length > 0 ? entitySets[0].id : null)
    onClose()
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleCancel}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <RadioGroup
          value={selectedEntitySetId?.toString() || ""}
          onValueChange={(value) => setSelectedEntitySetId(parseInt(value, 10))}
          className="space-y-3 py-4"
        >
          {entitySets.map((entitySet) => (
            <div key={entitySet.id} className="flex items-center space-x-3">
              <RadioGroupItem
                value={entitySet.id.toString()}
                id={`entity-set-${entitySet.id}`}
                style="blocky"
              />
              <Label
                htmlFor={`entity-set-${entitySet.id}`}
                className="flex-1 cursor-pointer"
              >
                <div className="font-medium">{entitySet.name}</div>
                <div className="text-sm text-muted-foreground">
                  {entitySet.members?.length || 0} members
                </div>
              </Label>
            </div>
          ))}
        </RadioGroup>

        <DialogFooter>
          <Button variant="outline" style="blocky" onClick={handleCancel}>
            Cancel
          </Button>
          <Button
            style="blocky"
            onClick={handleSubmit}
            disabled={selectedEntitySetId === null}
          >
            Select
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
