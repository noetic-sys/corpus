import { useAuth } from '@/hooks/useAuth'
import { Link, useRouterState } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { BackButton } from '@/components/ui/back-button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Badge } from '@/components/ui/badge'
import { useSubscriptionStatus, useUsageStats } from '@/hooks/use-billing'
import { LogIn, LogOut, User, ChevronRight } from 'lucide-react'

function formatBytes(bytes: number) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

function getTierBadgeClass(tier: string): string {
  switch (tier.toLowerCase()) {
    case 'free': return 'bg-gray-100 text-gray-800 border-gray-300'
    case 'starter': return 'bg-blue-100 text-blue-800 border-blue-300'
    case 'professional': return 'bg-purple-100 text-purple-800 border-purple-300'
    case 'business': return 'bg-indigo-100 text-indigo-800 border-indigo-300'
    case 'enterprise': return 'bg-amber-100 text-amber-800 border-amber-300'
    default: return 'bg-gray-100 text-gray-800 border-gray-300'
  }
}

function UsageTooltipContent() {
  const { data: subscription, isLoading: loadingSub } = useSubscriptionStatus()
  const { data: usage, isLoading: loadingUsage } = useUsageStats()

  if (loadingSub || loadingUsage) {
    return <div className="text-xs text-muted-foreground">Loading...</div>
  }

  if (!subscription || !usage) {
    return <div className="text-xs text-muted-foreground">No subscription</div>
  }

  const maxUsage = Math.max(
    usage.cellOperationsPercentage,
    usage.agenticQaPercentage,
    usage.workflowsPercentage,
    usage.storageBytesPercentage,
    usage.agenticChunkingPercentage
  )

  const isNearLimit = (pct: number) => pct >= 80

  return (
    <div className="space-y-2 min-w-[180px]">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-muted-foreground">Plan</span>
        <Badge variant="outline" style="blocky" className={`${getTierBadgeClass(subscription.tier)} text-[10px] px-1.5 py-0`}>
          {subscription.tier.toUpperCase()}
        </Badge>
      </div>
      <div className="border-t pt-2 space-y-1.5">
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Cells</span>
          <span className={isNearLimit(usage.cellOperationsPercentage) ? 'text-destructive font-medium' : ''}>
            {usage.cellOperations.toLocaleString()}/{usage.cellOperationsLimit.toLocaleString()}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Agentic QA</span>
          <span className={isNearLimit(usage.agenticQaPercentage) ? 'text-destructive font-medium' : ''}>
            {usage.agenticQa.toLocaleString()}/{usage.agenticQaLimit.toLocaleString()}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Workflows</span>
          <span className={isNearLimit(usage.workflowsPercentage) ? 'text-destructive font-medium' : ''}>
            {usage.workflows.toLocaleString()}/{usage.workflowsLimit.toLocaleString()}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Storage</span>
          <span className={isNearLimit(usage.storageBytesPercentage) ? 'text-destructive font-medium' : ''}>
            {formatBytes(usage.storageBytes)}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">AI Docs</span>
          <span className={isNearLimit(usage.agenticChunkingPercentage) ? 'text-destructive font-medium' : ''}>
            {usage.agenticChunking.toLocaleString()}/{usage.agenticChunkingLimit.toLocaleString()}
          </span>
        </div>
      </div>
      <div className="border-t pt-2 flex items-center justify-between text-xs">
        <span className={`font-medium ${isNearLimit(maxUsage) ? 'text-destructive' : 'text-muted-foreground'}`}>
          {maxUsage.toFixed(0)}% peak usage
        </span>
        <ChevronRight className="w-3 h-3 text-muted-foreground" />
      </div>
    </div>
  )
}

export function AuthHeader() {
  const { user, isLoading, login, logout } = useAuth()
  const routerState = useRouterState()

  // Check if we're on a workspace detail page
  const isWorkspaceDetailPage = routerState.location.pathname.startsWith('/workspaces/') &&
    routerState.location.pathname !== '/workspaces'

  if (isLoading) {
    return (
      <div className="flex items-center justify-between p-4 border-b">
        <div className="text-sm text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="flex items-center justify-between p-4 border-b">
        <div className="text-sm font-medium">Corpus</div>
        <Button style="blocky" onClick={() => login()}>
          <LogIn className="w-4 h-4 mr-2" />
          Sign in with Google
        </Button>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-between p-4 border-b">
      {/* Left side - Conditionally show back button */}
      <div className="flex items-center gap-4">
        {isWorkspaceDetailPage && <BackButton toMatricesList={true} label="Back to Workspaces" />}
      </div>

      {/* Right side - Always show user info + logout */}
      <div className="flex items-center gap-4">
        <Tooltip>
          <TooltipTrigger asChild>
            <Link
              to="/billing"
              className="flex items-center gap-2 text-sm hover:text-primary transition-colors cursor-pointer rounded-md px-2 py-1 hover:bg-muted"
            >
              <User className="w-4 h-4" />
              <span>{user.name || user.email || 'User'}</span>
            </Link>
          </TooltipTrigger>
          <TooltipContent side="bottom" align="end" className="p-3">
            <UsageTooltipContent />
          </TooltipContent>
        </Tooltip>
        <Button
          variant="outline"
          style="blocky"
          size="sm"
          onClick={() => logout()}
        >
          <LogOut className="w-4 h-4 mr-2" />
          Log out
        </Button>
      </div>
    </div>
  )
}
