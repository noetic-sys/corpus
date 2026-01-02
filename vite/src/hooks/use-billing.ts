import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import {
  getSubscriptionStatusApiV1BillingStatusGet,
  getUsageStatsApiV1BillingUsageGet,
  checkCellOperationQuotaApiV1BillingQuotaCellOperationsGet,
} from '@/client'
import { apiClient } from '@/lib/api'
import { throwApiError } from '@/lib/api-error'

export function useSubscriptionStatus() {
  const { getToken } = useAuth()

  return useQuery({
    queryKey: ['billing', 'status'],
    queryFn: async () => {
      const token = await getToken()

      const response = await getSubscriptionStatusApiV1BillingStatusGet({
        client: apiClient,
        headers: {
          authorization: `Bearer ${token}`,
        },
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to fetch subscription status')
      }

      return response.data!
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    refetchOnMount: 'always', // Always refetch when returning from Stripe checkout
    retry: false, // Don't retry - backend will create subscription if missing
  })
}

export function useUsageStats() {
  const { getToken } = useAuth()

  return useQuery({
    queryKey: ['billing', 'usage'],
    queryFn: async () => {
      const token = await getToken()

      const response = await getUsageStatsApiV1BillingUsageGet({
        client: apiClient,
        headers: {
          authorization: `Bearer ${token}`,
        },
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to fetch usage stats')
      }

      return response.data!
    },
    staleTime: 1000 * 60, // 1 minute
    refetchOnMount: 'always', // Always refetch when returning from Stripe checkout
    refetchInterval: 1000 * 60 * 2, // Refetch every 2 minutes
    retry: false, // Don't retry - backend will create subscription if missing
  })
}

export function useCellOperationQuota() {
  const { getToken } = useAuth()

  return useQuery({
    queryKey: ['billing', 'quota', 'cell-operations'],
    queryFn: async () => {
      const token = await getToken()

      const response = await checkCellOperationQuotaApiV1BillingQuotaCellOperationsGet({
        client: apiClient,
        headers: {
          authorization: `Bearer ${token}`,
        },
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to fetch cell operation quota')
      }

      return response.data!
    },
    staleTime: 1000 * 30, // 30 seconds
    retry: false, // Don't retry on billing errors
  })
}
