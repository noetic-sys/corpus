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
import { useUsageStats } from '@/hooks/use-billing'

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
  const { data: usageStats } = useUsageStats()

  // Check if user has agentic chunking quota remaining
  const hasAgenticQuota = usageStats
    ? usageStats.agenticChunking < usageStats.agenticChunkingLimit
    : false
  const agenticQuotaRemaining = usageStats
    ? usageStats.agenticChunkingLimit - usageStats.agenticChunking
    : 0

  // Initialize items - default based on file size if quota available
  useEffect(() => {
    setItems(
      files.map(file => ({
        file,
        useAgenticChunking: hasAgenticQuota && file.size >= AGENTIC_CHUNKING_SIZE_THRESHOLD,
      }))
    )
  }, [files, hasAgenticQuota])

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
      <DialogContent variant="blocky" className="sm:max-w-lg p-0">
        <DialogHeader className="p-4 border-b-2 border-border">
          <DialogTitle>Upload {files.length} document{files.length !== 1 ? 's' : ''}</DialogTitle>
          <DialogDescription>
            Configure processing options for each file.
          </DialogDescription>
        </DialogHeader>

        <div className="p-4 space-y-4">
          {/* AI Chunking option - only show if user has quota */}
          {hasAgenticQuota && (
            <div className="flex items-center gap-4">
              <Sparkles className="h-4 w-4 text-primary flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <Label className="text-sm font-medium">AI-Powered Chunking</Label>
                <p className="text-xs text-muted-foreground">
                  Better Q&A for complex documents ({agenticQuotaRemaining} remaining)
                </p>
              </div>
              {items.length > 1 && (
                <div className="flex border-2 border-border divide-x-2 divide-border flex-shrink-0">
                  <button
                    className="px-3 py-1 text-xs hover:bg-muted disabled:opacity-50"
                    onClick={() => toggleAll(false)}
                    disabled={isUploading}
                  >
                    None
                  </button>
                  <button
                    className="px-3 py-1 text-xs hover:bg-muted disabled:opacity-50"
                    onClick={() => toggleAll(true)}
                    disabled={isUploading}
                  >
                    All
                  </button>
                </div>
              )}
            </div>
          )}

          {/* File table */}
          <div className="border-2 border-border">
            {/* Table header */}
            <div className="flex items-center justify-between px-3 py-2 bg-muted/50 border-b-2 border-border text-xs font-medium text-muted-foreground uppercase tracking-wide">
              <span>File</span>
              {hasAgenticQuota && <span>AI</span>}
            </div>

            {/* File rows */}
            <div className="max-h-[240px] overflow-y-auto divide-y-2 divide-border">
              {items.map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between px-3 py-2 hover:bg-muted/30"
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                    <span className="text-sm truncate">{item.file.name}</span>
                    <span className="text-xs text-muted-foreground flex-shrink-0">
                      {(item.file.size / 1024).toFixed(0)} KB
                    </span>
                  </div>
                  {hasAgenticQuota && (
                    <Switch
                      checked={item.useAgenticChunking}
                      onCheckedChange={() => toggleAgenticChunking(index)}
                      disabled={isUploading}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>

          {hasAgenticQuota && agenticCount > 0 && (
            <p className="text-xs text-muted-foreground">
              {agenticCount} of {items.length} file{items.length !== 1 ? 's' : ''} will use AI chunking
            </p>
          )}
        </div>

        <DialogFooter className="p-4 border-t-2 border-border">
          <Button variant="outline" style="blocky" onClick={onClose} disabled={isUploading}>
            Cancel
          </Button>
          <Button style="blocky" onClick={handleConfirm} disabled={isUploading}>
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
