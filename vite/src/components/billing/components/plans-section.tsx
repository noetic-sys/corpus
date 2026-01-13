import { ArrowUpCircle, Check, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import type { PlanInfo } from '@/client'
import type { UsageStatsResponse, PlanTier } from '../types'
import { TIER_ORDER } from '../types'
import { TIER_STYLES } from '../utils/tier-styles'

interface PlansSectionProps {
  plans: PlanInfo[]
  currentTier: string
  usage: UsageStatsResponse
  onChangePlan: (tier: PlanTier) => void
  isLoading: boolean
  error: string | null
}

export function PlansSection({
  plans,
  currentTier,
  usage,
  onChangePlan,
  isLoading,
  error,
}: PlansSectionProps) {
  const maxUsage = Math.max(
    usage.cellOperationsPercentage,
    usage.agenticQaPercentage,
    usage.workflowsPercentage,
    usage.storageBytesPercentage
  )
  const isNearLimit = maxUsage >= 80

  const currentTierLower = currentTier.toLowerCase() as PlanTier
  const currentTierIndex = TIER_ORDER.indexOf(currentTierLower)

  const getButtonLabel = (tier: PlanTier): string => {
    if (tier === currentTierLower) return 'Current Plan'
    const tierIndex = TIER_ORDER.indexOf(tier)
    if (tierIndex > currentTierIndex) return 'Upgrade'
    return 'Downgrade'
  }

  const isCurrentTier = (tier: string): boolean => tier.toLowerCase() === currentTierLower

  return (
    <Card variant="blocky">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <ArrowUpCircle className="h-5 w-5" />
              Subscription Plans
            </CardTitle>
            <CardDescription>
              {currentTierLower === 'enterprise'
                ? "You're on our highest tier with maximum capacity."
                : isNearLimit
                  ? "You're approaching your limits. Consider upgrading for more capacity."
                  : 'Manage your subscription or upgrade for more capacity.'}
            </CardDescription>
          </div>
          {isNearLimit && currentTierLower !== 'enterprise' && (
            <Badge variant="outline" style="blocky" className="bg-orange-100 text-orange-800 border-orange-300">
              Upgrade Recommended
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {plans.map((plan) => {
            const styles = TIER_STYLES[plan.tier] || TIER_STYLES.free
            const isCurrent = isCurrentTier(plan.tier)

            return (
              <Card
                key={plan.tier}
                variant="blocky"
                className={isCurrent ? `${styles.cardBorderClass} ${styles.cardBgClass}` : ''}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" style="blocky" className={styles.badgeClass}>
                      {plan.name}
                    </Badge>
                    {isCurrent && (
                      <span className="text-xs text-muted-foreground font-medium">Current</span>
                    )}
                  </div>
                  <div className="mt-2">
                    <span className="text-2xl font-semibold">{plan.price_formatted}</span>
                    <span className="text-muted-foreground text-sm">/{plan.billing_period}</span>
                  </div>
                </CardHeader>

                <CardContent className="space-y-3">
                  <ul className="space-y-1 text-sm">
                    {plan.features.map((feature, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-muted-foreground">
                        <Check className="h-3 w-3" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <Button
                    onClick={() => onChangePlan(plan.tier as PlanTier)}
                    disabled={isLoading || isCurrent}
                    variant={isCurrent ? 'secondary' : 'outline'}
                    style="blocky"
                    className="w-full"
                  >
                    {isLoading ? 'Processing...' : getButtonLabel(plan.tier as PlanTier)}
                  </Button>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {error && (
          <Alert variant="destructive" style="blocky" className="mt-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}
