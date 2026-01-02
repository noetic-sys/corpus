'use client'

import { useState } from 'react'
import { DocumentUploadDialog } from '../dialogs'
import { Button } from "@/components/ui/button"
import { FilePlus2 } from "lucide-react"
import type { DocumentResponse } from '@/client'
import {useMatrixContext} from "@/components/matrix-detail";

interface DocumentUploadClientProps {
  matrixId: number
  entitySetId: number
}

export function DocumentUploadClient({ matrixId, entitySetId }: DocumentUploadClientProps) {
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false)
  const { triggerRefresh } = useMatrixContext()

  const handleDocumentUploaded = (document: DocumentResponse) => {
    console.log('Document uploaded:', document)
    triggerRefresh(matrixId, { documents: true, entitySets: true, tiles: true, stats: true })
  }

  return (
      <>
        <Button
            variant="outline"
            style="blocky"
            size="sm"
            onClick={() => setIsUploadDialogOpen(true)}
            className="h-10 px-3"
            title="Add Document"
        >
          <FilePlus2 className="h-4 w-4 mr-2" />
          Add
        </Button>

        <DocumentUploadDialog
            isOpen={isUploadDialogOpen}
            onClose={() => setIsUploadDialogOpen(false)}
            matrixId={matrixId}
            entitySetId={entitySetId}
            onDocumentUploaded={handleDocumentUploaded}
        />
      </>
  )
}