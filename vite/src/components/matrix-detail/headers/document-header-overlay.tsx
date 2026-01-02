import { useState } from "react"
import { cn } from "@/lib/utils"
import { RefreshCw, Trash2, Tag } from "lucide-react"
import { ReprocessDropdown, type ReprocessAction } from "../reprocess/reprocess-dropdown"
import { useReprocessDocument } from "../hooks/use-reprocess-document"
import { useSoftDeleteDocument } from "../hooks/use-soft-delete-document"
import { useUpdateDocumentLabel } from "../hooks/use-update-document-label"
import { DeleteConfirmationDialog } from "../dialogs/delete-confirmation-dialog"
import { LabelEditDialog } from "../dialogs/label-edit-dialog"
import type { MatrixDocument } from '../types'
import type { EntityRole } from '@/client'

interface DocumentHeaderOverlayProps {
  document: MatrixDocument
  matrixId: number
  entitySetId: number
  memberId: number
  role: string
  children: React.ReactNode
}

export function DocumentHeaderOverlay({ document, matrixId, entitySetId, memberId, role, children }: DocumentHeaderOverlayProps) {
  const { reprocessDocument, isReprocessing } = useReprocessDocument()
  const { softDeleteDocument, isDeleting } = useSoftDeleteDocument()
  const { updateDocumentLabel, isUpdating: isUpdatingLabel } = useUpdateDocumentLabel()
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showLabelDialog, setShowLabelDialog] = useState(false)

  const handleReprocessDocument = async () => {
    await reprocessDocument(matrixId, document.document.id, entitySetId, role)
  }

  const handleEditLabel = () => {
    setShowLabelDialog(true)
  }

  const handleDeleteClick = () => {
    setShowDeleteDialog(true)
  }

  const handleConfirmDelete = async () => {
    await softDeleteDocument(matrixId, document.id, document.document.id, entitySetId, role as EntityRole)
    setShowDeleteDialog(false)
  }

  const handleSaveLabel = async (label: string | null) => {
    await updateDocumentLabel(matrixId, entitySetId, memberId, label)
  }

  const actions: ReprocessAction[] = [
    {
      id: 'edit-label',
      label: 'Edit Label',
      onClick: handleEditLabel,
      disabled: isReprocessing || isDeleting || isUpdatingLabel,
      isLoading: isUpdatingLabel,
      icon: <Tag className="mr-2 h-4 w-4" />
    },
    {
      id: 'reprocess-document',
      label: 'Reprocess Row',
      onClick: handleReprocessDocument,
      disabled: isReprocessing || isDeleting || isUpdatingLabel,
      isLoading: isReprocessing,
      icon: <RefreshCw className={cn("mr-2 h-4 w-4", isReprocessing && "animate-spin")} />
    },
    {
      id: 'delete-document',
      label: 'Delete Document',
      onClick: handleDeleteClick,
      disabled: isReprocessing || isDeleting || isUpdatingLabel,
      isLoading: isDeleting,
      icon: <Trash2 className="mr-2 h-4 w-4 text-destructive" />
    }
  ]

  return (
    <>
      <ReprocessDropdown actions={actions}>
        <div className={cn(
          "w-full h-full transition-colors cursor-pointer",
          "hover:bg-muted/50"
        )}>
          {children}
        </div>
      </ReprocessDropdown>

      <DeleteConfirmationDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        onConfirm={handleConfirmDelete}
        title="Delete Document"
        description="Are you sure you want to delete this document?"
        isDeleting={isDeleting}
      />

      <LabelEditDialog
        open={showLabelDialog}
        onOpenChange={setShowLabelDialog}
        currentLabel={document.label}
        onSave={handleSaveLabel}
        isLoading={isUpdatingLabel}
        title="Edit Document Label"
        description="Set a label for this document to help with organization."
      />
    </>
  )
}