import { useCallback, useRef } from 'react'
import { toast } from 'sonner'
import { MessageType } from '../constants'
import type { 
  ServerMessage, 
  AgentMessageResponse, 
  ChatAction,
  ConnectedResponse,
  ConversationHistoryResponse,
  ErrorResponse
} from '../types'

interface UseMessageHandlerProps {
  dispatch: React.Dispatch<ChatAction>
}

export function useMessageHandler({ dispatch }: UseMessageHandlerProps) {
  // Use ref to get current conversation ID to avoid stale closure
  const currentConversationIdRef = useRef<number | null>(null)

  const setCurrentConversationId = useCallback((id: number | null) => {
    currentConversationIdRef.current = id
  }, [])

  const handleServerMessage = useCallback((message: ServerMessage) => {
    switch (message.type) {
      case MessageType.CONNECTED:
        { const connectedMsg = message as ConnectedResponse
        // Add conversation if not exists
        dispatch({
          type: 'ADD_CONVERSATION',
          payload: {
            id: connectedMsg.conversationId,
            title: connectedMsg.title,
            extraData: null,
            aiModelId: null,
            isActive: true,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          }
        })
        break }

      case MessageType.AGENT_MESSAGE:
        { const agentMsg = message as AgentMessageResponse
        const currentConvId = currentConversationIdRef.current
        if (currentConvId) {
          dispatch({
            type: 'ADD_MESSAGE',
            payload: {
              conversationId: currentConvId,
              message: agentMsg
            }
          })
        }
        break }

      case MessageType.CONVERSATION_HISTORY:
        { const historyMsg = message as ConversationHistoryResponse
        const currentConvIdForHistory = currentConversationIdRef.current
        if (currentConvIdForHistory) {
          dispatch({
            type: 'SET_MESSAGES',
            payload: {
              conversationId: currentConvIdForHistory,
              messages: historyMsg.messages || []
            }
          })
        }
        break }

      case MessageType.MESSAGE_RECEIVED:
        break

      case MessageType.RESPONSE_COMPLETE:
        dispatch({ type: 'SET_LOADING', payload: false })
        break

      case MessageType.ERROR:
        { const errorMsg = message as ErrorResponse
        console.error('Server error:', errorMsg.error)
        toast.error('Chat Error', {
          description: errorMsg.error
        })
        dispatch({ type: 'SET_LOADING', payload: false })
        break }

      case MessageType.PONG:
        break

      default:
        break
    }
  }, [dispatch])

  return {
    handleServerMessage,
    setCurrentConversationId
  }
}