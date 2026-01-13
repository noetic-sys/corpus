import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { TrendingUp, AlertCircle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useSubscriptionStatus, useUsageStats } from '@/hooks/use-billing'
import { usePlans } from '@/hooks/use-plans'
import type { PlanTier } from './types'
import { formatDate } from './utils/formatting'
import { DashboardSkeleton } from './components/dashboard-skeleton'
import { SubscriptionCard } from './components/subscription-card'
import { UsageMetricsGrid } from './components/usage-metrics-grid'
import { PlansSection } from './components/plans-section'
import { NoSubscriptionView } from './components/no-subscription-view'

export function BillingDashboard() {
  const { getToken } = useAuth()
  const { data: subscription, isLoading: isLoadingSubscription, error: subscriptionError } = useSubscriptionStatus()
  const { data: usage, isLoading: isLoadingUsage, error: usageError } = useUsageStats()
  const { data: plansData, isLoading: isLoadingPlans } = usePlans()
  const [isOpeningPortal, setIsOpeningPortal] = useState(false)
  const [portalError, setPortalError] = useState<string | null>(null)

  if (subscriptionError) {
    const errorMessage = (subscriptionError as Error)?.message || ''
    if (errorMessage.includes('404') || errorMessage.includes('No subscription')) {
      return <NoSubscriptionView />
    }
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>Failed to load billing information. Please try again later.</AlertDescription>
      </Alert>
    )
  }

  if (usageError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>Failed to load usage information. Please try again later.</AlertDescription>
      </Alert>
    )
  }

  if (isLoadingSubscription || isLoadingUsage || isLoadingPlans) {
    return <DashboardSkeleton />
  }

  if (!subscription || !usage || !plansData) {
    return null
  }

  const handleManageSubscription = async () => {
    setIsOpeningPortal(true)
    setPortalError(null)

    try {
      const token = await getToken()
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/billing/portal`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ return_url: `${window.location.origin}/billing` }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || `Failed to open portal: ${response.status}`)
      }

      const data = await response.json()
      window.location.href = data.portal_url
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setPortalError(errorMessage)
      console.error('Error opening portal:', errorMessage)
    } finally {
      setIsOpeningPortal(false)
    }
  }

  const handleChangePlan = async (tier: PlanTier) => {
    setIsOpeningPortal(true)
    setPortalError(null)

    try {
      const token = await getToken()
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/billing/checkout`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tier,
          success_url: `${window.location.origin}/billing`,
          cancel_url: `${window.location.origin}/billing`,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || `Failed to change plan: ${response.status}`)
      }

      const data = await response.json()
      window.location.href = data.checkout_url
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setPortalError(errorMessage)
      console.error('Error changing plan:', errorMessage)
    } finally {
      setIsOpeningPortal(false)
    }
  }

  return (
    <div className="space-y-6">
      <SubscriptionCard
        subscription={subscription}
        onManageSubscription={handleManageSubscription}
        isLoading={isOpeningPortal}
        error={portalError}
      />

      <UsageMetricsGrid usage={usage} />

      <PlansSection
        plans={plansData.plans}
        currentTier={subscription.tier}
        usage={usage}
        onChangePlan={handleChangePlan}
        isLoading={isOpeningPortal}
        error={portalError}
      />

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <TrendingUp className="h-4 w-4" />
        <span>
          Usage period: {formatDate(usage.periodStart)} - {formatDate(usage.periodEnd)}
        </span>
      </div>
    </div>
  )
}
