import type { LucideIcon } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'

interface UsageMetricCardProps {
  icon: LucideIcon
  title: string
  description: string
  value: string
  limit: string
  percentage: number
}

export function UsageMetricCard({
  icon: Icon,
  title,
  description,
  value,
  limit,
  percentage,
}: UsageMetricCardProps) {
  return (
    <Card variant="blocky">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-baseline justify-between">
          <span className="text-2xl font-semibold">{value}</span>
          <span className="text-xs text-muted-foreground">/ {limit}</span>
        </div>
        <Progress value={percentage} />
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">{percentage.toFixed(1)}% used</p>
          {percentage >= 80 && (
            <span className="text-xs text-destructive font-medium">Approaching limit</span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
