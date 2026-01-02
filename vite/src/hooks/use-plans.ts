import { useQuery } from '@tanstack/react-query'
import { getPlansApiV1BillingPlansGet } from '@/client'
import { apiClient } from '@/lib/api'
import { throwApiError } from '@/lib/api-error'

export type { PlanInfo, PlanLimits, PlansResponse } from '@/client'

export function usePlans() {
  return useQuery({
    queryKey: ['billing', 'plans'],
    queryFn: async () => {
      const response = await getPlansApiV1BillingPlansGet({
        client: apiClient,
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to fetch plans')
      }

      return response.data!
    },
    staleTime: 1000 * 60 * 60, // 1 hour - plans don't change often
    gcTime: 1000 * 60 * 60 * 24, // Keep in cache for 24 hours
  })
}

// Helper to get a specific plan by tier
export function usePlan(tier: string) {
  const { data, ...rest } = usePlans()

  return {
    ...rest,
    data: data?.plans.find(p => p.tier === tier),
  }
}
