import {useCallback, useRef} from 'react'
import {ChatConfig, ConnectionStatus, WebSocketCloseCode, WebSocketCloseReason} from '../constants'
import type {GetHistoryRequest, PingRequest, ServerMessage, UserMessageRequest} from '../types'
import { useAuth } from '@/hooks/useAuth'

interface UseWebSocketProps {
  onMessage: (message: ServerMessage) => void
  onStatusChange: (status: ConnectionStatus) => void
}

export function useWebSocket({ onMessage, onStatusChange }: UseWebSocketProps) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const reconnectAttempts = useRef(0)
  const { getToken } = useAuth()

  const connectWebSocket = useCallback(async (conversationId: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close()
    }

    onStatusChange(ConnectionStatus.CONNECTING)

    try {
      // Get access token for WebSocket authentication
      const token = await getToken()

      // Use dedicated WebSocket URL from environment
      const wsBaseUrl = import.meta.env.VITE_WS_URL!
      const wsUrl = `${wsBaseUrl}/api/v1/agents/conversations/${conversationId}/ws?token=${encodeURIComponent(token)}`

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        onStatusChange(ConnectionStatus.CONNECTED)
        reconnectAttempts.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const message: ServerMessage = JSON.parse(event.data)
          onMessage(message)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      ws.onclose = (event) => {
        onStatusChange(ConnectionStatus.DISCONNECTED)
        
        // Auto-reconnect unless it was a manual close
        if (event.code !== WebSocketCloseCode.NORMAL && reconnectAttempts.current < ChatConfig.MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000)
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++
            connectWebSocket(conversationId)
          }, delay)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        onStatusChange(ConnectionStatus.ERROR)
      }

    } catch (error) {
      console.error('Error creating WebSocket or getting token:', error)
      onStatusChange(ConnectionStatus.ERROR)
    }
  }, [onMessage, onStatusChange, getToken])

  const sendMessage = useCallback((message: UserMessageRequest | GetHistoryRequest | PingRequest) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
      return true
    }
    return false
  }, [])

  const closeConnection = useCallback((reason?: string) => {
    if (wsRef.current) {
      wsRef.current.close(WebSocketCloseCode.NORMAL, reason || WebSocketCloseReason.USER_NAVIGATED_BACK)
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
  }, [])

  const cleanup = useCallback(() => {
    closeConnection(WebSocketCloseReason.COMPONENT_UNMOUNTING)
  }, [closeConnection])

  return {
    connectWebSocket,
    sendMessage,
    closeConnection,
    cleanup
  }
}