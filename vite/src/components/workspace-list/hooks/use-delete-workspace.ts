import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { toast } from 'sonner'
import { deleteWorkspaceApiV1WorkspacesWorkspaceIdDelete } from '@/client'
import { apiClient } from '@/lib/api'
import { getApiErrorMessage } from '@/lib/api-error'

export function useDeleteWorkspace() {
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { getToken } = useAuth()

  const deleteWorkspace = async (workspaceId: number) => {
    setIsDeleting(true)
    setError(null)

    try {
      const token = await getToken()

      const response = await deleteWorkspaceApiV1WorkspacesWorkspaceIdDelete({
        path: { workspaceId },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        throw new Error(getApiErrorMessage(response.error, 'Failed to delete workspace'))
      }

      // Invalidate workspaces query to refresh the list
      await queryClient.invalidateQueries({ queryKey: ['workspaces'] })

      toast.success('Workspace deleted successfully', {
        description: 'The workspace has been successfully deleted'
      })

      return response.data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete workspace'
      setError(errorMessage)
      toast.error('Failed to delete workspace', {
        description: errorMessage
      })
      throw err
    } finally {
      setIsDeleting(false)
    }
  }

  return {
    deleteWorkspace,
    isDeleting,
    error,
  }
}
