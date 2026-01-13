import { AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LowConfidenceWarningProps {
  confidence: number
  className?: string
  compact?: boolean
}

export const CONFIDENCE_THRESHOLD = 0.7

export function LowConfidenceWarning({
  confidence,
  className,
  compact = false,
}: LowConfidenceWarningProps) {
  if (confidence >= CONFIDENCE_THRESHOLD) {
    return null
  }

  const confidencePercent = Math.round(confidence * 100)

  // Compact mode for matrix cells - just a small indicator
  if (compact) {
    return (
      <div
        className={cn(
          'inline-flex items-center gap-1 text-amber-700 dark:text-amber-300',
          className
        )}
        title={`Low confidence: ${confidencePercent}%`}
      >
        <AlertTriangle className="h-3 w-3 flex-shrink-0" />
        <span className="text-[10px] font-medium">Low confidence</span>
      </div>
    )
  }

  return (
    <div
      className={cn(
        'flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200',
        className
      )}
    >
      <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="font-medium">Low Confidence Answer</p>
        <p className="text-xs mt-1 text-amber-700 dark:text-amber-300">
          This answer has a confidence score of {confidencePercent}% (below the {CONFIDENCE_THRESHOLD * 100}% threshold).
          The evidence may be indirect, contradictory, or require human review.
        </p>
      </div>
    </div>
  )
}
