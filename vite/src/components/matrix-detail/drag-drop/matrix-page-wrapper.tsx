import { useRef, useEffect, useCallback } from 'react'
import { DropZoneOverlay } from './drop-zone-overlay'
import { useFileDrop } from './use-file-drop'
import { MatrixProvider, useMatrixContext } from '../context/matrix-context'
import { EntitySetSelectorDialog } from '../dialogs/entity-set-selector-dialog'
import { toast } from "sonner"
import type { MatrixDocument, Question } from '../types'
import type {DocumentResponse, EntitySetResponse, AiProviderResponse, AiModelResponse, MatrixType} from '@/client'

interface MatrixPageWrapperProps {
  matrix: {
    id: number
    name: string
    description?: string | null
    createdAt: string
    updatedAt: string
  }
  matrixId: number
  matrixType: MatrixType
  documents: MatrixDocument[]
  questions: Question[]
  entitySets: EntitySetResponse[]
  aiProviders: AiProviderResponse[]
  aiModels: AiModelResponse[]
  children: React.ReactNode
}

function MatrixPageWrapperInner({ children }: { children: React.ReactNode }) {
  const pageRef = useRef<HTMLDivElement>(null)
  const { matrixId, triggerRefresh, entitySets } = useMatrixContext()

  // Filter document entity sets for upload dialog
  const documentEntitySets = entitySets.filter(es => es.entityType === 'document')

  const handleFilesUploaded = useCallback((uploadedDocuments: DocumentResponse[]) => {
    const count = uploadedDocuments.length
    toast.success(`Successfully uploaded ${count} document${count === 1 ? '' : 's'}`, {
      description: uploadedDocuments.map(doc => doc.filename).join(', ')
    })
    // Only refresh documents, entity sets, and tiles - questions and matrix unchanged
    triggerRefresh(matrixId, { documents: true, entitySets: true, tiles: true })
  }, [triggerRefresh, matrixId])

  const {
    isDragging,
    isUploading,
    uploadProgress,
    errors,
    clearErrors,
    showEntitySetDialog,
    documentEntitySets: uploadDocumentEntitySets,
    onEntitySetSelected,
    onEntitySetDialogClose,
    handlers
  } = useFileDrop({
    matrixId,
    entitySets: documentEntitySets,
    onFilesUploaded: handleFilesUploaded
  })

  // Set up drag-and-drop handlers on the entire page
  useEffect(() => {
    const element = pageRef.current
    if (!element) {
      return
    }

    element.addEventListener('drop', handlers.onDrop as EventListener)
    element.addEventListener('dragenter', handlers.onDragEnter as EventListener)
    element.addEventListener('dragleave', handlers.onDragLeave as EventListener)
    element.addEventListener('dragover', handlers.onDragOver as EventListener)

    return () => {
      element.removeEventListener('drop', handlers.onDrop as EventListener)
      element.removeEventListener('dragenter', handlers.onDragEnter as EventListener)
      element.removeEventListener('dragleave', handlers.onDragLeave as EventListener)
      element.removeEventListener('dragover', handlers.onDragOver as EventListener)
    }
  }, [handlers])

  // Show errors if any
  useEffect(() => {
    if (errors.length > 0) {
      // Show individual error toasts
      errors.forEach(error => {
        toast.error("Upload failed", {
          description: error
        })
      })
      // Clear errors after showing toasts
      const timer = setTimeout(() => clearErrors(), 1000)
      return () => clearTimeout(timer)
    }
  }, [errors, clearErrors])

  return (
    <div ref={pageRef} className="h-full relative">
      {children}

      <DropZoneOverlay
        isDragging={isDragging}
        isUploading={isUploading}
        uploadProgress={uploadProgress}
      />

      <EntitySetSelectorDialog
        isOpen={showEntitySetDialog}
        onClose={onEntitySetDialogClose}
        entitySets={uploadDocumentEntitySets}
        title="Select Document Set"
        description="Choose which document set to add the files to."
        onSelect={onEntitySetSelected}
      />
    </div>
  )
}

export function MatrixPageWrapper(props: MatrixPageWrapperProps) {
  return (
    <MatrixProvider
      matrix={props.matrix}
      matrixType={props.matrixType}
      documents={props.documents}
      questions={props.questions}
      entitySets={props.entitySets}
      aiProviders={props.aiProviders}
      aiModels={props.aiModels}
    >
      <MatrixPageWrapperInner>
        {props.children}
      </MatrixPageWrapperInner>
    </MatrixProvider>
  )
}