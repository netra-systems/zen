'use client';

/**
 * Enhanced WebSocket Provider with comprehensive features:
 * - Connection established on app state load (BEFORE first message)
 * - Persistent connection resilient to component re-renders
 * - Proper JWT authentication with service discovery
 * - JSON-first communication with validation
 * - Robust reconnection logic with exponential backoff
 * - Comprehensive error handling and recovery
 * - Connection status indicators and metrics
 * - Message queuing during disconnections
 */

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
import type { WebSocketMessage } from '@/types/domains/websocket';
import { websocketTicketService } from '@/services/websocketTicketService';
import type { WebSocketTicket } from '@/types/websocket-ticket';

// Types
export type WebSocketStatus = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTING' | 'DISCONNECTED' | 'RECONNECTING' | 'ERROR';

export interface WebSocketError {
  code: string;
  message: string;
  timestamp: number;
  recoverable: boolean;
  help?: string;
}

export interface WebSocketConfig {
  version: string;
  features: Record<string, boolean>;
  endpoints: Record<string, string>;
  connection_limits: {
    max_connections_per_user: number;
    max_message_rate: number;
    max_message_size: number;
    heartbeat_interval: number;
  };
  auth: {
    methods: string[];
    token_validation: string;
    session_handling: string;
  };
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
  config: WebSocketConfig | null;
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

export const EnhancedWebSocketProvider: React.FC<WebSocketProviderProps> = ({
  children,
  autoConnect = true,
  maxReconnectAttempts = 5,
  reconnectInterval = 1000
}) => {
  const { token } = useContext(AuthContext) || { token: null };
  
  // State management
  const [status, setStatus] = useState<WebSocketStatus>('DISCONNECTED');
  const [config, setConfig] = useState<WebSocketConfig | null>(null);
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
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const messageQueueRef = useRef<WebSocketMessage[]>([]);
  const isConnectingRef = useRef(false);
  const connectionIdRef = useRef<string | null>(null);
  const memoryCleanupIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // Message rate limiting
  const messageTimestampsRef = useRef<number[]>([]);
  const rateLimitWindowMs = 60000; // 1 minute
  
  // Memory management constants
  const MAX_QUEUE_SIZE = 1000; // Prevent unbounded memory growth
  const MAX_MESSAGE_AGE_MS = 300000; // 5 minutes
  const CLEANUP_INTERVAL_MS = 60000; // 1 minute

  // Service discovery: Fetch WebSocket configuration
  const fetchWebSocketConfig = useCallback(async (): Promise<WebSocketConfig | null> => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/ws/config`);
      
      if (!response.ok) {
        throw new Error(`Service discovery failed: ${response.status}`);
      }
      
      const data = await response.json();
      const wsConfig = data.websocket_config;
      
      logger.info('[WebSocket] Service discovery successful', {
        version: wsConfig.version,
        features: Object.keys(wsConfig.features || {}),
        endpoints: Object.keys(wsConfig.endpoints || {})
      });
      
      return wsConfig;
    } catch (error) {
      logger.error('[WebSocket] Service discovery failed:', error);
      return null;
    }
  }, []);

  // Rate limiting check
  const checkRateLimit = useCallback((): boolean => {
    if (!config?.connection_limits?.max_message_rate) {
      return true; // No rate limiting configured
    }

    const now = Date.now();
    const windowStart = now - rateLimitWindowMs;
    
    // Remove old timestamps
    messageTimestampsRef.current = messageTimestampsRef.current.filter(
      timestamp => timestamp > windowStart
    );
    
    return messageTimestampsRef.current.length < config.connection_limits.max_message_rate;
  }, [config]);

  // Record message for rate limiting
  const recordMessage = useCallback(() => {
    messageTimestampsRef.current.push(Date.now());
  }, []);

  // Memory cleanup function to prevent memory leaks
  const cleanupMessageMemory = useCallback(() => {
    const now = Date.now();
    
    // Clean up old message timestamps for rate limiting
    messageTimestampsRef.current = messageTimestampsRef.current.filter(
      timestamp => now - timestamp < rateLimitWindowMs
    );
    
    // Clean up old queued messages to prevent memory leaks
    messageQueueRef.current = messageQueueRef.current.filter(
      message => {
        const messageAge = now - (message.timestamp || 0);
        return messageAge < MAX_MESSAGE_AGE_MS;
      }
    );
    
    // Enforce maximum queue size to prevent unbounded growth
    if (messageQueueRef.current.length > MAX_QUEUE_SIZE) {
      logger.warn(`[WebSocket] Message queue size exceeded ${MAX_QUEUE_SIZE}, dropping oldest messages`);
      messageQueueRef.current = messageQueueRef.current.slice(-MAX_QUEUE_SIZE);
    }
    
    // Log memory cleanup stats
    const queueSize = messageQueueRef.current.length;
    const timestampCount = messageTimestampsRef.current.length;
    
    if (queueSize > 100 || timestampCount > 100) {
      logger.debug(`[WebSocket] Memory cleanup - Queue: ${queueSize}, Timestamps: ${timestampCount}`);
    }
  }, [rateLimitWindowMs]);

  // Start memory cleanup interval
  const startMemoryCleanup = useCallback(() => {
    if (memoryCleanupIntervalRef.current) {
      clearInterval(memoryCleanupIntervalRef.current);
    }
    
    memoryCleanupIntervalRef.current = setInterval(cleanupMessageMemory, CLEANUP_INTERVAL_MS);
    logger.debug('[WebSocket] Memory cleanup interval started');
  }, [cleanupMessageMemory]);

  // Stop memory cleanup interval
  const stopMemoryCleanup = useCallback(() => {
    if (memoryCleanupIntervalRef.current) {
      clearInterval(memoryCleanupIntervalRef.current);
      memoryCleanupIntervalRef.current = null;
      logger.debug('[WebSocket] Memory cleanup interval stopped');
    }
  }, []);

  // WebSocket URL builder with ticket authentication
  const buildWebSocketUrl = useCallback((config: WebSocketConfig, ticket?: WebSocketTicket): string => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const wsUrl = apiUrl.replace(/^http/, 'ws');
    const endpoint = config.endpoints?.websocket || '/ws'; // Use unified endpoint
    
    // If ticket is provided, use it in URL parameters (preferred method)
    if (ticket?.ticket) {
      const separator = endpoint.includes('?') ? '&' : '?';
      return `${wsUrl}${endpoint}${separator}ticket=${ticket.ticket}`;
    }
    
    // Fallback to base URL without ticket
    return `${wsUrl}${endpoint}`;
  }, []);

  // Clear reconnection timeout
  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  // Clear heartbeat interval
  const clearHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  // Start heartbeat
  const startHeartbeat = useCallback((interval: number) => {
    clearHeartbeat();
    
    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const pingMessage: WebSocketMessage = {
          type: 'ping',
          timestamp: Date.now()
        };
        wsRef.current.send(JSON.stringify(pingMessage));
        logger.debug('[WebSocket] Heartbeat ping sent');
      }
    }, interval);
  }, [clearHeartbeat]);

  // Process queued messages
  const processQueuedMessages = useCallback(() => {
    const queue = messageQueueRef.current;
    messageQueueRef.current = [];
    
    queue.forEach(message => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(message));
        recordMessage();
      }
    });
    
    if (queue.length > 0) {
      logger.info(`[WebSocket] Processed ${queue.length} queued messages`);
    }
  }, [recordMessage]);

  // Send message function
  const sendMessage = useCallback(async (message: WebSocketMessage): Promise<boolean> => {
    try {
      // Validate message structure (JSON-first)
      if (!message || typeof message !== 'object') {
        throw new Error('Message must be a JSON object');
      }
      
      if (!message.type || typeof message.type !== 'string' || !message.type.trim()) {
        throw new Error('Message must have a valid type field');
      }

      // Add timestamp if not present for memory management
      const messageWithTimestamp = {
        ...message,
        timestamp: message.timestamp || Date.now()
      };

      // Check rate limiting
      if (!checkRateLimit()) {
        logger.warn('[WebSocket] Rate limit exceeded, queuing message');
        messageQueueRef.current.push(messageWithTimestamp);
        return false;
      }

      // Check message size
      const messageStr = JSON.stringify(messageWithTimestamp);
      const maxSize = config?.connection_limits?.max_message_size || 10240;
      if (messageStr.length > maxSize) {
        throw new Error(`Message too large: ${messageStr.length} bytes > ${maxSize} bytes`);
      }

      // Send message or queue if not connected
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(messageStr);
        recordMessage();
        
        setConnectionStats(prev => ({
          ...prev,
          messages_sent: prev.messages_sent + 1,
          last_activity: new Date().toISOString()
        }));
        
        logger.debug('[WebSocket] Message sent:', messageWithTimestamp.type);
        return true;
      } else {
        // Queue message for later with memory limit check
        messageQueueRef.current.push(messageWithTimestamp);
        
        // Trigger immediate cleanup if queue is getting too large
        if (messageQueueRef.current.length > MAX_QUEUE_SIZE * 0.8) {
          cleanupMessageMemory();
        }
        
        logger.debug('[WebSocket] Message queued (not connected):', messageWithTimestamp.type);
        return false;
      }
    } catch (error) {
      logger.error('[WebSocket] Send message error:', error);
      setLastError({
        code: 'SEND_MESSAGE_ERROR',
        message: error instanceof Error ? error.message : 'Failed to send message',
        timestamp: Date.now(),
        recoverable: true
      });
      return false;
    }
  }, [checkRateLimit, recordMessage, config, cleanupMessageMemory]);

  // Send optimistic message
  const sendOptimisticMessage = useCallback((content: string, type: string = 'user_message'): string => {
    const correlationId = `opt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
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
    
    logger.error('[WebSocket] Error occurred:', wsError);
  }, []);

  // Connection establishment
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
      clearReconnectTimeout();

      // Step 1: Service discovery
      logger.info('[WebSocket] Starting connection with service discovery');
      const wsConfig = await fetchWebSocketConfig();
      if (!wsConfig) {
        throw new Error('Failed to discover WebSocket configuration');
      }
      setConfig(wsConfig);

      // Step 2: Acquire authentication ticket for secure WebSocket connection
      logger.info('[WebSocket] Acquiring authentication ticket...');
      const ticketResult = await websocketTicketService.acquireTicket(300); // 5 minutes TTL
      
      if (!ticketResult.success || !ticketResult.ticket) {
        // If ticket acquisition fails, log detailed error and attempt fallback
        const errorMsg = ticketResult.error || 'Failed to acquire WebSocket ticket';
        logger.error('[WebSocket] Ticket acquisition failed:', errorMsg);
        
        // For Issue #1295, we prioritize ticket auth but provide informative error
        throw new Error(`WebSocket ticket authentication failed: ${errorMsg}`);
      }
      
      logger.info('[WebSocket] Ticket acquired successfully, establishing connection');

      // Step 3: Build WebSocket URL with secure ticket authentication
      const wsUrl = buildWebSocketUrl(wsConfig, ticketResult.ticket);
      logger.info('[WebSocket] Connecting with ticket authentication');

      // Step 4: Create WebSocket connection (no subprotocols needed with ticket auth)
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      // Connection timeout
      const connectionTimeout = setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          ws.close(1000, 'Connection timeout');
          handleError(new Error('Connection timeout'));
        }
      }, 10000);

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

        // Start heartbeat
        if (wsConfig.connection_limits?.heartbeat_interval) {
          startHeartbeat(wsConfig.connection_limits.heartbeat_interval);
        }

        // Start memory cleanup interval
        startMemoryCleanup();

        // Process queued messages
        processQueuedMessages();

        logger.info('[WebSocket] Connection established successfully with memory management');
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          // Update connection stats
          setConnectionStats(prev => ({
            ...prev,
            messages_received: prev.messages_received + 1,
            last_activity: new Date().toISOString()
          }));

          // Handle special message types
          if (message.type === 'connection_established') {
            connectionIdRef.current = message.payload?.connection_id;
            setConnectionStats(prev => ({
              ...prev,
              connection_id: message.payload?.connection_id
            }));
            logger.info('[WebSocket] Connection ID:', message.payload?.connection_id);
          } else if (message.type === 'error') {
            handleError({
              code: message.payload?.code || 'SERVER_ERROR',
              message: message.payload?.error || 'Server error',
              timestamp: message.payload?.timestamp || Date.now(),
              recoverable: message.payload?.recoverable ?? true,
              help: message.payload?.help
            });
          } else if (message.type === 'pong') {
            logger.debug('[WebSocket] Received pong response');
          } else {
            // Custom message handling can be added here
            logger.debug('[WebSocket] Message received:', message.type);
          }
        } catch (error) {
          logger.error('[WebSocket] Message parse error:', error);
          handleError(new Error('Failed to parse server message'));
        }
      };

      ws.onclose = (event) => {
        clearTimeout(connectionTimeout);
        clearHeartbeat();
        isConnectingRef.current = false;

        const wasConnected = status === 'CONNECTED';
        setStatus('DISCONNECTED');

        logger.info(`[WebSocket] Connection closed: ${event.code} - ${event.reason}`);

        // Handle authentication errors specifically
        if (event.code === 1008) {
          const isTicketError = event.reason && (
            event.reason.includes('ticket') ||
            event.reason.includes('authentication') ||
            event.reason.includes('unauthorized')
          );
          
          handleError({
            code: isTicketError ? 'TICKET_AUTHENTICATION_FAILED' : 'AUTHENTICATION_FAILED',
            message: isTicketError 
              ? 'Ticket authentication failed: Invalid, expired, or consumed ticket'
              : 'Authentication failed: Unable to authenticate connection',
            timestamp: Date.now(),
            recoverable: true, // Ticket errors are recoverable with new ticket
            help: isTicketError 
              ? 'A new authentication ticket will be acquired automatically'
              : 'Please check your login status and try again'
          });
          
          // Clear ticket cache on authentication failure to force refresh
          if (isTicketError) {
            websocketTicketService.clearTicketCache();
          }
        }

        // Attempt reconnection for abnormal closures (excluding auth errors)
        if (
          wasConnected && 
          event.code !== 1000 && 
          event.code !== 1008 && // Don't retry auth failures
          reconnectAttemptsRef.current < maxReconnectAttempts &&
          autoConnect
        ) {
          attemptReconnection();
        }
      };

      ws.onerror = (event) => {
        clearTimeout(connectionTimeout);
        isConnectingRef.current = false;
        
        // Distinguish between connection and authentication errors
        const errorMessage = token 
          ? 'WebSocket connection error - check network and authentication'
          : 'WebSocket connection error - no authentication token';
          
        handleError({
          code: token ? 'CONNECTION_ERROR' : 'NO_AUTH_TOKEN',
          message: errorMessage,
          timestamp: Date.now(),
          recoverable: !!token,
          help: token 
            ? 'Connection will be retried automatically with a new ticket'
            : 'Please log in to establish a secure connection'
        });
        
        // Clear ticket cache on connection error to force fresh ticket on retry
        if (token) {
          websocketTicketService.clearTicketCache();
        }
      };

    } catch (error) {
      isConnectingRef.current = false;
      setStatus('ERROR');
      handleError(error instanceof Error ? error : new Error('Connection failed'));
      throw error;
    }
  }, [token, fetchWebSocketConfig, buildWebSocketUrl, startHeartbeat, processQueuedMessages, handleError, clearReconnectTimeout, clearHeartbeat, status, maxReconnectAttempts, autoConnect]);

  // Reconnection logic with proper exponential backoff
  const attemptReconnection = useCallback(() => {
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      logger.error('[WebSocket] Max reconnection attempts reached');
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

    // Exponential backoff with jitter to prevent thundering herd
    const baseDelay = reconnectInterval;
    const exponentialDelay = baseDelay * Math.pow(2, reconnectAttemptsRef.current - 1);
    const jitter = Math.random() * 1000; // Add up to 1 second of jitter
    const delay = Math.min(exponentialDelay + jitter, 30000); // Cap at 30 seconds
    
    logger.info(`[WebSocket] Attempting reconnection ${reconnectAttemptsRef.current}/${maxReconnectAttempts} in ${Math.round(delay)}ms (exponential backoff)`);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      connect().catch(error => {
        logger.error('[WebSocket] Reconnection failed:', error);
        // If this reconnection fails, attemptReconnection will be called again from onclose
      });
    }, delay);
  }, [maxReconnectAttempts, reconnectInterval, connect]);

  // Disconnect
  const disconnect = useCallback(() => {
    clearReconnectTimeout();
    clearHeartbeat();
    stopMemoryCleanup();
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'User initiated disconnect');
      wsRef.current = null;
    }
    
    setStatus('DISCONNECTED');
    connectionIdRef.current = null;
    
    // Final memory cleanup on disconnect
    cleanupMessageMemory();
    
    logger.info('[WebSocket] Disconnected and cleaned up');
  }, [clearReconnectTimeout, clearHeartbeat, stopMemoryCleanup, cleanupMessageMemory]);

  // Force reconnect
  const forceReconnect = useCallback(() => {
    logger.info('[WebSocket] Force reconnect initiated');
    reconnectAttemptsRef.current = 0;
    disconnect();
    setTimeout(() => {
      connect().catch(error => {
        logger.error('[WebSocket] Force reconnect failed:', error);
      });
    }, 1000);
  }, [disconnect, connect]);

  // Clear error
  const clearError = useCallback(() => {
    setLastError(null);
  }, []);

  // Auto-connect effect
  useEffect(() => {
    if (token && autoConnect && status === 'DISCONNECTED') {
      connect().catch(error => {
        logger.error('[WebSocket] Auto-connect failed:', error);
      });
    }
    
    return () => {
      disconnect();
    };
  }, [token, autoConnect, connect, disconnect, status]);

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