'use client'

import { useState, useCallback } from 'react'

interface UseDialogStateOptions {
  onClose?: () => void
}

export function useDialogState({ onClose }: UseDialogStateOptions = {}) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reset = useCallback(() => {
    setError(null)
    setIsLoading(false)
  }, [])

  const handleClose = useCallback(() => {
    if (!isLoading) {
      reset()
      onClose?.()
    }
  }, [isLoading, reset, onClose])

  const handleError = useCallback((error: unknown) => {
    console.error('Dialog error:', error)
    
    if (error instanceof Error) {
      setError(error.message)
    } else if (typeof error === 'string') {
      setError(error)
    } else {
      setError('An unexpected error occurred. Please try again.')
    }
  }, [])

  return {
    isLoading,
    setIsLoading,
    error,
    setError,
    reset,
    handleClose,
    handleError,
  }
}