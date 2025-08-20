/**
 * DRAFT: Enhanced WebSocket Provider fixes for DEV MODE connection issues.
 * 
 * Key fixes:
 * 1. Simplified service discovery with better error handling
 * 2. Improved CORS handling for localhost development
 * 3. Better JWT token management
 * 4. Simplified connection lifecycle
 * 5. Enhanced error recovery for DEV MODE
 * 
 * DO NOT DEPLOY TO PRODUCTION - THIS IS A DRAFT FOR REVIEW
 */

'use client';

import React, { 
  createContext, 
  useContext, 
  useEffect, 
  useState, 
  useCallback, 
  useRef,
  useMemo
} from 'react';
import { logger } from '@/lib/logger';
import { AuthContext } from '@/auth/context';

// Types (simplified for DEV)
export type WebSocketStatus = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTING' | 'DISCONNECTED' | 'RECONNECTING' | 'ERROR';

export interface WebSocketMessage {
  type: string;
  payload?: Record<string, any>;
  timestamp?: number;
}

export interface WebSocketError {
  code: string;
  message: string;
  timestamp: number;
  recoverable: boolean;
  help?: string;
}

export interface DevWebSocketConfig {
  version: string;
  features: Record<string, boolean>;
  endpoints: Record<string, string>;
  connection_limits: {
    max_connections_per_user: number;
    max_message_rate: number;
    max_message_size: number;
    heartbeat_interval: number;
  };
  dev_mode?: boolean;
  cors_origins?: string[];
}

export interface ConnectionStats {
  connected_at?: string;
  last_activity?: string;
  messages_sent: number;
  messages_received: number;
  errors_encountered: number;
  reconnections: number;
  connection_id?: string;
}

export interface WebSocketContextValue {
  status: WebSocketStatus;
  config: DevWebSocketConfig | null;
  connectionStats: ConnectionStats;
  lastError: WebSocketError | null;
  sendMessage: (message: WebSocketMessage) => Promise<boolean>;
  sendOptimisticMessage: (content: string, type?: string) => string;
  clearError: () => void;
  forceReconnect: () => void;
  isConnected: boolean;
  isReconnecting: boolean;
}

interface WebSocketProviderProps {
  children: React.ReactNode;
  autoConnect?: boolean;
  maxReconnectAttempts?: number;
  reconnectInterval?: number;
}

// Create context
const EnhancedWebSocketContext = createContext<WebSocketContextValue | null>(null);

export const useEnhancedWebSocket = (): WebSocketContextValue => {
  const context = useContext(EnhancedWebSocketContext);
  if (!context) {
    throw new Error('useEnhancedWebSocket must be used within an EnhancedWebSocketProvider');
  }
  return context;
};

// DEV MODE configuration
const DEV_MODE_CONFIG = {
  SERVICE_DISCOVERY_TIMEOUT: 5000, // 5 seconds
  CONNECTION_TIMEOUT: 10000, // 10 seconds
  MAX_QUEUE_SIZE: 100, // Smaller queue for DEV
  HEARTBEAT_TIMEOUT: 60000, // 1 minute
  RECONNECT_BASE_DELAY: 2000, // 2 seconds
  MAX_RECONNECT_DELAY: 15000, // 15 seconds max
};

export const EnhancedWebSocketProvider: React.FC<WebSocketProviderProps> = ({
  children,
  autoConnect = true,
  maxReconnectAttempts = 3, // Reduced for DEV
  reconnectInterval = 2000 // 2 seconds for DEV
}) => {
  const { token } = useContext(AuthContext) || { token: null };
  
  // State management (simplified)
  const [status, setStatus] = useState<WebSocketStatus>('DISCONNECTED');
  const [config, setConfig] = useState<DevWebSocketConfig | null>(null);
  const [connectionStats, setConnectionStats] = useState<ConnectionStats>({
    messages_sent: 0,
    messages_received: 0,
    errors_encountered: 0,
    reconnections: 0
  });
  const [lastError, setLastError] = useState<WebSocketError | null>(null);
  
  // Refs for stable references
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const messageQueueRef = useRef<WebSocketMessage[]>([]);
  const isConnectingRef = useRef(false);
  const connectionIdRef = useRef<string | null>(null);

  // DEV MODE: Simplified service discovery
  const fetchWebSocketConfig = useCallback(async (): Promise<DevWebSocketConfig | null> => {
    try {
      // DEV MODE: Use localhost with fallback
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      logger.info('[WebSocket] DEV MODE: Fetching service discovery from:', apiUrl);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), DEV_MODE_CONFIG.SERVICE_DISCOVERY_TIMEOUT);
      
      const response = await fetch(`${apiUrl}/ws/config`, {
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        }
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`Service discovery failed: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      const wsConfig = data.websocket_config;
      
      logger.info('[WebSocket] DEV MODE: Service discovery successful', {
        version: wsConfig.version,
        dev_mode: wsConfig.dev_mode,
        cors_origins: wsConfig.cors_origins?.length || 0
      });
      
      return wsConfig;
    } catch (error) {
      logger.error('[WebSocket] DEV MODE: Service discovery failed:', error);
      
      // DEV MODE: Return fallback config
      const fallbackConfig: DevWebSocketConfig = {
        version: '1.0-dev-fallback',
        features: {
          json_first: true,
          auth_required: true,
          heartbeat_supported: true,
          dev_mode: true
        },
        endpoints: {
          websocket: '/ws/enhanced'
        },
        connection_limits: {
          max_connections_per_user: 3,
          max_message_rate: 30,
          max_message_size: 8192,
          heartbeat_interval: 45000
        },
        dev_mode: true
      };
      
      logger.warn('[WebSocket] DEV MODE: Using fallback configuration');
      return fallbackConfig;
    }
  }, []);

  // DEV MODE: Simplified WebSocket URL builder
  const buildWebSocketUrl = useCallback((config: DevWebSocketConfig, token: string): string => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const wsUrl = apiUrl.replace(/^http/, 'ws');
    const endpoint = config.endpoints?.websocket || '/ws/enhanced';
    
    // DEV MODE: Always include token and origin for CORS
    const url = new URL(`${wsUrl}${endpoint}`);
    url.searchParams.set('token', token);
    
    // DEV MODE: Explicitly set origin for CORS
    const origin = window.location.origin;
    logger.debug('[WebSocket] DEV MODE: Using origin for CORS:', origin);
    
    return url.toString();
  }, []);

  // Clear timeouts
  const clearAllTimeouts = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  // Error handler
  const handleError = useCallback((error: WebSocketError | Error) => {
    const wsError: WebSocketError = error instanceof Error 
      ? {
          code: 'CONNECTION_ERROR',
          message: error.message,
          timestamp: Date.now(),
          recoverable: true
        }
      : error;
    
    setLastError(wsError);
    setConnectionStats(prev => ({
      ...prev,
      errors_encountered: prev.errors_encountered + 1
    }));
    
    logger.error('[WebSocket] DEV MODE: Error occurred:', wsError);
  }, []);

  // Send message function (simplified)
  const sendMessage = useCallback(async (message: WebSocketMessage): Promise<boolean> => {
    try {
      // Basic validation
      if (!message || typeof message !== 'object' || !message.type) {
        throw new Error('Invalid message format');
      }

      const messageWithTimestamp = {
        ...message,
        timestamp: message.timestamp || Date.now()
      };

      // Send or queue
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(messageWithTimestamp));
        
        setConnectionStats(prev => ({
          ...prev,
          messages_sent: prev.messages_sent + 1,
          last_activity: new Date().toISOString()
        }));
        
        logger.debug('[WebSocket] DEV MODE: Message sent:', messageWithTimestamp.type);
        return true;
      } else {
        // Queue for later (with size limit)
        if (messageQueueRef.current.length < DEV_MODE_CONFIG.MAX_QUEUE_SIZE) {
          messageQueueRef.current.push(messageWithTimestamp);
          logger.debug('[WebSocket] DEV MODE: Message queued:', messageWithTimestamp.type);
        } else {
          logger.warn('[WebSocket] DEV MODE: Message queue full, dropping message');
        }
        return false;
      }
    } catch (error) {
      logger.error('[WebSocket] DEV MODE: Send message error:', error);
      handleError(error instanceof Error ? error : new Error('Send failed'));
      return false;
    }
  }, [handleError]);

  // Send optimistic message
  const sendOptimisticMessage = useCallback((content: string, type: string = 'user_message'): string => {
    const correlationId = `dev_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const message: WebSocketMessage = {
      type,
      payload: {
        content,
        correlation_id: correlationId
      },
      timestamp: Date.now()
    };
    
    sendMessage(message);
    return correlationId;
  }, [sendMessage]);

  // Process queued messages
  const processQueuedMessages = useCallback(() => {
    const queue = messageQueueRef.current;
    messageQueueRef.current = [];
    
    queue.forEach(message => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(message));
      }
    });
    
    if (queue.length > 0) {
      logger.info(`[WebSocket] DEV MODE: Processed ${queue.length} queued messages`);
      setConnectionStats(prev => ({
        ...prev,
        messages_sent: prev.messages_sent + queue.length
      }));
    }
  }, []);

  // Connection establishment (simplified for DEV)
  const connect = useCallback(async (): Promise<void> => {
    if (!token) {
      throw new Error('No authentication token available');
    }

    if (isConnectingRef.current || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      isConnectingRef.current = true;
      setStatus('CONNECTING');
      clearAllTimeouts();

      logger.info('[WebSocket] DEV MODE: Starting connection process');

      // Step 1: Service discovery
      const wsConfig = await fetchWebSocketConfig();
      if (!wsConfig) {
        throw new Error('Service discovery failed');
      }
      setConfig(wsConfig);

      // Step 2: Build URL
      const wsUrl = buildWebSocketUrl(wsConfig, token);
      logger.info('[WebSocket] DEV MODE: Connecting to WebSocket');

      // Step 3: Create connection
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      // Connection timeout
      const connectionTimeout = setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          ws.close(1000, 'Connection timeout');
          handleError(new Error('Connection timeout in DEV mode'));
        }
      }, DEV_MODE_CONFIG.CONNECTION_TIMEOUT);

      ws.onopen = () => {
        clearTimeout(connectionTimeout);
        setStatus('CONNECTED');
        reconnectAttemptsRef.current = 0;
        isConnectingRef.current = false;

        setConnectionStats(prev => ({
          ...prev,
          connected_at: new Date().toISOString(),
          last_activity: new Date().toISOString()
        }));

        // Process queued messages
        processQueuedMessages();

        logger.info('[WebSocket] DEV MODE: Connection established successfully');
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          setConnectionStats(prev => ({
            ...prev,
            messages_received: prev.messages_received + 1,
            last_activity: new Date().toISOString()
          }));

          // Handle special messages
          if (message.type === 'connection_established') {
            connectionIdRef.current = message.payload?.connection_id;
            setConnectionStats(prev => ({
              ...prev,
              connection_id: message.payload?.connection_id
            }));
            logger.info('[WebSocket] DEV MODE: Connection ID received:', message.payload?.connection_id);
          } else if (message.type === 'error') {
            handleError({
              code: message.payload?.code || 'SERVER_ERROR',
              message: message.payload?.error || 'Server error',
              timestamp: message.payload?.timestamp || Date.now(),
              recoverable: message.payload?.recoverable ?? true,
              help: message.payload?.help
            });
          } else if (message.type === 'pong' || message.type === 'server_heartbeat') {
            logger.debug('[WebSocket] DEV MODE: Heartbeat received');
          } else {
            logger.debug('[WebSocket] DEV MODE: Message received:', message.type);
          }
        } catch (error) {
          logger.error('[WebSocket] DEV MODE: Message parse error:', error);
        }
      };

      ws.onclose = (event) => {
        clearTimeout(connectionTimeout);
        isConnectingRef.current = false;

        const wasConnected = status === 'CONNECTED';
        setStatus('DISCONNECTED');

        logger.info(`[WebSocket] DEV MODE: Connection closed: ${event.code} - ${event.reason}`);

        // Attempt reconnection for unexpected closures
        if (
          wasConnected && 
          event.code !== 1000 && 
          reconnectAttemptsRef.current < maxReconnectAttempts &&
          autoConnect
        ) {
          attemptReconnection();
        }
      };

      ws.onerror = (event) => {
        clearTimeout(connectionTimeout);
        isConnectingRef.current = false;
        logger.error('[WebSocket] DEV MODE: Connection error');
        handleError(new Error('WebSocket connection error in DEV mode'));
      };

    } catch (error) {
      isConnectingRef.current = false;
      setStatus('ERROR');
      handleError(error instanceof Error ? error : new Error('Connection failed'));
      throw error;
    }
  }, [token, fetchWebSocketConfig, buildWebSocketUrl, processQueuedMessages, handleError, clearAllTimeouts, status, maxReconnectAttempts, autoConnect]);

  // Reconnection logic (simplified for DEV)
  const attemptReconnection = useCallback(() => {
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      logger.error('[WebSocket] DEV MODE: Max reconnection attempts reached');
      setStatus('ERROR');
      setLastError({
        code: 'MAX_RECONNECT_ATTEMPTS',
        message: `Failed to reconnect after ${maxReconnectAttempts} attempts`,
        timestamp: Date.now(),
        recoverable: false
      });
      return;
    }

    reconnectAttemptsRef.current++;
    setStatus('RECONNECTING');
    
    setConnectionStats(prev => ({
      ...prev,
      reconnections: prev.reconnections + 1
    }));

    // Simple exponential backoff for DEV
    const delay = Math.min(
      DEV_MODE_CONFIG.RECONNECT_BASE_DELAY * Math.pow(2, reconnectAttemptsRef.current - 1),
      DEV_MODE_CONFIG.MAX_RECONNECT_DELAY
    );
    
    logger.info(`[WebSocket] DEV MODE: Attempting reconnection ${reconnectAttemptsRef.current}/${maxReconnectAttempts} in ${delay}ms`);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      connect().catch(error => {
        logger.error('[WebSocket] DEV MODE: Reconnection failed:', error);
      });
    }, delay);
  }, [maxReconnectAttempts, connect]);

  // Disconnect
  const disconnect = useCallback(() => {
    clearAllTimeouts();
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'User initiated disconnect');
      wsRef.current = null;
    }
    
    setStatus('DISCONNECTED');
    connectionIdRef.current = null;
    messageQueueRef.current = []; // Clear queue
    
    logger.info('[WebSocket] DEV MODE: Disconnected and cleaned up');
  }, [clearAllTimeouts]);

  // Force reconnect
  const forceReconnect = useCallback(() => {
    logger.info('[WebSocket] DEV MODE: Force reconnect initiated');
    reconnectAttemptsRef.current = 0;
    disconnect();
    setTimeout(() => {
      connect().catch(error => {
        logger.error('[WebSocket] DEV MODE: Force reconnect failed:', error);
      });
    }, 1000);
  }, [disconnect, connect]);

  // Clear error
  const clearError = useCallback(() => {
    setLastError(null);
  }, []);

  // Auto-connect effect (simplified for DEV)
  useEffect(() => {
    if (token && autoConnect && status === 'DISCONNECTED' && !isConnectingRef.current) {
      logger.info('[WebSocket] DEV MODE: Auto-connect triggered');
      connect().catch(error => {
        logger.error('[WebSocket] DEV MODE: Auto-connect failed:', error);
      });
    }
    
    return () => {
      disconnect();
    };
  }, [token, autoConnect]); // Simplified dependencies

  // Context value
  const contextValue = useMemo<WebSocketContextValue>(() => ({
    status,
    config,
    connectionStats,
    lastError,
    sendMessage,
    sendOptimisticMessage,
    clearError,
    forceReconnect,
    isConnected: status === 'CONNECTED',
    isReconnecting: status === 'RECONNECTING'
  }), [
    status,
    config,
    connectionStats,
    lastError,
    sendMessage,
    sendOptimisticMessage,
    clearError,
    forceReconnect
  ]);

  return (
    <EnhancedWebSocketContext.Provider value={contextValue}>
      {children}
    </EnhancedWebSocketContext.Provider>
  );
};

export default EnhancedWebSocketProvider;