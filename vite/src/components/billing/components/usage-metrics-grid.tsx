import { Grid3X3, Bot, Workflow, HardDrive, FileStack, FileText } from 'lucide-react'
import type { UsageStatsResponse } from '../types'
import { formatBytes } from '../utils/formatting'
import { UsageMetricCard } from './usage-metric-card'

interface UsageMetricsGridProps {
  usage: UsageStatsResponse
}

export function UsageMetricsGrid({ usage }: UsageMetricsGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <UsageMetricCard
        icon={Grid3X3}
        title="Cell Operations"
        description="Monthly usage"
        value={usage.cellOperations.toLocaleString()}
        limit={usage.cellOperationsLimit.toLocaleString()}
        percentage={usage.cellOperationsPercentage}
      />
      <UsageMetricCard
        icon={Bot}
        title="Agentic QA"
        description="AI agent queries"
        value={usage.agenticQa.toLocaleString()}
        limit={usage.agenticQaLimit.toLocaleString()}
        percentage={usage.agenticQaPercentage}
      />
      <UsageMetricCard
        icon={Workflow}
        title="Workflows"
        description="Workflow executions"
        value={usage.workflows.toLocaleString()}
        limit={usage.workflowsLimit.toLocaleString()}
        percentage={usage.workflowsPercentage}
      />
      <UsageMetricCard
        icon={FileText}
        title="Documents"
        description="Document uploads"
        value={usage.documents.toLocaleString()}
        limit={usage.documentsLimit.toLocaleString()}
        percentage={usage.documentsPercentage}
      />
      <UsageMetricCard
        icon={HardDrive}
        title="Storage"
        description="File storage used"
        value={formatBytes(usage.storageBytes)}
        limit={formatBytes(usage.storageBytesLimit)}
        percentage={usage.storageBytesPercentage}
      />
      <UsageMetricCard
        icon={FileStack}
        title="AI Doc Processing"
        description="Smart document chunking"
        value={usage.agenticChunking.toLocaleString()}
        limit={usage.agenticChunkingLimit.toLocaleString()}
        percentage={usage.agenticChunkingPercentage}
      />
    </div>
  )
}
