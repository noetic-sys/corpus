import { useState, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { FileText, Sparkles, Upload, X } from "lucide-react"
import { AGENTIC_CHUNKING_SIZE_THRESHOLD } from '@/lib/file-constants'
import { useUsageStats } from '@/hooks/use-billing'

export interface FileUploadItem {
  file: File
  useAgenticChunking: boolean
}

interface FileUploadListProps {
  files: File[]
  isUploading: boolean
  onUpload: (items: FileUploadItem[]) => void
  onClear?: () => void
  onRemoveFile?: (index: number) => void
  /** Whether to show the upload button (false when parent handles it) */
  showUploadButton?: boolean
  /** Controlled items - parent manages state */
  items?: FileUploadItem[]
  onItemsChange?: (items: FileUploadItem[]) => void
}

export function FileUploadList({
  files,
  isUploading,
  onUpload,
  onClear,
  onRemoveFile,
  showUploadButton = true,
  items: controlledItems,
  onItemsChange,
}: FileUploadListProps) {
  const [internalItems, setInternalItems] = useState<FileUploadItem[]>([])
  const { data: usageStats } = useUsageStats()

  // Use controlled or internal state
  const items = controlledItems ?? internalItems
  const setItems = onItemsChange ?? setInternalItems

  // Check if user has agentic chunking quota remaining
  const hasAgenticQuota = usageStats
    ? usageStats.agenticChunking < usageStats.agenticChunkingLimit
    : false
  const agenticQuotaRemaining = usageStats
    ? usageStats.agenticChunkingLimit - usageStats.agenticChunking
    : 0

  // Initialize items - default based on file size if quota available
  useEffect(() => {
    if (!controlledItems) {
      setInternalItems(
        files.map(file => ({
          file,
          useAgenticChunking: hasAgenticQuota && file.size >= AGENTIC_CHUNKING_SIZE_THRESHOLD,
        }))
      )
    }
  }, [files, hasAgenticQuota, controlledItems])

  // Sync controlled items when files change
  useEffect(() => {
    if (controlledItems && onItemsChange) {
      // Only update if file count changed
      if (files.length !== controlledItems.length) {
        onItemsChange(
          files.map(file => ({
            file,
            useAgenticChunking: hasAgenticQuota && file.size >= AGENTIC_CHUNKING_SIZE_THRESHOLD,
          }))
        )
      }
    }
  }, [files, hasAgenticQuota, controlledItems, onItemsChange])

  const toggleAgenticChunking = (index: number) => {
    setItems(
      items.map((item, i) =>
        i === index ? { ...item, useAgenticChunking: !item.useAgenticChunking } : item
      )
    )
  }

  const toggleAll = (value: boolean) => {
    setItems(items.map(item => ({ ...item, useAgenticChunking: value })))
  }

  const agenticCount = items.filter(i => i.useAgenticChunking).length

  const handleUpload = () => {
    onUpload(items)
  }

  if (files.length === 0) {
    return null
  }

  return (
    <div className="space-y-4">
      {/* Header with count and clear button */}
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">
          {files.length} file{files.length !== 1 ? 's' : ''} selected
        </Label>
        {onClear && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClear}
            disabled={isUploading}
            className="text-xs h-7"
          >
            Clear all
          </Button>
        )}
      </div>

      {/* AI Chunking option - only show if user has quota */}
      {hasAgenticQuota && (
        <div className="flex items-center gap-4 p-3 bg-muted/30 rounded-lg border">
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
          <div className="flex items-center gap-4">
            {hasAgenticQuota && <span>AI</span>}
            {onRemoveFile && <span className="w-6"></span>}
          </div>
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
              <div className="flex items-center gap-4">
                {hasAgenticQuota && (
                  <Switch
                    checked={item.useAgenticChunking}
                    onCheckedChange={() => toggleAgenticChunking(index)}
                    disabled={isUploading}
                  />
                )}
                {onRemoveFile && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onRemoveFile(index)}
                    disabled={isUploading}
                    className="h-6 w-6 p-0 hover:bg-destructive/10 hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {hasAgenticQuota && agenticCount > 0 && (
        <p className="text-xs text-muted-foreground">
          {agenticCount} of {items.length} file{items.length !== 1 ? 's' : ''} will use AI chunking
        </p>
      )}

      {/* Upload button */}
      {showUploadButton && (
        <Button
          style="blocky"
          onClick={handleUpload}
          disabled={isUploading || items.length === 0}
          className="w-full"
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
      )}
    </div>
  )
}
