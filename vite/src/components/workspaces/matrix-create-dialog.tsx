import { useState } from 'react'
import { useRouter, useLocation } from '@tanstack/react-router'
import { useAuth } from '@/hooks/useAuth'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { toast } from "sonner"
import { createMatrixApiV1MatricesPost } from '@/client'
import { apiClient } from '@/lib/api'
import type { WorkspaceResponse, MatrixType } from '@/client'
import {throwApiError} from "@/lib/api-error.ts";

interface MatrixCreateDialogProps {
  workspace: WorkspaceResponse
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function MatrixCreateDialog({ workspace, open, onOpenChange }: MatrixCreateDialogProps) {
  const router = useRouter()
  const location = useLocation()
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  const [createFormData, setCreateFormData] = useState({
    name: '',
    description: '',
    matrixType: 'standard' as MatrixType
  })
  const [createError, setCreateError] = useState<string | null>(null)

  const createMatrixMutation = useMutation({
    mutationFn: async (data: { name: string; description?: string; workspaceId: number; matrixType?: MatrixType }) => {
      const token = await getToken()

      const response = await createMatrixApiV1MatricesPost({
        client: apiClient,
        body: data,
        headers: {
          authorization: `Bearer ${token}`
        }
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to create matrix')
      }

      return response.data
    },
    onSuccess: (data) => {
      toast.success("Matrix created successfully", {
        description: data.name
      })

      // Invalidate matrices query to refetch the list
      queryClient.invalidateQueries({ queryKey: ['matrices', workspace.id.toString()] })

      // Reset form and close dialog
      setCreateFormData({ name: '', description: '', matrixType: 'standard' })
      setCreateError(null)
      onOpenChange(false)

      // Navigate to new matrix tab
      router.navigate({
        to: location.pathname,
        search: { ...location.search, matrix: data.id },
        replace: true
      })
    },
    onError: (error) => {
      setCreateError(error instanceof Error ? error.message : 'Failed to create matrix')
    }
  })

  const handleCreateMatrix = async () => {
    if (!createFormData.name.trim()) {
      setCreateError('Matrix name is required')
      return
    }

    setCreateError(null)

    const requestBody = {
      name: createFormData.name.trim(),
      description: createFormData.description.trim() || undefined,
      workspaceId: workspace.id,
      matrixType: createFormData.matrixType
    }

    createMatrixMutation.mutate(requestBody)
  }

  const closeCreateDialog = () => {
    if (!createMatrixMutation.isPending) {
      setCreateFormData({ name: '', description: '', matrixType: 'standard' })
      setCreateError(null)
      onOpenChange(false)
    }
  }

  const isCreating = createMatrixMutation.isPending

  return (
    <Dialog open={open} onOpenChange={closeCreateDialog}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Create New Matrix</DialogTitle>
          <DialogDescription>
            Create a new matrix in {workspace.name}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={createFormData.name}
              onChange={(e) => setCreateFormData(prev => ({ ...prev, name: e.target.value }))}
              placeholder="Enter matrix name"
              disabled={isCreating}
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description (optional)</Label>
            <Textarea
              id="description"
              value={createFormData.description}
              onChange={(e) => setCreateFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Enter matrix description"
              disabled={isCreating}
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label>Matrix Type</Label>
            <RadioGroup
              value={createFormData.matrixType}
              onValueChange={(value) => setCreateFormData(prev => ({ ...prev, matrixType: value as MatrixType }))}
              disabled={isCreating}
              className="space-y-2"
            >
              <label
                className={`flex items-start gap-3 rounded-md border p-3 cursor-pointer transition-colors ${
                  createFormData.matrixType === 'standard' ? 'border-primary bg-primary/5' : 'border-input hover:bg-muted/50'
                }`}
              >
                <RadioGroupItem value="standard" className="mt-0.5" />
                <div className="space-y-0.5">
                  <div className="font-medium text-sm">Standard</div>
                  <div className="text-xs text-muted-foreground">
                    Documents × Questions. Extract the same data points across a set of files. Best for contract review, earnings, due diligence.
                  </div>
                </div>
              </label>
              <label
                className={`flex items-start gap-3 rounded-md border p-3 cursor-pointer transition-colors ${
                  createFormData.matrixType === 'cross_correlation' ? 'border-primary bg-primary/5' : 'border-input hover:bg-muted/50'
                }`}
              >
                <RadioGroupItem value="cross_correlation" className="mt-0.5" />
                <div className="space-y-0.5">
                  <div className="font-medium text-sm">Cross-Correlation</div>
                  <div className="text-xs text-muted-foreground">
                    Compare two document sets against each other. Best for comparing terms across contracts, finding discrepancies.
                  </div>
                </div>
              </label>
              <label
                className={`flex items-start gap-3 rounded-md border p-3 cursor-pointer transition-colors ${
                  createFormData.matrixType === 'generic_correlation' ? 'border-primary bg-primary/5' : 'border-input hover:bg-muted/50'
                }`}
              >
                <RadioGroupItem value="generic_correlation" className="mt-0.5" />
                <div className="space-y-0.5">
                  <div className="font-medium text-sm">Generic Correlation</div>
                  <div className="text-xs text-muted-foreground">
                    Multiple document sets with custom relationships. Best for complex multi-party analysis.
                  </div>
                </div>
              </label>
              <label
                className={`flex items-start gap-3 rounded-md border p-3 cursor-pointer transition-colors ${
                  createFormData.matrixType === 'synopsis' ? 'border-primary bg-primary/5' : 'border-input hover:bg-muted/50'
                }`}
              >
                <RadioGroupItem value="synopsis" className="mt-0.5" />
                <div className="space-y-0.5">
                  <div className="font-medium text-sm">Synopsis</div>
                  <div className="text-xs text-muted-foreground">
                    Synthesize all documents together for each question. Best for research summaries, literature reviews, multi-source analysis.
                  </div>
                </div>
              </label>
            </RadioGroup>
          </div>

          {createError && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{createError}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={closeCreateDialog}
            disabled={isCreating}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreateMatrix}
            disabled={!createFormData.name.trim() || isCreating}
          >
            {isCreating ? (
              <>Creating...</>
            ) : (
              <>
                <Plus className="mr-2 h-4 w-4" />
                Create Matrix
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}