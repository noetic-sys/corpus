import {useLocation} from '@tanstack/react-router'
import {useMemo} from 'react'
import type {PageContext} from '../types'

export function usePageContext(): PageContext {
  const location = useLocation()

  return useMemo(() => {
    const context: PageContext = {
      page: 'unknown'
    }

    // Parse the pathname to determine context
    const pathParts = location.pathname.split('/').filter(Boolean)

    if (pathParts.length === 0) {
      context.page = 'home'
      return context
    }

    switch (pathParts[0]) {
      case 'workspaces':
        context.page = 'workspace'
        if (pathParts[1]) {
          context.workspaceId = parseInt(pathParts[1])
        }
        break

      case 'matrices':
        context.page = 'matrix'
        if (pathParts[1]) {
          context.matrixId = parseInt(pathParts[1])
        }

        // Check for specific matrix views
        if (pathParts[2] === 'interactive') {
          context.page = 'matrix-interactive'
        } else if (pathParts[2] === 'documents') {
          context.page = 'matrix-documents'
        } else if (pathParts[2] === 'questions') {
          context.page = 'matrix-questions'
        }
        break

      case 'documents':
        context.page = 'document'
        if (pathParts[1]) {
          context.documentId = parseInt(pathParts[1])
        }
        break

      case 'questions':
        context.page = 'question'
        if (pathParts[1]) {
          context.questionId = parseInt(pathParts[1])
        }
        break

      default:
        context.page = pathParts[0]
        break
    }

    // Add search params as additional context
    if (location.search) {
      for (const [key, value] of Object.entries(location.search)) {
        // Convert numeric strings to numbers for common ID fields
        if (key.toLowerCase().includes('id') && typeof value === 'string' && /^\d+$/.test(value)) {
          context[key] = parseInt(value)
        } else {
          context[key] = value
        }
      }
    }

    return context
  }, [location])
}