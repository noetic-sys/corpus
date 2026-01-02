import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Check, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { usePlans } from '@/hooks/use-plans'
import type { PlanTier } from '../types'
import { TIER_STYLES } from '../utils/tier-styles'
import { DashboardSkeleton } from './dashboard-skeleton'

export function NoSubscriptionView() {
  const { getToken } = useAuth()
  const { data: plansData, isLoading: isLoadingPlans } = usePlans()
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubscribe = async (tier: PlanTier) => {
    setIsCreating(true)
    setError(null)

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
        throw new Error(`Failed to create subscription: ${response.status}`)
      }

      const data = await response.json()
      window.location.href = data.checkout_url
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
      console.error('Error creating subscription:', errorMessage)
    } finally {
      setIsCreating(false)
    }
  }

  if (isLoadingPlans) {
    return <DashboardSkeleton />
  }

  return (
    <div className="space-y-6">
      <Alert style="blocky">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          You don't have an active subscription. Choose a plan to get started.
        </AlertDescription>
      </Alert>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {plansData?.plans.map((plan) => {
          const styles = TIER_STYLES[plan.tier] || TIER_STYLES.free
          const isFree = plan.tier === 'free'

          return (
            <Card key={plan.tier} variant="blocky">
              <CardHeader>
                <Badge variant="outline" style="blocky" className={styles.badgeClass}>
                  {plan.name}
                </Badge>
                <CardDescription>{plan.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-2xl font-semibold">{plan.price_formatted}</p>
                  <p className="text-xs text-muted-foreground">
                    {isFree ? 'forever' : `per ${plan.billing_period}`}
                  </p>
                </div>
                <ul className="space-y-1 text-sm">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-center gap-2 text-muted-foreground">
                      <Check className="h-3 w-3" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <Button
                  onClick={() => handleSubscribe(plan.tier as PlanTier)}
                  disabled={isCreating}
                  variant="outline"
                  style="blocky"
                  className="w-full"
                >
                  {isCreating ? 'Creating...' : isFree ? 'Get Started' : 'Subscribe'}
                </Button>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {error && (
        <Alert variant="destructive" style="blocky">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
