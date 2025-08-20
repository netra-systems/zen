import { WebSocketMessage, AuthMessage, PingMessage, PongMessage } from '@/types/registry';
import { UnifiedWebSocketEvent } from '../types/unified-chat';
import { config } from '@/config';
import { logger } from '@/lib/logger';
import { logger as debugLogger } from '@/utils/debug-logger';

export type WebSocketStatus = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED';
export type WebSocketState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export interface WebSocketServiceError {
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
  onError?: (error: WebSocketServiceError) => void;
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

    private validateAgentMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    const agentTypes = ['agent_started', 'tool_executing', 'agent_thinking', 'partial_result', 'agent_completed'];
    if (!agentTypes.includes(obj.type)) return null;
    return obj.payload && typeof obj.payload === 'object' ? obj : null;
  }

  private validateThreadMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    const threadTypes = ['thread_created', 'thread_loading', 'thread_loaded', 'thread_renamed'];
    if (!threadTypes.includes(obj.type)) return null;
    return obj.payload && typeof obj.payload === 'object' ? obj : null;
  }

  private validateSystemMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    const systemTypes = ['auth', 'ping', 'pong'];
    if (!systemTypes.includes(obj.type)) return null;
    return obj;
  }

  private validateReportMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    const reportTypes = ['final_report', 'error'];
    if (!reportTypes.includes(obj.type)) return null;
    return obj.payload && typeof obj.payload === 'object' ? obj : null;
  }

  private handleUnknownMessageType(obj: any): WebSocketMessage | UnifiedWebSocketEvent {
    logger.debug('Unknown WebSocket message type', undefined, {
      component: 'WebSocketService',
      action: 'unknown_message_type',
      metadata: { type: obj.type }
    });
    return obj;
  }

  private validateWebSocketMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    if (!this.isBasicWebSocketMessage(obj)) return null;
    
    return this.validateAgentMessage(obj) ||
           this.validateThreadMessage(obj) ||
           this.validateSystemMessage(obj) ||
           this.validateReportMessage(obj) ||
           this.handleUnknownMessageType(obj);
  }

  private setupConnectionState(url: string, options: WebSocketOptions): boolean {
    this.url = url;
    this.options = options;
    if (this.state === 'connected' || this.state === 'connecting') return false;
    this.state = 'connecting';
    this.status = 'CONNECTING';
    this.onStatusChange?.(this.status);
    return true;
  }

  private handleConnectionOpen(url: string, options: WebSocketOptions): void {
    debugLogger.debug('[WebSocketService] Connection opened to:', url);
    this.state = 'connected';
    this.status = 'OPEN';
    this.onStatusChange?.(this.status);
    this.sendAuthToken();
    this.processQueuedMessages();
    this.startHeartbeatIfConfigured(options);
    options.onOpen?.();
  }

  private sendAuthToken(): void {
    // Token is already sent in query params during connection
    // No need to send again in auth message
    logger.debug('Token authentication already handled via query params');
  }

  private processQueuedMessages(): void {
    while (this.messageQueue.length > 0) {
      const msg = this.messageQueue.shift();
      this.send(msg);
    }
  }

  private startHeartbeatIfConfigured(options: WebSocketOptions): void {
    if (options.heartbeatInterval) {
      this.startHeartbeat(options.heartbeatInterval);
    }
  }

  private handleBinaryMessage(event: MessageEvent, options: WebSocketOptions): boolean {
    if (event.data instanceof ArrayBuffer) {
      options.onBinaryMessage?.(event.data);
      return true;
    }
    return false;
  }

  private processTextMessage(rawMessage: any, options: WebSocketOptions): void {
    const validatedMessage = this.validateWebSocketMessage(rawMessage);
    if (!validatedMessage) {
      this.handleInvalidMessage(rawMessage, options);
      return;
    }
    this.onMessage?.(validatedMessage);
    options.onMessage?.(validatedMessage);
  }

  private handleInvalidMessage(rawMessage: any, options: WebSocketOptions): void {
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
  }

  private handleMessageParseError(error: Error, options: WebSocketOptions): void {
    logger.error('Error parsing WebSocket message', error, {
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

  private handleConnectionClose(options: WebSocketOptions): void {
    this.state = 'disconnected';
    this.status = 'CLOSED';
    this.onStatusChange?.(this.status);
    this.stopHeartbeat();
    options.onClose?.();
    if (this.options.onReconnect) {
      this.scheduleReconnect();
    }
  }

  private handleConnectionError(error: Event, options: WebSocketOptions): void {
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
  }

  private handleConnectionFailure(error: Error, options: WebSocketOptions): void {
    logger.error('Failed to connect to WebSocket', error, {
      component: 'WebSocketService',
      action: 'connection_failed'
    });
    this.status = 'CLOSED';
    this.state = 'disconnected';
    this.onStatusChange?.(this.status);
    options.onError?.({
      code: 1000,
      message: error.message || 'Failed to connect to WebSocket',
      timestamp: Date.now(),
      type: 'connection',
      recoverable: true
    });
  }

  private checkRateLimit(): boolean {
    if (!this.options.rateLimit) return true;
    const now = Date.now();
    const windowStart = now - this.options.rateLimit.window;
    this.messageTimestamps = this.messageTimestamps.filter(ts => ts > windowStart);
    return this.messageTimestamps.length < this.options.rateLimit.messages;
  }

  private handleRateLimitExceeded(message: any): void {
    this.options.onRateLimit?.();
    this.messageQueue.push(message);
  }

  private recordMessageTimestamp(): void {
    if (this.options.rateLimit) {
      this.messageTimestamps.push(Date.now());
    }
  }

  private sendDirectly(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      this.messageQueue.push(message);
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
        debugLogger.debug('[WebSocketService] Connection opened to:', url);
        this.state = 'connected';
        this.status = 'OPEN';
        this.onStatusChange?.(this.status);
        
        // Token is already sent in query params during connection
        // No need to send again in auth message
        logger.debug('WebSocket connected, token authentication handled via query params');
        
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