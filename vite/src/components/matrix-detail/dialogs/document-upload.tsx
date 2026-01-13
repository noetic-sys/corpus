import { useState, useCallback } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Input } from "@/components/ui/input"
import { Upload } from "lucide-react"
import { uploadDocumentApiV1MatricesMatrixIdDocumentsPost } from '@/client'
import { apiClient } from '@/lib/api'
import { ACCEPTED_FILE_TYPES, MAX_FILE_SIZE } from '@/lib/file-constants'
import type { DocumentResponse } from '@/client'
import { toast } from "sonner"
import { FileUploadList, type FileUploadItem } from '../shared/file-upload-list'

interface DocumentUploadProps {
  matrixId: number
  entitySetId: number
  onDocumentUploaded: (document: DocumentResponse) => void
}

export function DocumentUpload({ matrixId, entitySetId, onDocumentUploaded }: DocumentUploadProps) {
  const { getToken } = useAuth()
  const [files, setFiles] = useState<File[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 })

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
      setFiles(prev => [...prev, ...validFiles])
    }

    // Reset input so same files can be selected again
    event.target.value = ''
  }, [validateFile])

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const uploadFiles = async (items: FileUploadItem[]) => {
    setIsUploading(true)
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

      {/* Inline file list with agentic toggle - no separate dialog */}
      <FileUploadList
        files={files}
        isUploading={isUploading}
        onUpload={uploadFiles}
        onClear={() => setFiles([])}
        onRemoveFile={removeFile}
        showUploadButton={true}
      />

      {/* Upload progress indicator */}
      {isUploading && uploadProgress.total > 1 && (
        <p className="text-xs text-muted-foreground text-center">
          Uploading {uploadProgress.current}/{uploadProgress.total}...
        </p>
      )}
    </div>
  )
}
