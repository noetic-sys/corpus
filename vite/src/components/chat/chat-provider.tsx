import React, {createContext, useCallback, useContext, useEffect, useReducer} from 'react'
import {toast} from 'sonner'
import {ChatConfig, ConnectionStatus, MessageType} from './constants'
import {useWebSocket} from './hooks/use-websocket'
import {useMessageHandler} from './hooks/use-message-handler'
import {useConversationManager} from './hooks/use-conversation-manager'
import type {
  AgentMessageResponse,
  ChatAction,
  ChatState,
  GetHistoryRequest,
  PageContext,
  PermissionMode,
  UserMessageRequest
} from './types'

// Initial state
const initialState: ChatState = {
  isOpen: false,
  currentConversationId: null,
  conversations: [],
  messages: {},
  connectionStatus: ConnectionStatus.DISCONNECTED,
  isLoading: false
}

// Reducer
function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'SET_OPEN':
      return { ...state, isOpen: action.payload }
    case 'SET_CURRENT_CONVERSATION':
      return { ...state, currentConversationId: action.payload }
    case 'ADD_CONVERSATION':
      // Check if conversation already exists to avoid duplicates
      { const existingConv = state.conversations.find(c => c.id === action.payload.id)
      if (existingConv) {
        return state
      }
      return {
        ...state,
        conversations: [...state.conversations, action.payload]
      } }
    case 'SET_CONVERSATIONS':
      return { ...state, conversations: action.payload }
    case 'ADD_MESSAGE':
      { const { conversationId, message } = action.payload
      const currentMessages = state.messages[conversationId] || []
      return {
        ...state,
        messages: {
          ...state.messages,
          [conversationId]: [...currentMessages, message]
        }
      } }
    case 'SET_MESSAGES':
      return {
        ...state,
        messages: {
          ...state.messages,
          [action.payload.conversationId]: action.payload.messages
        }
      }
    case 'SET_CONNECTION_STATUS':
      return { ...state, connectionStatus: action.payload }
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload }
    case 'CLEAR_MESSAGES':
      return {
        ...state,
        messages: {
          ...state.messages,
          [action.payload]: []
        }
      }
    default:
      return state
  }
}

// Context type
interface ChatContextType {
  state: ChatState
  openChat: () => void
  closeChat: () => void
  sendMessage: (content: string, permissionMode: PermissionMode, context?: PageContext) => void
  switchConversation: (conversationId: number) => Promise<void>
  createNewConversation: (context?: PageContext) => Promise<void>
  getHistory: (conversationId: number) => void
  loadConversations: () => Promise<void>
  backToConversationList: () => void
}

const ChatContext = createContext<ChatContextType | null>(null)

// Provider component
export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState)

  // Initialize hooks
  const { handleServerMessage, setCurrentConversationId } = useMessageHandler({ dispatch })
  
  const { connectWebSocket, sendMessage: sendWebSocketMessage, closeConnection, cleanup } = useWebSocket({
    onMessage: handleServerMessage,
    onStatusChange: (status) => dispatch({ type: 'SET_CONNECTION_STATUS', payload: status })
  })

  // Update message handler with current conversation ID
  setCurrentConversationId(state.currentConversationId)

  const switchConversation = useCallback(async (conversationId: number) => {
    console.log('Switching to conversation:', conversationId)
    dispatch({ type: 'SET_CURRENT_CONVERSATION', payload: conversationId })
    await connectWebSocket(conversationId)
    
    // Request conversation history
    setTimeout(() => {
      console.log('Requesting conversation history for:', conversationId)
      const historyRequest: GetHistoryRequest = { type: MessageType.GET_HISTORY }
      sendWebSocketMessage(historyRequest)
    }, ChatConfig.HISTORY_REQUEST_DELAY)
  }, [connectWebSocket, sendWebSocketMessage])

  const { loadConversations, createNewConversation } = useConversationManager({ 
    dispatch, 
    switchConversation 
  })

  // Public methods
  const openChat = useCallback(() => {
    dispatch({ type: 'SET_OPEN', payload: true })
    // Load conversations when chat is opened (ensures we have latest data)
    loadConversations()
  }, [loadConversations])

  const closeChat = useCallback(() => {
    dispatch({ type: 'SET_OPEN', payload: false })
  }, [])

  const sendMessage = useCallback((content: string, permissionMode: PermissionMode, context?: PageContext) => {
    if (!state.currentConversationId) {
      toast.error('No active conversation')
      return
    }

    dispatch({ type: 'SET_LOADING', payload: true })

    // Add user message to local state immediately
    const userMessage: AgentMessageResponse = {
      type: MessageType.AGENT_MESSAGE,
      id: Date.now(), // Temporary ID
      role: 'user',
      content,
      toolCalls: null,
      toolCallId: null,
      permissionMode,
      sequenceNumber: 0,
      createdAt: new Date().toISOString()
    }

    dispatch({
      type: 'ADD_MESSAGE',
      payload: {
        conversationId: state.currentConversationId,
        message: userMessage
      }
    })

    // Send to server
    const message: UserMessageRequest = {
      type: MessageType.USER_MESSAGE,
      content,
      permissionMode,
      extraData: context ? { pageContext: context } : null
    }

    sendWebSocketMessage(message)
  }, [state.currentConversationId, sendWebSocketMessage])

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const getHistory = useCallback((_conversationId: number) => {
    const historyRequest: GetHistoryRequest = { type: MessageType.GET_HISTORY }
    sendWebSocketMessage(historyRequest)
  }, [sendWebSocketMessage])

  const backToConversationList = useCallback(() => {
    console.log('Going back to conversation list')
    closeConnection()
    dispatch({ type: 'SET_CURRENT_CONVERSATION', payload: null })
    dispatch({ type: 'SET_CONNECTION_STATUS', payload: ConnectionStatus.DISCONNECTED })
  }, [closeConnection])

  // Cleanup on unmount
  useEffect(() => {
    return cleanup
  }, [cleanup])

  // Load conversations when provider mounts (only if authenticated)
  useEffect(() => {
    // Don't load conversations if not authenticated
    // The loadConversations function will be called when user opens chat
    // This prevents unnecessary API calls and error toasts for logged out users
  }, [])

  const contextValue: ChatContextType = {
    state,
    openChat,
    closeChat,
    sendMessage,
    switchConversation,
    createNewConversation,
    getHistory,
    loadConversations,
    backToConversationList
  }

  return (
    <ChatContext.Provider value={contextValue}>
      {children}
    </ChatContext.Provider>
  )
}

// Hook to use chat context
export function useChat() {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider')
  }
  return context
}