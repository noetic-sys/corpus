import { Calendar, CreditCard, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import type { SubscriptionStatusResponse } from '@/client'
import { getTierBadgeClass, getStatusBadgeClass } from '../utils/tier-styles'
import { formatDate } from '../utils/formatting'

interface SubscriptionCardProps {
  subscription: SubscriptionStatusResponse
  onManageSubscription: () => void
  isLoading: boolean
  error: string | null
}

export function SubscriptionCard({
  subscription,
  onManageSubscription,
  isLoading,
  error,
}: SubscriptionCardProps) {
  const isFreeTier = subscription.tier === 'free'

  return (
    <Card variant="blocky">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Subscription</CardTitle>
            <CardDescription>Current plan and status</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" style="blocky" className={getTierBadgeClass(subscription.tier)}>
              {subscription.tier.toUpperCase()}
            </Badge>
            <Badge variant="outline" style="blocky" className={getStatusBadgeClass(subscription.status)}>
              {subscription.status.toUpperCase()}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Current Period</p>
              <p className="text-sm font-medium">
                {formatDate(subscription.current_period_start)} -{' '}
                {formatDate(subscription.current_period_end)}
              </p>
            </div>
          </div>
          {subscription.cancelled_at && (
            <div>
              <p className="text-xs text-muted-foreground">Cancelled</p>
              <p className="text-sm font-medium">{formatDate(subscription.cancelled_at)}</p>
            </div>
          )}
          {subscription.suspended_at && (
            <div>
              <p className="text-xs text-muted-foreground">Suspended</p>
              <p className="text-sm font-medium">{formatDate(subscription.suspended_at)}</p>
            </div>
          )}
        </div>

        {!isFreeTier && (
          <div className="flex items-center gap-3 pt-4 border-t">
            <Button
              onClick={onManageSubscription}
              disabled={isLoading}
              variant="outline"
              style="blocky"
              className="gap-2"
            >
              <CreditCard className="h-4 w-4" />
              {isLoading ? 'Opening...' : 'Manage Subscription'}
            </Button>
          </div>
        )}

        {error && (
          <Alert variant="destructive" style="blocky">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}
