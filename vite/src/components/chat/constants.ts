export const ConnectionStatus = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error'
} as const

export type ConnectionStatus = typeof ConnectionStatus[keyof typeof ConnectionStatus]

export const MessageType = {
  CONNECTED: 'connected',
  AGENT_MESSAGE: 'agent_message',
  CONVERSATION_HISTORY: 'conversation_history',
  MESSAGE_RECEIVED: 'message_received',
  RESPONSE_COMPLETE: 'response_complete',
  ERROR: 'error',
  PONG: 'pong',
  USER_MESSAGE: 'user_message',
  GET_HISTORY: 'get_history',
  PING: 'ping'
} as const

export type MessageType = typeof MessageType[keyof typeof MessageType]

export const WebSocketCloseCode = {
  NORMAL: 1000
} as const

export type WebSocketCloseCode = typeof WebSocketCloseCode[keyof typeof WebSocketCloseCode]

export const WebSocketCloseReason = {
  USER_NAVIGATED_BACK: 'User navigated back to conversation list',
  COMPONENT_UNMOUNTING: 'Component unmounting'
} as const

export const ChatConfig = {
  MAX_RECONNECT_ATTEMPTS: 5,
  HISTORY_REQUEST_DELAY: 100
} as const