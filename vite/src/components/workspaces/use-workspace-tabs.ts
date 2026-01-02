import { useEffect, useRef } from 'react'
import { useRouter, useSearch, useLocation } from '@tanstack/react-router'
import type { MatrixListResponse } from '@/client'
import type { WorkspaceSearch } from '@/routes/workspaces.$workspaceId'

interface UseWorkspaceTabsProps {
  matrices: MatrixListResponse[]
}

export function useWorkspaceTabs({ matrices }: UseWorkspaceTabsProps): {
  activeTab: 'workflows' | number
  handleTabChange: (value: number | 'workflows') => void
} {
  const router = useRouter()
  const location = useLocation()
  const search = useSearch({ from: '/workspaces/$workspaceId' }) as WorkspaceSearch
  const hasInitialized = useRef(false)

  // URL is source of truth - no state needed
  const matrixParam = search.matrix

  // Active tab can be "workflows" or a matrix ID
  const activeTab: 'workflows' | number = matrixParam && matrices.some(m => m.id === matrixParam)
    ? matrixParam
    : 'workflows'

  // Set default to workflows tab on mount if needed
  useEffect(() => {
    if (hasInitialized.current) return

    if (!matrixParam) {
      hasInitialized.current = true
      // Default to workflows tab
    } else {
      hasInitialized.current = true
    }
  }, [matrixParam, matrices, router, location.pathname])

  // Update URL when tab changes - NO state update
  const handleTabChange = (value: number | string) => {
    console.log(`[handleTabChange] START at ${performance.now().toFixed(2)}ms`)

    if (value === 'workflows') {
      // Navigate to workflows tab - remove matrix param
      router.navigate({
        to: location.pathname,
        search: {},
        replace: true
      })
    } else {
      // Navigate to matrix tab
      router.navigate({
        to: location.pathname,
        search: { matrix: value as number },
        replace: true
      })
    }
    console.log(`[handleTabChange] after router.navigate at ${performance.now().toFixed(2)}ms`)
  }

  return {
    activeTab,
    handleTabChange
  }
}