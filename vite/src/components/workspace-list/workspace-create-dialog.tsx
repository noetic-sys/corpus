import { useState } from 'react'
import { useRouter } from '@tanstack/react-router'
import { useAuth } from '@/hooks/useAuth'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { createWorkspaceApiV1WorkspacesPost } from '@/client'
import {apiClient} from "@/lib/api.ts";

interface WorkspaceCreateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function WorkspaceCreateDialog({ open, onOpenChange }: WorkspaceCreateDialogProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const { getToken } = useAuth()
  const router = useRouter()
  const queryClient = useQueryClient()

  const createWorkspaceMutation = useMutation({
    mutationFn: async (data: { name: string; description?: string }) => {
      const token = await getToken()

      const response = await createWorkspaceApiV1WorkspacesPost({
        client: apiClient,
        headers: {
          authorization: `Bearer ${token}`
        },
        body: data
      })

      return response.data
    },
    onSuccess: (data) => {
      toast.success('Workspace created successfully')
      // Invalidate workspaces query to refetch the list
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      onOpenChange(false)
      setName('')
      setDescription('')
      // Navigate to the new workspace
      if (data?.id) {
        router.navigate({ to: `/workspaces/$workspaceId`, params: { workspaceId: data.id.toString() } })
      }
    },
    onError: (error) => {
      console.error('Error creating workspace:', error)
      toast.error(error instanceof Error ? error.message : 'Failed to create workspace')
    }
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim()) {
      toast.error('Workspace name is required')
      return
    }

    const requestBody = {
      name: name.trim(),
      description: description.trim() || undefined
    }

    createWorkspaceMutation.mutate(requestBody)
  }

  const handleCancel = () => {
    onOpenChange(false)
    setName('')
    setDescription('')
  }

  const isLoading = createWorkspaceMutation.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Create New Workspace</DialogTitle>
          <DialogDescription>
            Create a new workspace to organize your matrices.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                placeholder="Enter workspace name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isLoading}
                autoFocus
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Enter workspace description (optional)"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isLoading}
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isLoading || !name.trim()}
            >
              {isLoading ? 'Creating...' : 'Create Workspace'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}