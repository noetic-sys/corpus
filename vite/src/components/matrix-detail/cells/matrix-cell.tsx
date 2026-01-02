import { useState } from "react"
import { cn } from "@/lib/utils"
import { ReprocessDropdown, type ReprocessAction } from "../reprocess/reprocess-dropdown"
import { AnswerItemRenderer } from "../answer-items/answer-item-renderer"
import { useMatrixContext } from '../context/matrix-context'
import type { MatrixCellType } from '../types'
import type { AnswerWithCitations, DateAnswerDataResponse, CurrencyAnswerDataResponse } from '@/client'
import { Copy, MoreHorizontal } from "lucide-react"
import { MatrixCellNotYetLoaded } from "./matrix-cell-not-yet-loaded"
import { MatrixCellLoading } from "./matrix-cell-loading"
import { MatrixCellError } from "./matrix-cell-error"
import { MatrixCellEmpty } from "./matrix-cell-empty"
import { MatrixCellDiagonal } from "./matrix-cell-diagonal"
import { MatrixCellDetailSheet } from "./matrix-cell-detail-sheet"
import { QUESTION_TYPE_IDS } from "@/lib/question-types"


// Helper function to extract plain text from answer data list for clipboard
function extractPlainText(answers: AnswerWithCitations[], answerFound?: boolean): string {
  if (!answerFound || !answers || answers.length === 0) {
    return 'Answer not found in document'
  }
  
  // Extract text from all answers and join them
  const textParts: string[] = []
  
  for (const answer of answers) {
    const answerData = answer.answerData
    if ('value' in answerData) {
      textParts.push(answerData.value)
    } else if ('optionValue' in answerData) {
      textParts.push(answerData.optionValue)
    } else if ('parsedDate' in answerData) {
      const dateData = answerData as DateAnswerDataResponse
      if (dateData.parsedDate) {
        textParts.push(dateData.parsedDate)
      }
    } else if ('currency' in answerData && 'amount' in answerData) {
      const currencyData = answerData as CurrencyAnswerDataResponse
      if (currencyData.currency && currencyData.amount) {
        textParts.push(`${currencyData.currency} ${currencyData.amount.toLocaleString()}`)
      }
    } else {
      textParts.push(String(answerData))
    }
  }
  
  return textParts.join(', ')
}

// Helper function to render structured answer data using new item renderer pattern
function renderAnswerData(
  answers: AnswerWithCitations[] | undefined,
  questionTypeId?: number,
  answerFound?: boolean,
  cellId?: number,
  sparseView?: boolean
): React.ReactNode {
  // Check for "not available" responses first - applies to ALL question types
  if (!answerFound || !answers || answers.length === 0) {
    // In sparse view, show minimal dot placeholder
    if (sparseView) {
      return (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-1.5 h-1.5 rounded-full bg-black/50"></div>
        </div>
      )
    }

    return (
      <div className="text-xs text-text-tertiary italic break-words whitespace-normal flex-1">
        Answer not found in document
      </div>
    )
  }

  // For SELECT type questions, use horizontal layout with wrapping
  // For all other types, use vertical stacking
  const isSelectType = questionTypeId === QUESTION_TYPE_IDS.SELECT

  return (
    <div className={cn(
      "flex gap-1",
      isSelectType ? "flex-wrap" : "flex-col"
    )}>
      {answers.map((answer, index) => (
        <AnswerItemRenderer
          key={index}
          answerData={answer.answerData}
          questionTypeId={questionTypeId}
          citations={answer.citations}
          cellId={cellId}
        />
      ))}
    </div>
  )
}

interface MatrixCellProps {
  cell: MatrixCellType | null
  isLoading?: boolean
  isNotYetLoaded?: boolean
  isError?: boolean
  isDiagonal?: boolean
  isSelected?: boolean
  onRetry?: () => void
  matrixId: number
  onReprocess?: (cellId: number) => void
  isReprocessing?: boolean
  isDetailOpen?: boolean
  onDetailOpenChange?: (open: boolean) => void
}

const statusConfig = {
  pending: {
    label: 'Pending',
    variant: 'outline' as const,
    className: 'bg-surface hover:bg-surface-hover'
  },
  processing: {
    label: 'Processing',
    variant: 'secondary' as const,
    className: 'bg-surface hover:bg-surface-hover'
  },
  completed: {
    label: 'Completed',
    variant: 'secondary' as const,
    className: 'bg-surface hover:bg-surface-hover'
  },
  failed: {
    label: 'Failed',
    variant: 'destructive' as const,
    className: 'bg-status-error-bg hover:bg-status-error-hover'
  }
}

export function MatrixCell({
  cell,
  isLoading,
  isNotYetLoaded,
  isError,
  isDiagonal,
  isSelected = false,
  onRetry,
  onReprocess,
  isReprocessing = false,
  isDetailOpen,
  onDetailOpenChange
}: MatrixCellProps) {
  const { sparseView } = useMatrixContext()
  const [internalDetailSheetOpen, setInternalDetailSheetOpen] = useState(false)

  // Use controlled state if provided, otherwise use internal state
  const isDetailSheetOpen = isDetailOpen !== undefined ? isDetailOpen : internalDetailSheetOpen
  const setIsDetailSheetOpen = onDetailOpenChange || setInternalDetailSheetOpen

  if (isDiagonal) {
    return <MatrixCellDiagonal isSelected={isSelected} />
  }

  if (isNotYetLoaded) {
    return <MatrixCellNotYetLoaded isSelected={isSelected} />
  }

  if (isLoading) {
    return <MatrixCellLoading isSelected={isSelected} />
  }

  if (isError) {
    return <MatrixCellError onRetry={onRetry} isSelected={isSelected} />
  }

  if (!cell) {
    return <MatrixCellEmpty onRetry={onRetry} isSelected={isSelected} />
  }

  const config = statusConfig[cell.status]

  const handleReprocess = () => {
    if (onReprocess && cell?.id) {
      onReprocess(cell.id)
    }
  }

  const handleCopyToClipboard = () => {
    if (!cell?.currentAnswer?.answers) return

    const textToCopy = extractPlainText(
      cell.currentAnswer.answers,
      cell.currentAnswer.answerFound
    )

    navigator.clipboard.writeText(textToCopy)
  }

  const handleCellClick = () => {
    if (cell.status === 'completed' && cell.currentAnswer) {
      setIsDetailSheetOpen(true)
    }
  }

  const actions: ReprocessAction[] = [
    {
      id: 'reprocess-cell',
      label: 'Reprocess',
      onClick: handleReprocess,
      disabled: isReprocessing,
      isLoading: isReprocessing,
    },
    ...(cell.status === 'completed' ? [{
      id: 'copy-to-clipboard',
      label: 'Copy to clipboard',
      onClick: handleCopyToClipboard,
      icon: <Copy className="mr-2 h-4 w-4" />,
    }] : [])
  ]

  return (
    <>
      <div
        className={cn(
          "w-full h-full p-2 transition-colors flex flex-col relative",
          config.className,
          cell.status === 'completed' && cell.currentAnswer && "cursor-pointer hover:opacity-80",
          isSelected && "ring-2 ring-blue-500 ring-inset"
        )}
        onClick={handleCellClick}
      >
        {/* Reprocess dropdown button */}
        <div className="absolute top-1 right-1 z-10">
          <ReprocessDropdown actions={actions}>
            <button
              className="p-1 hover:bg-black/10 rounded-sm transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              <MoreHorizontal className="h-3 w-3 text-text-light" />
            </button>
          </ReprocessDropdown>
        </div>

        {/* Content area with right padding to avoid overlap with menu button */}
        <div className="pr-6">
          {cell.status !== 'completed' && (
            <span className="text-[10px] font-semibold uppercase text-text-light mb-1">
              {config.label}
            </span>
          )}

          {cell.status === 'completed' && renderAnswerData(
            cell.currentAnswer?.answers,
            cell.currentAnswer?.questionTypeId,
            cell.currentAnswer?.answerFound,
            cell.id,
            sparseView
          )}
        </div>
      </div>

      {/* Detail sheet */}
      {cell.currentAnswer && (
        <MatrixCellDetailSheet
          open={isDetailSheetOpen}
          onOpenChange={setIsDetailSheetOpen}
          cell={cell}
        />
      )}
    </>
  )
}