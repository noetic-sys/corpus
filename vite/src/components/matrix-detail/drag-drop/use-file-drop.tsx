import { useState, useCallback, useEffect, useRef } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { uploadDocumentApiV1MatricesMatrixIdDocumentsPost } from '@/client'
import { apiClient } from '@/lib/api'
import { ACCEPTED_FILE_TYPES, MAX_FILE_SIZE } from '@/lib/file-constants'
import { useUsageStats } from '@/hooks/use-billing'
import type { DocumentResponse, EntitySetResponse } from '@/client'
import type { FileUploadItem } from '../shared/file-upload-list'

interface UseFileDropOptions {
  matrixId: number
  entitySets: EntitySetResponse[]
  onFilesUploaded?: (documents: DocumentResponse[]) => void
  acceptedFileTypes?: string[]
  maxFileSize?: number
}

export function useFileDrop({
  matrixId,
  entitySets,
  onFilesUploaded,
  acceptedFileTypes = ACCEPTED_FILE_TYPES,
  maxFileSize = MAX_FILE_SIZE
}: UseFileDropOptions) {
  const { getToken } = useAuth()
  const { data: usageStats } = useUsageStats()
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number }>({ current: 0, total: 0 })
  const [errors, setErrors] = useState<string[]>([])
  const [pendingFiles, setPendingFiles] = useState<File[]>([])
  const [showUploadConfigDialog, setShowUploadConfigDialog] = useState(false)
  const dragCounter = useRef(0)

  // Check if user has agentic chunking quota
  const hasAgenticQuota = usageStats
    ? usageStats.agenticChunking < usageStats.agenticChunkingLimit
    : false

  // Get document entity sets
  const documentEntitySets = entitySets.filter(es => es.entityType === 'document')

  const validateFile = useCallback((file: File): string | null => {
    if (file.size > maxFileSize) {
      return `${file.name}: File size must be less than ${maxFileSize / 1024 / 1024}MB`
    }

    const fileExtension = `.${file.name.split('.').pop()?.toLowerCase()}`
    if (!acceptedFileTypes.some(type => fileExtension.endsWith(type))) {
      return `${file.name}: File type not supported`
    }

    return null
  }, [maxFileSize, acceptedFileTypes])

  // Upload files with their individual agentic chunking settings
  const uploadFilesWithOptions = useCallback(async (items: FileUploadItem[], entitySetId: number) => {
    setIsUploading(true)
    setShowUploadConfigDialog(false)
    setErrors([])
    setUploadProgress({ current: 0, total: items.length })

    const uploadedDocuments: DocumentResponse[] = []
    const uploadErrors: string[] = []

    for (let i = 0; i < items.length; i++) {
      const { file, useAgenticChunking } = items[i]
      setUploadProgress({ current: i + 1, total: items.length })

      try {
        const token = await getToken()

        const response = await uploadDocumentApiV1MatricesMatrixIdDocumentsPost({
          client: apiClient,
          path: { matrixId },
          query: { entitySetId, useAgenticChunking },
          body: { file },
          headers: {
            authorization: `Bearer ${token}`
          },
        })

        if (response.error) {
          uploadErrors.push(`${file.name}: ${response.error.detail || 'Upload failed'}`)
        } else if (response.data) {
          uploadedDocuments.push(response.data)
        }
      } catch (error) {
        uploadErrors.push(`${file.name}: ${error instanceof Error ? error.message : 'Upload failed'}`)
      }
    }

    setErrors(uploadErrors)
    setIsUploading(false)
    setUploadProgress({ current: 0, total: 0 })
    setPendingFiles([])

    if (uploadedDocuments.length > 0) {
      onFilesUploaded?.(uploadedDocuments)
    }
  }, [matrixId, onFilesUploaded, getToken])

  // Handle dropping files - show combined config dialog
  const handleFilesDropped = useCallback((files: File[]) => {
    const targetEntitySetId = documentEntitySets[0]?.id
    if (!targetEntitySetId && documentEntitySets.length === 0) {
      setErrors(['No document entity set found'])
      return
    }

    // If only one entity set AND no agentic quota, upload directly without any dialog
    if (documentEntitySets.length === 1 && !hasAgenticQuota) {
      const items: FileUploadItem[] = files.map(file => ({
        file,
        useAgenticChunking: false,
      }))
      uploadFilesWithOptions(items, targetEntitySetId)
      return
    }

    // Otherwise, show the combined config dialog
    setPendingFiles(files)
    setShowUploadConfigDialog(true)
  }, [documentEntitySets, hasAgenticQuota, uploadFilesWithOptions])

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()

    dragCounter.current = 0
    setIsDragging(false)

    if (isUploading) return

    const files = Array.from(e.dataTransfer?.files || [])
    if (files.length === 0) return

    // Validate all files
    const validationErrors: string[] = []
    const validFiles: File[] = []

    files.forEach(file => {
      const error = validateFile(file)
      if (error) {
        validationErrors.push(error)
      } else {
        validFiles.push(file)
      }
    })

    if (validationErrors.length > 0) {
      setErrors(validationErrors)
    }

    if (validFiles.length > 0) {
      handleFilesDropped(validFiles)
    }
  }, [isUploading, handleFilesDropped, validateFile])

  const handleDragEnter = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()

    dragCounter.current++

    if (e.dataTransfer?.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true)
    }
  }, [])

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()

    dragCounter.current--

    if (dragCounter.current === 0) {
      setIsDragging(false)
    }
  }, [])

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  useEffect(() => {
    const handleWindowDrop = (e: DragEvent) => {
      e.preventDefault()
    }

    window.addEventListener('drop', handleWindowDrop)
    window.addEventListener('dragover', handleDragOver)

    return () => {
      window.removeEventListener('drop', handleWindowDrop)
      window.removeEventListener('dragover', handleDragOver)
    }
  }, [handleDragOver])

  return {
    isDragging,
    isUploading,
    uploadProgress,
    errors,
    clearErrors: () => setErrors([]),
    // Combined upload config dialog
    showUploadConfigDialog,
    pendingFiles,
    documentEntitySets,
    onUploadConfigConfirm: uploadFilesWithOptions,
    onUploadConfigClose: () => {
      setShowUploadConfigDialog(false)
      setPendingFiles([])
    },
    handlers: {
      onDrop: handleDrop,
      onDragEnter: handleDragEnter,
      onDragLeave: handleDragLeave,
      onDragOver: handleDragOver,
    }
  }
}
