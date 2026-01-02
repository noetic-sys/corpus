import type { RefObject } from 'react'
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { TemplateVariablesButton } from '@/components/matrix-detail/template-variables'
import { MatrixDuplicationDropdown } from "@/components/matrix-detail/matrix-duplication-dropdown.tsx"
import { SliceAxisCombobox, type SliceAxisComboboxHandle } from './grid/slice-axis-combobox'
import { SliceItemCombobox, type SliceItemComboboxHandle } from './grid/slice-item-combobox'
import { useMatrixContext } from './context/matrix-context'
import { useAuth } from '@/hooks/useAuth'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMatrixStatsApiV1MatricesMatrixIdStatsGet,
  queuePendingDocumentsApiV1ExtractionQueuePendingPost,
  retryFailedExtractionsApiV1ExtractionRetryFailedPost,
  queuePendingCellsApiV1QueueProcessPendingPost
} from '@/client'
import { apiClient } from '@/lib/api'
import { RefreshCw, Grid3x3, Grid2x2 } from 'lucide-react'
import { toast } from 'sonner'

import type { EntityRole } from '@/client/types.gen'

interface MatrixHeaderProps {
  sliceControls?: {
    canSwapAxes: boolean
    allAxes: Array<{ role: EntityRole; entitySetId: number; entitySetName: string; count: number }>
    activeSliceAxisRole: string
    handleAxisChange: (role: string) => void
    currentSliceAxis: { role: EntityRole; entitySetId: number; entitySetName: string; count: number } | null
    sliceOptions: Array<{ value: string; label: string; description?: string }>
    currentSliceIndex: number
    setCurrentSliceIndex: (index: number) => void
    sliceItemComboboxRef: RefObject<SliceItemComboboxHandle | null>
    sliceAxisComboboxRef: RefObject<SliceAxisComboboxHandle | null>
  }
}

export function MatrixHeader({ sliceControls }: MatrixHeaderProps) {
  const { matrix, matrixType, documents, questions, entitySets, sparseView, setSparseView } = useMatrixContext()
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  // Calculate total cells by multiplying entity set member counts
  // For cross_correlation, document set is squared (used as both LEFT and RIGHT)
  const totalCells = entitySets.reduce((product, entitySet) => {
    const memberCount = entitySet.members?.length || 0

    // For cross-correlation, square the document entity set
    if (matrixType === 'cross_correlation' && entitySet.entityType === 'document') {
      return product * memberCount * memberCount
    }

    return product * memberCount
  }, 1)

  // Get question entity set ID
  const questionEntitySet = entitySets.find(es => es.entityType === 'question')

  // Fetch matrix cell statistics
  const { data: stats } = useQuery({
    queryKey: ['matrix-stats', matrix.id],
    queryFn: async () => {
      const token = await getToken()
      const response = await getMatrixStatsApiV1MatricesMatrixIdStatsGet({
        path: { matrixId: matrix.id },
        headers: { authorization: `Bearer ${token}` },
        client: apiClient
      })
      return response.data
    },
    staleTime: (query) => {
      const data = query.state.data
      // If any cells/documents are pending or processing, don't cache
      const hasActiveCells = data && (
        data.pending > 0 ||
        data.processing > 0 ||
        (data.documentsPendingExtraction ?? 0) > 0
      )
      return hasActiveCells ? 0 : 30000
    },
    refetchInterval: (query) => {
      const data = query.state.data
      // Poll if any cells/documents are pending or processing
      const hasActiveCells = data && (
        data.pending > 0 ||
        data.processing > 0 ||
        (data.documentsPendingExtraction ?? 0) > 0
      )
      return hasActiveCells ? 5000 : false // Poll every 5 seconds
    },
  })

  // Calculate if we should show progress
  const showProgress = stats && (
    stats.pending > 0 ||
    stats.processing > 0 ||
    stats.failed > 0 ||
    (stats.documentsPendingExtraction ?? 0) > 0 ||
    (stats.documentsFailedExtraction ?? 0) > 0
  )
  const progressPercent = stats ? (stats.completed / stats.totalCells) * 100 : 0

  // Mutations for self-help actions
  const queuePendingQAMutation = useMutation({
    mutationFn: async () => {
      const token = await getToken()
      const response = await queuePendingCellsApiV1QueueProcessPendingPost({
        headers: { authorization: `Bearer ${token}` },
        body: { matrixId: matrix.id },
        client: apiClient
      })
      return response.data
    },
    onSuccess: (data) => {
      toast.success(`Queued ${data?.queued ?? 0} pending QA cells for processing`)
      queryClient.invalidateQueries({ queryKey: ['matrix-stats', matrix.id] })
    },
    onError: () => {
      toast.error('Failed to queue pending QA cells')
    }
  })

  const queuePendingDocumentsMutation = useMutation({
    mutationFn: async () => {
      const token = await getToken()
      const response = await queuePendingDocumentsApiV1ExtractionQueuePendingPost({
        headers: { authorization: `Bearer ${token}` },
        client: apiClient
      })
      return response.data
    },
    onSuccess: (data) => {
      toast.success(`Queued ${data?.queued ?? 0} pending documents for extraction`)
      queryClient.invalidateQueries({ queryKey: ['matrix-stats', matrix.id] })
    },
    onError: () => {
      toast.error('Failed to queue pending documents')
    }
  })

  const retryFailedDocumentsMutation = useMutation({
    mutationFn: async () => {
      const token = await getToken()
      const response = await retryFailedExtractionsApiV1ExtractionRetryFailedPost({
        headers: { authorization: `Bearer ${token}` },
        client: apiClient
      })
      return response.data
    },
    onSuccess: (data) => {
      toast.success(`Retried ${data?.retried ?? 0} failed document extractions`)
      queryClient.invalidateQueries({ queryKey: ['matrix-stats', matrix.id] })
    },
    onError: () => {
      toast.error('Failed to retry document extractions')
    }
  })

  return (
    <div className="grid grid-cols-[auto_1fr_auto_auto] gap-6 items-center px-4 py-1.5 bg-surface border-b border-border">
      {/* Column 1: Matrix name and stats */}
      <div className="flex flex-col gap-0.5 text-sm min-w-0">
        <span className="font-semibold truncate">{matrix.name}</span>
        <span className="text-xs text-muted-foreground whitespace-nowrap">
          {documents.length} Docs • {questions.length} Qs • {totalCells} Cells
        </span>
      </div>

      {/* Column 2: Slice controls (center, only if provided) */}
      {sliceControls ? (
        <div className="flex items-center gap-2 justify-center">
          {sliceControls.canSwapAxes && (
            <SliceAxisCombobox
              ref={sliceControls.sliceAxisComboboxRef}
              axes={sliceControls.allAxes}
              activeAxisRole={sliceControls.activeSliceAxisRole}
              onAxisChange={sliceControls.handleAxisChange}
            />
          )}

          {sliceControls.currentSliceAxis && (
            <SliceItemCombobox
              ref={sliceControls.sliceItemComboboxRef}
              axisName={sliceControls.currentSliceAxis.entitySetName}
              options={sliceControls.sliceOptions}
              selectedIndex={sliceControls.currentSliceIndex}
              onIndexChange={sliceControls.setCurrentSliceIndex}
            />
          )}
        </div>
      ) : (
        <div />
      )}

      {/* Column 3: Progress and action buttons (only when active) */}
      {showProgress && stats ? (
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 min-w-[200px]">
            <Progress value={progressPercent} className="h-2 flex-1" />
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {stats.completed}/{stats.totalCells}
            </span>
          </div>

          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {stats.processing > 0 && <span className="text-blue-600">{stats.processing} processing</span>}
            {stats.processing > 0 && stats.pending > 0 && ', '}
            {stats.pending > 0 && <span className="text-yellow-600">{stats.pending} pending</span>}
            {(stats.processing > 0 || stats.pending > 0) && stats.failed > 0 && ', '}
            {stats.failed > 0 && <span className="text-red-600">{stats.failed} failed</span>}
          </span>

          <div className="flex items-center gap-1">
            {stats.pending > 0 && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => queuePendingQAMutation.mutate()}
                disabled={queuePendingQAMutation.isPending}
                className="h-7 text-xs"
              >
                <RefreshCw className={`h-3 w-3 mr-1 ${queuePendingQAMutation.isPending ? 'animate-spin' : ''}`} />
                Process
              </Button>
            )}
            {(stats.documentsPendingExtraction ?? 0) > 0 && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => queuePendingDocumentsMutation.mutate()}
                disabled={queuePendingDocumentsMutation.isPending}
                className="h-7 text-xs"
              >
                <RefreshCw className={`h-3 w-3 mr-1 ${queuePendingDocumentsMutation.isPending ? 'animate-spin' : ''}`} />
                Queue
              </Button>
            )}
            {(stats.documentsFailedExtraction ?? 0) > 0 && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => retryFailedDocumentsMutation.mutate()}
                disabled={retryFailedDocumentsMutation.isPending}
                className="h-7 text-xs"
              >
                <RefreshCw className={`h-3 w-3 mr-1 ${retryFailedDocumentsMutation.isPending ? 'animate-spin' : ''}`} />
                Retry
              </Button>
            )}
          </div>
        </div>
      ) : (
        <div />
      )}

      {/* Column 4: Action buttons (always visible, right-aligned) */}
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant={sparseView ? "default" : "outline"}
          style="blocky"
          onClick={() => setSparseView(!sparseView)}
          className="h-8 text-xs"
          title={sparseView ? "Switch to dense view" : "Switch to sparse view"}
        >
          {sparseView ? (
            <>
              <Grid2x2 className="h-3.5 w-3.5 mr-1.5" />
              Sparse
            </>
          ) : (
            <>
              <Grid3x3 className="h-3.5 w-3.5 mr-1.5" />
              Dense
            </>
          )}
        </Button>
        <TemplateVariablesButton
          matrixId={matrix.id}
          questions={questions}
          questionEntitySetId={questionEntitySet?.id}
        />
        <MatrixDuplicationDropdown matrixId={matrix.id} matrixName={matrix.name} />
        <Badge variant="outline" style="blocky" className="text-xs">ID: {matrix.id}</Badge>
      </div>
    </div>
  )
}