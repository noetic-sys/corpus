import {useCallback} from 'react'
import { useAuth } from '@/hooks/useAuth'
import {toast} from 'sonner'
import type {ConversationCreate, ConversationResponse} from '@/client'
import {
  createConversationApiV1AgentsConversationsPost,
  getActiveConversationsApiV1AgentsConversationsGet
} from '@/client'
import {apiClient} from '@/lib/api'
import type {ChatAction, Conversation, PageContext} from '../types'
import { throwApiError } from '@/lib/api-error'

interface UseConversationManagerProps {
  dispatch: React.Dispatch<ChatAction>
  switchConversation: (conversationId: number) => Promise<void>
}

function convertApiConversationToLocal(apiConv: ConversationResponse): Conversation {
  return {
    id: apiConv.id,
    title: apiConv.title || `Chat ${apiConv.id}`,
    extraData: apiConv.extraData,
    aiModelId: apiConv.aiModelId,
    isActive: apiConv.isActive,
    createdAt: apiConv.createdAt,
    updatedAt: apiConv.createdAt // Backend doesn't seem to have updatedAt in the response
  }
}

export function useConversationManager({ dispatch, switchConversation }: UseConversationManagerProps) {
  const { getToken, isAuthenticated } = useAuth()

  const loadConversations = useCallback(async () => {
    // Skip loading if user is not authenticated
    if (!isAuthenticated) {
      return
    }

    try {
      const token = await getToken()

      const response = await getActiveConversationsApiV1AgentsConversationsGet({
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to load conversations')
      }

      if (response.data) {
        const conversations = response.data.map(convertApiConversationToLocal)
        dispatch({ type: 'SET_CONVERSATIONS', payload: conversations })
      }
    } catch (error) {
      console.error('Error loading conversations:', error)
      toast.error('Failed to load conversations')
    }
  }, [dispatch, getToken, isAuthenticated])

  const createNewConversation = useCallback(async (context?: PageContext) => {
    console.log('Creating new conversation with context:', context)
    try {
      const token = await getToken()

      // Determine title based on context
      let title = 'New Chat'
      if (context?.page && context.page !== 'unknown') {
        title = `Chat - ${context.page}`
        if (context.matrixId) {
          title += ` (Matrix #${context.matrixId})`
        }
      }

      const conversationData: ConversationCreate = {
        title,
        extraData: context ? {
          pageContext: context
        } : null
      }

      console.log('Sending conversation creation request:', conversationData)
      const response = await createConversationApiV1AgentsConversationsPost({
        body: conversationData,
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to create conversation')
      }

      console.log('Conversation creation response:', response.data)
      if (response.data) {
        const newConversation = convertApiConversationToLocal(response.data)
        console.log('Converted conversation:', newConversation)
        dispatch({ type: 'ADD_CONVERSATION', payload: newConversation })
        console.log('Switching to new conversation:', newConversation.id)
        await switchConversation(newConversation.id)
      } else {
        console.error('No data in conversation creation response')
      }
    } catch (error) {
      console.error('Error creating conversation:', error)
      toast.error('Failed to create new conversation')
    }
  }, [dispatch, switchConversation, getToken])

  return {
    loadConversations,
    createNewConversation
  }
}