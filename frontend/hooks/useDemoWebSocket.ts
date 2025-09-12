import { useState, useEffect, useCallback, useRef } from 'react'
import { logger } from '@/lib/logger'

interface DemoWebSocketOptions {
  onMessage?: (data: any) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
  autoReconnect?: boolean
  reconnectInterval?: number
}

interface DemoWebSocketReturn {
  isConnected: boolean
  sendMessage: (message: any) => void
  sendChatMessage: (message: string, industry: string, context?: any) => void
  requestMetrics: (scenario?: string) => void
  lastMessage: any
  error: Error | null
  reconnect: () => void
  disconnect: () => void
}

export function useDemoWebSocket(options: DemoWebSocketOptions = {}): DemoWebSocketReturn {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    autoReconnect = true,
    reconnectInterval = 3000
  } = options

  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<any>(null)
  const [error, setError] = useState<Error | null>(null)
  
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const sessionIdRef = useRef<string | null>(null)
  const reconnectAttemptsRef = useRef(0)

  const connect = useCallback(() => {
    try {
      // Clear any existing connection
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close()
      }

      // Create WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      // Use the backend API URL for WebSocket connection
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'localhost:8000'
      // Remove protocol from API URL if present
      const host = apiUrl.replace(/^https?:\/\//, '')
      const wsUrl = `${protocol}//${host}/api/demo/ws`

      // Create new WebSocket connection
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        logger.info('Demo WebSocket connected', { component: 'useDemoWebSocket', action: 'connection_established' })
        setIsConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
        onConnect?.()
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setLastMessage(data)
          
          // Store session ID if provided
          if (data.session_id) {
            sessionIdRef.current = data.session_id
          }
          
          onMessage?.(data)
        } catch (err) {
          logger.error('Failed to parse WebSocket message', err as Error, { 
            component: 'useDemoWebSocket', 
            action: 'message_parse_error' 
          })
        }
      }

      ws.onerror = (event) => {
        logger.error('Demo WebSocket error', undefined, { 
          component: 'useDemoWebSocket', 
          action: 'websocket_error',
          metadata: { event }
        })
        setError(new Error('WebSocket connection error'))
        onError?.(event)
      }

      ws.onclose = () => {
        logger.info('Demo WebSocket disconnected', { component: 'useDemoWebSocket', action: 'connection_closed' })
        setIsConnected(false)
        wsRef.current = null
        onDisconnect?.()

        // Auto-reconnect if enabled
        if (autoReconnect && reconnectAttemptsRef.current < 5) {
          reconnectAttemptsRef.current++
          const delay = reconnectInterval * Math.pow(2, reconnectAttemptsRef.current - 1)
          logger.info(`Attempting to reconnect in ${delay}ms`, { 
            component: 'useDemoWebSocket', 
            action: 'reconnect_scheduled',
            metadata: { delay_ms: delay, attempt: reconnectAttemptsRef.current }
          })
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, delay)
        }
      }
    } catch (err) {
      logger.error('Failed to establish WebSocket connection', err as Error, { 
        component: 'useDemoWebSocket', 
        action: 'connection_failed' 
      })
      setError(err as Error)
    }
  }, [onConnect, onDisconnect, onError, onMessage, autoReconnect, reconnectInterval])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    
    setIsConnected(false)
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      logger.error('WebSocket is not connected', undefined, { 
        component: 'useDemoWebSocket', 
        action: 'send_failed_not_connected' 
      })
      setError(new Error('WebSocket is not connected'))
    }
  }, [])

  const sendChatMessage = useCallback((message: string, industry: string, context?: any) => {
    sendMessage({
      type: 'chat',
      message,
      industry,
      context: context || {},
      session_id: sessionIdRef.current
    })
  }, [sendMessage])

  const requestMetrics = useCallback((scenario: string = 'standard') => {
    sendMessage({
      type: 'metrics',
      scenario,
      session_id: sessionIdRef.current
    })
  }, [sendMessage])

  const reconnect = useCallback(() => {
    disconnect()
    reconnectAttemptsRef.current = 0
    connect()
  }, [connect, disconnect])

  // Connect on mount
  useEffect(() => {
    connect()
    
    // Cleanup on unmount
    return () => {
      disconnect()
    }
  }, []) // Only run once on mount

  // Ping-pong to keep connection alive
  useEffect(() => {
    if (!isConnected) return

    const pingInterval = setInterval(() => {
      sendMessage({ type: 'ping' })
    }, 30000) // Ping every 30 seconds

    return () => clearInterval(pingInterval)
  }, [isConnected, sendMessage])

  return {
    isConnected,
    sendMessage,
    sendChatMessage,
    requestMetrics,
    lastMessage,
    error,
    reconnect,
    disconnect
  }
}