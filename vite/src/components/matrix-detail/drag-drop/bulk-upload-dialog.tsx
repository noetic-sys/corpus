import { useState, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { FileText, Sparkles, Upload } from "lucide-react"
import { AGENTIC_CHUNKING_SIZE_THRESHOLD } from '@/lib/file-constants'

interface FileUploadItem {
  file: File
  useAgenticChunking: boolean
}

interface BulkUploadDialogProps {
  isOpen: boolean
  onClose: () => void
  files: File[]
  onConfirm: (items: FileUploadItem[]) => void
  isUploading: boolean
}

export function BulkUploadDialog({
  isOpen,
  onClose,
  files,
  onConfirm,
  isUploading,
}: BulkUploadDialogProps) {
  const [items, setItems] = useState<FileUploadItem[]>([])

  // Initialize items with size-based defaults when files change
  useEffect(() => {
    setItems(
      files.map(file => ({
        file,
        useAgenticChunking: file.size >= AGENTIC_CHUNKING_SIZE_THRESHOLD,
      }))
    )
  }, [files])

  const toggleAgenticChunking = (index: number) => {
    setItems(prev =>
      prev.map((item, i) =>
        i === index ? { ...item, useAgenticChunking: !item.useAgenticChunking } : item
      )
    )
  }

  const toggleAll = (value: boolean) => {
    setItems(prev => prev.map(item => ({ ...item, useAgenticChunking: value })))
  }

  const agenticCount = items.filter(i => i.useAgenticChunking).length

  const handleConfirm = () => {
    onConfirm(items)
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Upload {files.length} document{files.length !== 1 ? 's' : ''}</DialogTitle>
          <DialogDescription>
            Configure AI-powered chunking for each document. Larger files benefit more from AI processing.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 max-h-[300px] overflow-y-auto py-2">
          {items.map((item, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 rounded border bg-secondary/10"
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{item.file.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {(item.file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                {item.useAgenticChunking && (
                  <Sparkles className="h-3 w-3 text-primary" />
                )}
                <Switch
                  checked={item.useAgenticChunking}
                  onCheckedChange={() => toggleAgenticChunking(index)}
                  disabled={isUploading}
                />
              </div>
            </div>
          ))}
        </div>

        {items.length > 1 && (
          <div className="flex items-center justify-between pt-2 border-t">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <Label className="text-sm">
                AI chunking: {agenticCount} of {items.length} files
              </Label>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => toggleAll(false)}
                disabled={isUploading}
              >
                None
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => toggleAll(true)}
                disabled={isUploading}
              >
                All
              </Button>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isUploading}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={isUploading}>
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

export type { FileUploadItem }
