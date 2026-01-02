import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Plus } from "lucide-react"
import { WorkspaceCreateDialog } from './workspace-create-dialog'

export function WorkspaceCreateButton() {
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  return (
    <>
      <Button
        onClick={() => setIsDialogOpen(true)}
        className="flex items-center gap-2"
        variant="default"
        style="blocky"
      >
        <Plus className="h-4 w-4" />
        Create Workspace
      </Button>

      <WorkspaceCreateDialog
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
      />
    </>
  )
}