// WebSocket message types matching backend schemas
import { MessageType, ConnectionStatus } from './constants'

// Permission modes matching backend ToolPermission enum
export type PermissionMode = 'read' | 'write'

// Client message types (sent to server)
export interface ClientMessage {
  type: string
}

export interface UserMessageRequest extends ClientMessage {
  type: typeof MessageType.USER_MESSAGE
  content: string
  permissionMode: PermissionMode
  extraData?: Record<string, unknown> | null
}

export interface GetHistoryRequest extends ClientMessage {
  type: typeof MessageType.GET_HISTORY
}

export interface PingRequest extends ClientMessage {
  type: typeof MessageType.PING
}

// Server message types (received from server)
export interface ServerMessage {
  type: string
}

export interface ConnectedResponse extends ServerMessage {
  type: typeof MessageType.CONNECTED
  conversationId: number
  title: string
}

export interface MessageReceivedResponse extends ServerMessage {
  type: typeof MessageType.MESSAGE_RECEIVED
  content: string
}

export interface AgentMessageResponse extends ServerMessage {
  type: typeof MessageType.AGENT_MESSAGE
  id: number
  role: 'user' | 'assistant' | 'tool'
  content: string
  toolCalls?: ToolCall[] | null
  toolCallId?: string | null
  permissionMode: PermissionMode
  sequenceNumber: number
  createdAt: string
}

export interface ResponseCompleteResponse extends ServerMessage {
  type: typeof MessageType.RESPONSE_COMPLETE
}

export interface ConversationHistoryResponse extends ServerMessage {
  type: typeof MessageType.CONVERSATION_HISTORY
  messages: AgentMessageResponse[]
}

export interface ErrorResponse extends ServerMessage {
  type: typeof MessageType.ERROR
  error: string
  code?: string | null
}

export interface PongResponse extends ServerMessage {
  type: typeof MessageType.PONG
}

// Tool call types
export interface ToolCall {
  id: string
  type: string
  function: {
    name: string
    arguments: string
  }
}

// Chat state types
export interface ChatState {
  isOpen: boolean
  currentConversationId: number | null
  conversations: Conversation[]
  messages: Record<number, AgentMessageResponse[]>
  connectionStatus: ConnectionStatus
  isLoading: boolean
}

export interface Conversation {
  id: number
  title: string | null
  extraData?: Record<string, unknown> | null
  aiModelId?: number | null
  isActive?: boolean
  createdAt: string
  updatedAt: string
}

// Page context for providing relevant information to the agent
export interface PageContext {
  page: string
  matrixId?: number
  workspaceId?: number
  documentId?: number
  questionId?: number
  [key: string]: unknown
}

// Chat reducer actions
export type ChatAction = 
  | { type: 'SET_OPEN'; payload: boolean }
  | { type: 'SET_CURRENT_CONVERSATION'; payload: number | null }
  | { type: 'ADD_CONVERSATION'; payload: Conversation }
  | { type: 'SET_CONVERSATIONS'; payload: Conversation[] }
  | { type: 'ADD_MESSAGE'; payload: { conversationId: number; message: AgentMessageResponse } }
  | { type: 'SET_MESSAGES'; payload: { conversationId: number; messages: AgentMessageResponse[] } }
  | { type: 'SET_CONNECTION_STATUS'; payload: ConnectionStatus }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'CLEAR_MESSAGES'; payload: number }