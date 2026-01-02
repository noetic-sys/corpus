export const TIER_STYLES: Record<string, { badgeClass: string; cardBorderClass: string; cardBgClass: string }> = {
  free: {
    badgeClass: 'bg-gray-100 text-gray-800 border-gray-300',
    cardBorderClass: 'border-gray-300',
    cardBgClass: 'bg-gray-50',
  },
  starter: {
    badgeClass: 'bg-blue-100 text-blue-800 border-blue-300',
    cardBorderClass: 'border-blue-300',
    cardBgClass: 'bg-blue-50',
  },
  professional: {
    badgeClass: 'bg-purple-100 text-purple-800 border-purple-300',
    cardBorderClass: 'border-purple-300',
    cardBgClass: 'bg-purple-50',
  },
  business: {
    badgeClass: 'bg-indigo-100 text-indigo-800 border-indigo-300',
    cardBorderClass: 'border-indigo-300',
    cardBgClass: 'bg-indigo-50',
  },
  enterprise: {
    badgeClass: 'bg-amber-100 text-amber-800 border-amber-300',
    cardBorderClass: 'border-amber-300',
    cardBgClass: 'bg-amber-50',
  },
}

export function getTierBadgeClass(tier: string): string {
  const styles = TIER_STYLES[tier.toLowerCase()]
  return styles?.badgeClass || TIER_STYLES.free.badgeClass
}

export function getStatusBadgeClass(status: string): string {
  switch (status) {
    case 'active':
      return 'bg-green-100 text-green-800 border-green-300'
    case 'cancelled':
      return 'bg-orange-100 text-orange-800 border-orange-300'
    case 'suspended':
    case 'past_due':
      return 'bg-red-100 text-red-800 border-red-300'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-300'
  }
}
