import { useState, useCallback, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { FileText, Upload, Sparkles } from "lucide-react"
import { uploadDocumentApiV1MatricesMatrixIdDocumentsPost } from '@/client'
import { apiClient } from '@/lib/api'
import { ACCEPTED_FILE_TYPES, MAX_FILE_SIZE, AGENTIC_CHUNKING_SIZE_THRESHOLD } from '@/lib/file-constants'
import type { DocumentResponse } from '@/client'
import { toast } from "sonner"

interface DocumentUploadProps {
  matrixId: number
  entitySetId: number
  onDocumentUploaded: (document: DocumentResponse) => void
}

export function DocumentUpload({ matrixId, entitySetId, onDocumentUploaded }: DocumentUploadProps) {
  const { getToken } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [useAgenticChunking, setUseAgenticChunking] = useState(false)

  // Auto-set agentic chunking based on file size
  useEffect(() => {
    if (file) {
      setUseAgenticChunking(file.size >= AGENTIC_CHUNKING_SIZE_THRESHOLD)
    }
  }, [file])

  const validateFile = useCallback((file: File): string | null => {
    if (file.size > MAX_FILE_SIZE) {
      return `File size must be less than ${MAX_FILE_SIZE / 1024 / 1024}MB`
    }
    
    const fileExtension = `.${file.name.split('.').pop()?.toLowerCase()}`
    if (!ACCEPTED_FILE_TYPES.includes(fileExtension)) {
      return `File type not supported. Accepted types: ${ACCEPTED_FILE_TYPES.join(', ')}`
    }
    
    return null
  }, [])

  const handleFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (selectedFile) {
      const validationError = validateFile(selectedFile)
      if (validationError) {
        toast.error("Invalid file", {
          description: validationError
        })
        setFile(null)
      } else {
        setFile(selectedFile)
      }
    }
  }, [validateFile])

  const handleUpload = async () => {
    if (!file) return

    setIsUploading(true)

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
        toast.success("Document uploaded successfully", {
          description: response.data.filename
        })
        onDocumentUploaded(response.data)
        setFile(null)
      }
    } catch (error) {
      toast.error("Upload failed", {
        description: `${file.name}: ${error instanceof Error ? error.message : 'Upload failed'}`
      })
    }

    setIsUploading(false)
  }

  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="file-upload">Choose File</Label>
        <Input
          id="file-upload"
          type="file"
          variant="blocky"
          onChange={handleFileChange}
          disabled={isUploading}
          accept={ACCEPTED_FILE_TYPES.join(',')}
          className="mt-2"
        />
        <p className="text-xs text-muted-foreground mt-1">
          Accepted: {ACCEPTED_FILE_TYPES.join(', ')} (max {MAX_FILE_SIZE / 1024 / 1024}MB)
        </p>
      </div>
      
      {file && (
        <div className="text-sm text-muted-foreground bg-secondary/20 p-3 rounded border">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            <span className="font-medium">{file.name}</span>
            <span className="text-xs">({(file.size / 1024).toFixed(1)} KB)</span>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between p-3 rounded border bg-secondary/10">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <div>
            <Label htmlFor="agentic-chunking" className="text-sm font-medium">
              AI-powered chunking
            </Label>
            <p className="text-xs text-muted-foreground">
              Uses your quota for better document processing
            </p>
          </div>
        </div>
        <Switch
          id="agentic-chunking"
          checked={useAgenticChunking}
          onCheckedChange={setUseAgenticChunking}
          disabled={isUploading}
        />
      </div>

      <Button
        style="blocky"
        onClick={handleUpload}
        disabled={!file || isUploading}
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
            Upload Document
          </>
        )}
      </Button>
    </div>
  )
}