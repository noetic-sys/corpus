import { useState, useCallback } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { FileText, Upload, X } from "lucide-react"
import { uploadDocumentApiV1MatricesMatrixIdDocumentsPost } from '@/client'
import { apiClient } from '@/lib/api'
import { ACCEPTED_FILE_TYPES, MAX_FILE_SIZE } from '@/lib/file-constants'
import type { DocumentResponse } from '@/client'
import { toast } from "sonner"
import { BulkUploadDialog, type FileUploadItem } from '../drag-drop/bulk-upload-dialog'
import { useUsageStats } from '@/hooks/use-billing'

interface DocumentUploadProps {
  matrixId: number
  entitySetId: number
  onDocumentUploaded: (document: DocumentResponse) => void
}

export function DocumentUpload({ matrixId, entitySetId, onDocumentUploaded }: DocumentUploadProps) {
  const { getToken } = useAuth()
  const { data: usageStats } = useUsageStats()
  const [files, setFiles] = useState<File[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 })
  const [showBulkDialog, setShowBulkDialog] = useState(false)

  // Check if user has agentic chunking quota
  const hasAgenticQuota = usageStats
    ? usageStats.agenticChunking < usageStats.agenticChunkingLimit
    : false

  const validateFile = useCallback((file: File): string | null => {
    if (file.size > MAX_FILE_SIZE) {
      return `${file.name}: File size must be less than ${MAX_FILE_SIZE / 1024 / 1024}MB`
    }

    const fileExtension = `.${file.name.split('.').pop()?.toLowerCase()}`
    if (!ACCEPTED_FILE_TYPES.includes(fileExtension)) {
      return `${file.name}: File type not supported`
    }

    return null
  }, [])

  const handleFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || [])
    if (selectedFiles.length === 0) return

    const validFiles: File[] = []
    const errors: string[] = []

    selectedFiles.forEach(file => {
      const error = validateFile(file)
      if (error) {
        errors.push(error)
      } else {
        validFiles.push(file)
      }
    })

    if (errors.length > 0) {
      toast.error("Some files were rejected", {
        description: errors.join('\n')
      })
    }

    if (validFiles.length > 0) {
      setFiles(validFiles)
      // Show bulk dialog if user has quota, otherwise upload directly
      if (hasAgenticQuota) {
        setShowBulkDialog(true)
      }
    }

    // Reset input so same files can be selected again
    event.target.value = ''
  }, [validateFile, hasAgenticQuota])

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const uploadFiles = async (items: FileUploadItem[]) => {
    setIsUploading(true)
    setShowBulkDialog(false)
    setUploadProgress({ current: 0, total: items.length })

    const uploadedDocs: DocumentResponse[] = []

    for (let i = 0; i < items.length; i++) {
      const { file, useAgenticChunking } = items[i]
      setUploadProgress({ current: i + 1, total: items.length })

      try {
        const token = await getToken()

        const response = await uploadDocumentApiV1MatricesMatrixIdDocumentsPost({
          path: { matrixId },
          query: { entitySetId, useAgenticChunking },
          body: { file },
          headers: {
            authorization: `Bearer ${token}`
          },
          client: apiClient
        })

        if (response.error) {
          toast.error("Upload failed", {
            description: `${file.name}: ${response.error.detail || 'Upload failed'}`
          })
        } else if (response.data) {
          uploadedDocs.push(response.data)
        }
      } catch (error) {
        toast.error("Upload failed", {
          description: `${file.name}: ${error instanceof Error ? error.message : 'Upload failed'}`
        })
      }
    }

    if (uploadedDocs.length > 0) {
      toast.success(`Uploaded ${uploadedDocs.length} document${uploadedDocs.length !== 1 ? 's' : ''}`)
      uploadedDocs.forEach(doc => onDocumentUploaded(doc))
    }

    setFiles([])
    setIsUploading(false)
    setUploadProgress({ current: 0, total: 0 })
  }

  const handleUpload = async () => {
    if (files.length === 0) return

    // If no quota, upload all with agentic=false
    if (!hasAgenticQuota) {
      const items: FileUploadItem[] = files.map(file => ({
        file,
        useAgenticChunking: false
      }))
      await uploadFiles(items)
    } else {
      // Show dialog to configure per-file settings
      setShowBulkDialog(true)
    }
  }

  const handleBulkUploadConfirm = (items: FileUploadItem[]) => {
    uploadFiles(items)
  }

  return (
    <div className="space-y-4">
      {/* Dropzone-style upload area */}
      <label
        htmlFor="file-upload"
        className={`
          flex flex-col items-center justify-center gap-3 p-8
          border-2 border-dashed rounded-lg cursor-pointer
          transition-colors hover:border-primary hover:bg-muted/50
          ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <div className="p-3 rounded-full bg-muted">
          <Upload className="h-6 w-6 text-muted-foreground" />
        </div>
        <div className="text-center">
          <p className="text-sm font-medium">Click to upload files</p>
          <p className="text-xs text-muted-foreground mt-1">
            PDF, Word, Excel, PowerPoint, text files (max {MAX_FILE_SIZE / 1024 / 1024}MB each)
          </p>
        </div>
        <Input
          id="file-upload"
          type="file"
          multiple
          onChange={handleFileChange}
          disabled={isUploading}
          accept={ACCEPTED_FILE_TYPES.join(',')}
          className="hidden"
        />
      </label>

      {/* Selected files list */}
      {files.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-medium">
              {files.length} file{files.length !== 1 ? 's' : ''} selected
            </Label>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setFiles([])}
              disabled={isUploading}
              className="text-xs h-7"
            >
              Clear all
            </Button>
          </div>
          <div className="max-h-[200px] overflow-y-auto border-2 border-border divide-y-2 divide-border">
            {files.map((file, index) => (
              <div key={index} className="flex items-center justify-between text-sm p-2 hover:bg-muted/30">
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                  <span className="truncate">{file.name}</span>
                  <span className="text-xs text-muted-foreground flex-shrink-0">
                    {(file.size / 1024).toFixed(0)} KB
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeFile(index)}
                  disabled={isUploading}
                  className="h-6 w-6 p-0 hover:bg-destructive/10 hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload button */}
      {files.length > 0 && (
        <Button
          style="blocky"
          onClick={handleUpload}
          disabled={isUploading}
          className="w-full"
        >
          {isUploading ? (
            <>
              <Upload className="mr-2 h-4 w-4 animate-spin" />
              Uploading {uploadProgress.current}/{uploadProgress.total}...
            </>
          ) : (
            <>
              <Upload className="mr-2 h-4 w-4" />
              Upload {files.length} File{files.length !== 1 ? 's' : ''}
            </>
          )}
        </Button>
      )}

      <BulkUploadDialog
        isOpen={showBulkDialog}
        onClose={() => setShowBulkDialog(false)}
        files={files}
        onConfirm={handleBulkUploadConfirm}
        isUploading={isUploading}
      />
    </div>
  )
}