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
        value={usage.cell_operations.toLocaleString()}
        limit={usage.cell_operations_limit.toLocaleString()}
        percentage={usage.cell_operations_percentage}
      />
      <UsageMetricCard
        icon={Bot}
        title="Agentic QA"
        description="AI agent queries"
        value={usage.agentic_qa.toLocaleString()}
        limit={usage.agentic_qa_limit.toLocaleString()}
        percentage={usage.agentic_qa_percentage}
      />
      <UsageMetricCard
        icon={Workflow}
        title="Workflows"
        description="Workflow executions"
        value={usage.workflows.toLocaleString()}
        limit={usage.workflows_limit.toLocaleString()}
        percentage={usage.workflows_percentage}
      />
      <UsageMetricCard
        icon={FileText}
        title="Documents"
        description="Document uploads"
        value={usage.documents.toLocaleString()}
        limit={usage.documents_limit.toLocaleString()}
        percentage={usage.documents_percentage}
      />
      <UsageMetricCard
        icon={HardDrive}
        title="Storage"
        description="File storage used"
        value={formatBytes(usage.storage_bytes)}
        limit={formatBytes(usage.storage_bytes_limit)}
        percentage={usage.storage_bytes_percentage}
      />
      <UsageMetricCard
        icon={FileStack}
        title="AI Doc Processing"
        description="Smart document chunking"
        value={usage.agentic_chunking.toLocaleString()}
        limit={usage.agentic_chunking_limit.toLocaleString()}
        percentage={usage.agentic_chunking_percentage}
      />
    </div>
  )
}
