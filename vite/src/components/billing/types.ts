export type { UsageStatsResponse } from '@/client'

export type PlanTier = 'free' | 'standard' | 'professional' | 'enterprise'

export const TIER_ORDER: PlanTier[] = ['free', 'standard', 'professional', 'enterprise']
