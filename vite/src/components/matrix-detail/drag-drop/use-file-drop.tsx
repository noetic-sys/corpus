import { useState, useCallback, useEffect, useRef } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { uploadDocumentApiV1MatricesMatrixIdDocumentsPost } from '@/client'
import { apiClient } from '@/lib/api'
import type { DocumentResponse, EntitySetResponse } from '@/client'

interface UseFileDropOptions {
  matrixId: number
  entitySets: EntitySetResponse[]
  onFilesUploaded?: (documents: DocumentResponse[]) => void
  acceptedFileTypes?: string[]
  maxFileSize?: number
}

const DEFAULT_ACCEPTED_TYPES = ['.pdf', '.doc', '.docx', '.txt', '.md', '.xlsx', '.xls', '.pptx', '.ppt', '.csv', '.mp3', '.wav', '.flac', '.ogg', '.webm', '.m4a', '.aac']
const DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

export function useFileDrop({
  matrixId,
  entitySets,
  onFilesUploaded,
  acceptedFileTypes = DEFAULT_ACCEPTED_TYPES,
  maxFileSize = DEFAULT_MAX_FILE_SIZE
}: UseFileDropOptions) {
  const { getToken } = useAuth()
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number }>({ current: 0, total: 0 })
  const [errors, setErrors] = useState<string[]>([])
  const [pendingFiles, setPendingFiles] = useState<File[]>([])
  const [showEntitySetDialog, setShowEntitySetDialog] = useState(false)
  const dragCounter = useRef(0)

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

  const uploadFiles = useCallback(async (files: File[], entitySetId?: number) => {
    // If multiple document entity sets exist and no entitySetId provided, show dialog
    if (!entitySetId && documentEntitySets.length > 1) {
      setPendingFiles(files)
      setShowEntitySetDialog(true)
      return
    }

    // Use the single entity set if only one exists
    const targetEntitySetId = entitySetId || documentEntitySets[0]?.id

    if (!targetEntitySetId) {
      setErrors(['No document entity set found'])
      return
    }

    setIsUploading(true)
    setErrors([])
    setUploadProgress({ current: 0, total: files.length })

    const uploadedDocuments: DocumentResponse[] = []
    const uploadErrors: string[] = []

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      setUploadProgress({ current: i + 1, total: files.length })

      try {
        const token = await getToken()

        const response = await uploadDocumentApiV1MatricesMatrixIdDocumentsPost({
          client: apiClient,
          path: { matrixId },
          query: { entitySetId: targetEntitySetId },
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
  }, [matrixId, onFilesUploaded, getToken, documentEntitySets])

  const handleEntitySetSelected = useCallback((entitySetId: number) => {
    if (pendingFiles.length > 0) {
      uploadFiles(pendingFiles, entitySetId)
    }
  }, [pendingFiles, uploadFiles])

  const handleDrop = useCallback((e: DragEvent) => {
    console.log('DROP EVENT - Files:', e.dataTransfer?.files?.length)
    e.preventDefault()
    e.stopPropagation()

    dragCounter.current = 0
    setIsDragging(false)

    if (isUploading) {
      console.log('ALREADY UPLOADING - ignoring drop')
      return
    }

    const files = Array.from(e.dataTransfer?.files || [])
    console.log('FILES DROPPED:', files.length, files.map(f => f.name))
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
      uploadFiles(validFiles)
    }
  }, [isUploading, uploadFiles, validateFile])

  const handleDragEnter = useCallback((e: DragEvent) => {
    console.log('DRAG ENTER - Counter:', dragCounter.current, 'Items:', e.dataTransfer?.items?.length)
    e.preventDefault()
    e.stopPropagation()

    dragCounter.current++

    if (e.dataTransfer?.items && e.dataTransfer.items.length > 0) {
      console.log('SETTING isDragging = true')
      setIsDragging(true)
    }
  }, [])

  const handleDragLeave = useCallback((e: DragEvent) => {
    console.log('DRAG LEAVE - Counter:', dragCounter.current)
    e.preventDefault()
    e.stopPropagation()

    dragCounter.current--

    if (dragCounter.current === 0) {
      console.log('SETTING isDragging = false')
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
    showEntitySetDialog,
    documentEntitySets,
    onEntitySetSelected: handleEntitySetSelected,
    onEntitySetDialogClose: () => {
      setShowEntitySetDialog(false)
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