import { createFileRoute, Link } from '@tanstack/react-router'
import { ChevronLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { BillingDashboard } from '@/components/billing/billing-dashboard'

export const Route = createFileRoute('/billing')({
  component: BillingPage,
})

function BillingPage() {
  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="mb-8">
        <Link to="/workspaces">
          <Button variant="ghost" size="sm" className="mb-4 -ml-2 gap-1 text-muted-foreground hover:text-foreground">
            <ChevronLeft className="h-4 w-4" />
            Back to Workspaces
          </Button>
        </Link>
        <h1 className="text-2xl font-bold tracking-tight">Billing & Usage</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Monitor your subscription and usage metrics
        </p>
      </div>
      <BillingDashboard />
    </div>
  )
}
