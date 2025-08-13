import { useState, useEffect, useCallback, useRef } from 'react'

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
      const host = process.env.NEXT_PUBLIC_API_URL || window.location.host
      const wsUrl = `${protocol}//${host}/api/demo/ws`

      // Create new WebSocket connection
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('Demo WebSocket connected')
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
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onerror = (event) => {
        console.error('Demo WebSocket error:', event)
        setError(new Error('WebSocket connection error'))
        onError?.(event)
      }

      ws.onclose = () => {
        console.log('Demo WebSocket disconnected')
        setIsConnected(false)
        wsRef.current = null
        onDisconnect?.()

        // Auto-reconnect if enabled
        if (autoReconnect && reconnectAttemptsRef.current < 5) {
          reconnectAttemptsRef.current++
          const delay = reconnectInterval * Math.pow(2, reconnectAttemptsRef.current - 1)
          console.log(`Attempting to reconnect in ${delay}ms...`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, delay)
        }
      }
    } catch (err) {
      console.error('Failed to establish WebSocket connection:', err)
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
      console.error('WebSocket is not connected')
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