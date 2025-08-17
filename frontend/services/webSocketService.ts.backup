import { WebSocketMessage, AuthMessage, PingMessage, PongMessage } from '../types/backend_schema_auto_generated';
import { UnifiedWebSocketEvent } from '../types/unified-chat';
import { config } from '@/config';
import { logger } from '@/lib/logger';

export type WebSocketStatus = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED';
export type WebSocketState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export interface WebSocketError {
  code: number;
  message: string;
  timestamp: number;
  type: 'connection' | 'parse' | 'auth' | 'timeout' | 'rate_limit' | 'unknown';
  recoverable: boolean;
}

interface RateLimitConfig {
  messages: number;
  window: number;
}

interface WebSocketOptions {
  onOpen?: () => void;
  onMessage?: (message: WebSocketMessage | UnifiedWebSocketEvent) => void;
  onError?: (error: WebSocketError) => void;
  onClose?: () => void;
  onReconnect?: () => void;
  onBinaryMessage?: (data: ArrayBuffer) => void;
  onRateLimit?: () => void;
  heartbeatInterval?: number;
  rateLimit?: RateLimitConfig;
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private status: WebSocketStatus = 'CLOSED';
  private state: WebSocketState = 'disconnected';
  private options: WebSocketOptions = {};
  private messageQueue: (WebSocketMessage | UnifiedWebSocketEvent | AuthMessage | PingMessage | PongMessage)[] = [];
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private url: string = '';
  private messageTimestamps: number[] = [];

  public onStatusChange: ((status: WebSocketStatus) => void) | null = null;
  public onMessage: ((message: WebSocketMessage) => void) | null = null;

  // Type guards and validation
  private isBasicWebSocketMessage(obj: any): obj is WebSocketMessage {
    return obj && 
           typeof obj === 'object' && 
           typeof obj.type === 'string' && 
           typeof obj.payload === 'object';
  }

  private isUnifiedWebSocketEvent(obj: any): obj is UnifiedWebSocketEvent {
    const unifiedEventTypes = [
      'agent_started', 'tool_executing', 'agent_thinking', 'partial_result',
      'agent_completed', 'final_report', 'error', 'thread_created',
      'thread_loading', 'thread_loaded', 'thread_renamed', 'step_created'
    ];
    return this.isBasicWebSocketMessage(obj) && 
           unifiedEventTypes.includes(obj.type);
  }

  private validateWebSocketMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    if (!this.isBasicWebSocketMessage(obj)) {
      return null;
    }

    // Additional validation based on message type
    switch (obj.type) {
      case 'agent_started':
        // Basic structure validation - don't require all fields since we handle missing ones
        return obj.payload && typeof obj.payload === 'object' ? obj : null;
      
      case 'tool_executing':
        return obj.payload && typeof obj.payload === 'object' ? obj : null;
      
      case 'agent_thinking':
        return obj.payload && typeof obj.payload === 'object' ? obj : null;
      
      case 'partial_result':
        return obj.payload && typeof obj.payload === 'object' ? obj : null;
      
      case 'agent_completed':
        return obj.payload && typeof obj.payload === 'object' ? obj : null;
      
      case 'final_report':
        return obj.payload && typeof obj.payload === 'object' ? obj : null;
      
      case 'error':
        return obj.payload && typeof obj.payload === 'object' ? obj : null;
      
      case 'thread_created':
      case 'thread_loading':
      case 'thread_loaded':
      case 'thread_renamed':
        return obj.payload && typeof obj.payload === 'object' ? obj : null;
      
      case 'auth':
      case 'ping':
      case 'pong':
        return obj; // These have simpler structures
      
      default:
        // Allow unknown message types but log them
        logger.debug('Unknown WebSocket message type', undefined, {
          component: 'WebSocketService',
          action: 'unknown_message_type',
          metadata: { type: obj.type }
        });
        return obj; // Pass through unknown types
    }
  }

  public connect(url: string, options: WebSocketOptions = {}) {
    this.url = url;
    this.options = options;
    
    if (this.state === 'connected' || this.state === 'connecting') {
      return;
    }

    this.state = 'connecting';
    this.status = 'CONNECTING';
    this.onStatusChange?.(this.status);

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log('[WebSocketService] Connection opened to:', url);
        this.state = 'connected';
        this.status = 'OPEN';
        this.onStatusChange?.(this.status);
        
        // Send auth token
        const token = localStorage.getItem('authToken');
        if (token) {
          this.send({ type: 'auth', token } as AuthMessage);
        }
        
        // Send queued messages
        while (this.messageQueue.length > 0) {
          const msg = this.messageQueue.shift();
          this.send(msg);
        }
        
        // Start heartbeat if configured
        if (options.heartbeatInterval) {
          this.startHeartbeat(options.heartbeatInterval);
        }
        
        options.onOpen?.();
      };

      this.ws.onmessage = (event) => {
        // Handle binary data
        if (event.data instanceof ArrayBuffer) {
          options.onBinaryMessage?.(event.data);
          return;
        }
        
        try {
          const rawMessage = JSON.parse(event.data);
          
          // Validate message structure
          const validatedMessage = this.validateWebSocketMessage(rawMessage);
          if (!validatedMessage) {
            logger.warn('Invalid WebSocket message received', undefined, {
              component: 'WebSocketService',
              action: 'invalid_message',
              metadata: { message: rawMessage }
            });
            options.onError?.({
              code: 1003,
              message: 'Invalid message structure',
              timestamp: Date.now(),
              type: 'parse',
              recoverable: true
            });
            return;
          }
          
          this.onMessage?.(validatedMessage);
          options.onMessage?.(validatedMessage);
        } catch (error) {
          logger.error('Error parsing WebSocket message', error as Error, {
            component: 'WebSocketService',
            action: 'parse_message_error'
          });
          options.onError?.({
            code: 1003,
            message: 'Failed to parse message',
            timestamp: Date.now(),
            type: 'parse',
            recoverable: true
          });
        }
      };

      this.ws.onclose = () => {
        this.state = 'disconnected';
        this.status = 'CLOSED';
        this.onStatusChange?.(this.status);
        this.stopHeartbeat();
        options.onClose?.();
        
        // Attempt reconnection
        if (this.options.onReconnect) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        logger.error('WebSocket error occurred', undefined, {
          component: 'WebSocketService',
          action: 'websocket_error',
          metadata: { error }
        });
        this.status = 'CLOSED';
        this.state = 'disconnected';
        this.onStatusChange?.(this.status);
        options.onError?.({
          code: 1006,
          message: 'WebSocket connection error',
          timestamp: Date.now(),
          type: 'connection',
          recoverable: true
        });
      };
    } catch (error) {
      logger.error('Failed to connect to WebSocket', error as Error, {
        component: 'WebSocketService',
        action: 'connection_failed'
      });
      this.status = 'CLOSED';
      this.state = 'disconnected';
      this.onStatusChange?.(this.status);
      options.onError?.({
        code: 1000,
        message: (error as Error).message || 'Failed to connect to WebSocket',
        timestamp: Date.now(),
        type: 'connection',
        recoverable: true
      });
    }
  }
  
  private startHeartbeat(interval: number) {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping', timestamp: Date.now() } as PingMessage);
      }
    }, interval);
  }
  
  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
  
  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    
    this.state = 'reconnecting';
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.options.onReconnect?.();
      this.connect(this.url, this.options);
    }, 5000);
  }

  public send(message: WebSocketMessage | UnifiedWebSocketEvent | AuthMessage | PingMessage | PongMessage) {
    // Check rate limit if configured
    if (this.options.rateLimit) {
      const now = Date.now();
      const windowStart = now - this.options.rateLimit.window;
      
      // Remove timestamps outside the window
      this.messageTimestamps = this.messageTimestamps.filter(ts => ts > windowStart);
      
      // Check if we've exceeded the rate limit
      if (this.messageTimestamps.length >= this.options.rateLimit.messages) {
        this.options.onRateLimit?.();
        // Queue the message instead of dropping it
        this.messageQueue.push(message);
        return;
      }
      
      // Add current timestamp
      this.messageTimestamps.push(now);
    }
    
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      // Queue message for sending when connected
      this.messageQueue.push(message);
    }
  }

  public sendMessage(message: WebSocketMessage) {
    this.send(message);
  }
  
  public getState(): WebSocketState {
    return this.state;
  }

  public disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    this.stopHeartbeat();
    
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      this.ws.close();
    }
    
    this.state = 'disconnected';
    this.messageQueue = [];
  }
}

export const webSocketService = new WebSocketService();