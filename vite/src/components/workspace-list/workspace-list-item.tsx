import { useState } from "react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Trash2, MoreHorizontal } from "lucide-react"
import { ReprocessDropdown, type ReprocessAction } from "../matrix-detail/reprocess/reprocess-dropdown"
import { DeleteConfirmationDialog } from "../matrix-detail/dialogs/delete-confirmation-dialog"
import { useDeleteWorkspace } from "./hooks/use-delete-workspace"
import type { WorkspaceResponse } from '@/client'

interface WorkspaceListItemProps {
  workspace: WorkspaceResponse
}

export function WorkspaceListItem({ workspace }: WorkspaceListItemProps) {
  const { deleteWorkspace, isDeleting } = useDeleteWorkspace()
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  const handleDeleteClick = (e?: React.MouseEvent) => {
    console.log("clicked")
    e?.preventDefault()
    e?.stopPropagation()
    setShowDeleteDialog(true)
  }

  const handleConfirmDelete = async () => {
    await deleteWorkspace(workspace.id)
    setShowDeleteDialog(false)
  }

  const actions: ReprocessAction[] = [
    {
      id: 'delete-workspace',
      label: 'Delete Workspace',
      onClick: handleDeleteClick,
      disabled: isDeleting,
      isLoading: isDeleting,
      icon: <Trash2 className="mr-2 h-4 w-4 text-destructive" />
    }
  ]
  return (
    <>
      <Card variant="blocky" className="hover:shadow-md transition-all cursor-pointer">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="text-sm font-semibold">
                {workspace.name}
              </h3>
              {workspace.description && (
                <p className="text-xs text-muted-foreground mt-1">
                  {workspace.description}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2 ml-3">
              <Badge variant="secondary" style="blocky">
                ID: {workspace.id}
              </Badge>
              <ReprocessDropdown actions={actions}>
                <button
                  className="p-1 hover:bg-black/10 rounded-sm transition-colors"
                  key={"del-"+workspace.id}
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                  }}
                >
                  <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
                </button>
              </ReprocessDropdown>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex justify-between items-center text-xs text-muted-foreground">
            <span>Created: {new Date(workspace.createdAt).toLocaleDateString()}</span>
            <span>Updated: {new Date(workspace.updatedAt).toLocaleDateString()}</span>
          </div>
        </CardContent>
      </Card>

      <DeleteConfirmationDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        onConfirm={handleConfirmDelete}
        title="Delete Workspace"
        description={`Are you sure you want to delete "${workspace.name}"? This action cannot be undone.`}
        isDeleting={isDeleting}
      />
    </>
  )
}