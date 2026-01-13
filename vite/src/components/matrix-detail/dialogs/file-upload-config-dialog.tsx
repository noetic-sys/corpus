import { useState, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Upload, FolderOpen } from "lucide-react"
import { FileUploadList, type FileUploadItem } from '../shared/file-upload-list'
import { AGENTIC_CHUNKING_SIZE_THRESHOLD } from '@/lib/file-constants'
import { useUsageStats } from '@/hooks/use-billing'
import type { EntitySetResponse } from '@/client'

interface FileUploadConfigDialogProps {
  isOpen: boolean
  onClose: () => void
  files: File[]
  /** Document entity sets - show selector only if > 1 */
  documentEntitySets: EntitySetResponse[]
  /** Pre-selected entity set ID (optional) */
  defaultEntitySetId?: number
  onConfirm: (items: FileUploadItem[], entitySetId: number) => void
  isUploading: boolean
}

export function FileUploadConfigDialog({
  isOpen,
  onClose,
  files,
  documentEntitySets,
  defaultEntitySetId,
  onConfirm,
  isUploading,
}: FileUploadConfigDialogProps) {
  const [items, setItems] = useState<FileUploadItem[]>([])
  const [selectedEntitySetId, setSelectedEntitySetId] = useState<number | null>(null)
  const { data: usageStats } = useUsageStats()

  const hasAgenticQuota = usageStats
    ? usageStats.agenticChunking < usageStats.agenticChunkingLimit
    : false

  const showEntitySetSelector = documentEntitySets.length > 1

  // Initialize items when files change
  useEffect(() => {
    setItems(
      files.map(file => ({
        file,
        useAgenticChunking: hasAgenticQuota && file.size >= AGENTIC_CHUNKING_SIZE_THRESHOLD,
      }))
    )
  }, [files, hasAgenticQuota])

  // Initialize selected entity set
  useEffect(() => {
    if (isOpen) {
      if (defaultEntitySetId) {
        setSelectedEntitySetId(defaultEntitySetId)
      } else if (documentEntitySets.length > 0) {
        setSelectedEntitySetId(documentEntitySets[0].id)
      }
    }
  }, [isOpen, defaultEntitySetId, documentEntitySets])

  const handleConfirm = () => {
    if (selectedEntitySetId !== null && items.length > 0) {
      onConfirm(items, selectedEntitySetId)
    }
  }

  const canUpload = selectedEntitySetId !== null && items.length > 0

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent variant="blocky" className="sm:max-w-lg p-0">
        <DialogHeader className="p-4 border-b-2 border-border">
          <DialogTitle>
            Upload {files.length} document{files.length !== 1 ? 's' : ''}
          </DialogTitle>
          <DialogDescription>
            {showEntitySetSelector
              ? 'Select target document set and configure processing options.'
              : 'Configure processing options for each file.'}
          </DialogDescription>
        </DialogHeader>

        <div className="p-4 space-y-6">
          {/* Entity Set Selector - only if multiple document sets */}
          {showEntitySetSelector && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <FolderOpen className="h-4 w-4 text-muted-foreground" />
                <Label className="text-sm font-medium">Target Document Set</Label>
              </div>
              <RadioGroup
                value={selectedEntitySetId?.toString() || ''}
                onValueChange={(value) => setSelectedEntitySetId(parseInt(value, 10))}
                className="space-y-2"
              >
                {documentEntitySets.map((entitySet) => (
                  <div
                    key={entitySet.id}
                    className="flex items-center space-x-3 p-2 rounded border hover:bg-muted/30"
                  >
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
                      <div className="text-xs text-muted-foreground">
                        {entitySet.members?.length || 0} documents
                      </div>
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            </div>
          )}

          {/* Divider if both sections shown */}
          {showEntitySetSelector && files.length > 0 && (
            <div className="border-t border-border" />
          )}

          {/* File List with AI toggles */}
          {files.length > 0 && (
            <FileUploadList
              files={files}
              isUploading={isUploading}
              onUpload={() => {}} // Not used - we use footer button
              items={items}
              onItemsChange={setItems}
              showUploadButton={false}
            />
          )}
        </div>

        <DialogFooter className="p-4 border-t-2 border-border">
          <Button variant="outline" style="blocky" onClick={onClose} disabled={isUploading}>
            Cancel
          </Button>
          <Button
            style="blocky"
            onClick={handleConfirm}
            disabled={!canUpload || isUploading}
          >
            {isUploading ? (
              <>
                <Upload className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Upload {items.length} file{items.length !== 1 ? 's' : ''}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
