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
  token?: string;
  refreshToken?: () => Promise<string | null>;
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
  private currentToken: string | null = null;
  private tokenRefreshTimer: NodeJS.Timeout | null = null;

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
    // Token authentication is handled securely via subprotocol during connection
    // No additional auth message needed - security vulnerability prevented
    logger.debug('Token authentication handled via secure subprotocol method');
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
    this.currentToken = options.token || null;
    
    if (this.state === 'connected' || this.state === 'connecting') {
      return;
    }

    this.state = 'connecting';
    this.status = 'CONNECTING';
    this.onStatusChange?.(this.status);

    try {
      this.ws = this.createSecureWebSocket(url, options);

      this.ws.onopen = () => {
        debugLogger.debug('[WebSocketService] Connection opened to:', url);
        this.state = 'connected';
        this.status = 'OPEN';
        this.onStatusChange?.(this.status);
        
        // Token authentication handled securely via subprotocol
        // No additional auth message needed
        logger.debug('WebSocket connected, secure authentication completed');
        
        // Send queued messages
        while (this.messageQueue.length > 0) {
          const msg = this.messageQueue.shift();
          this.send(msg);
        }
        
        // Start heartbeat if configured
        if (options.heartbeatInterval) {
          this.startHeartbeat(options.heartbeatInterval);
        }

        // Setup token refresh
        this.setupTokenRefresh();
        
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

      this.ws.onclose = (event) => {
        this.state = 'disconnected';
        this.status = 'CLOSED';
        this.onStatusChange?.(this.status);
        this.stopHeartbeat();
        
        // Handle authentication errors specifically
        if (event.code === 1008) {
          logger.error('WebSocket authentication failed', undefined, {
            component: 'WebSocketService',
            action: 'auth_rejection',
            metadata: { code: event.code, reason: event.reason }
          });
          
          this.handleAuthError({
            code: event.code,
            reason: event.reason || 'Authentication failed'
          });
        }
        
        options.onClose?.();
        
        // Only attempt reconnection for non-auth errors
        if (this.options.onReconnect && event.code !== 1008) {
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
        
        // Determine error type based on readyState and context
        const errorType = this.currentToken ? 'auth' : 'connection';
        
        options.onError?.({
          code: 1006,
          message: errorType === 'auth' ? 'Authentication error' : 'WebSocket connection error',
          timestamp: Date.now(),
          type: errorType,
          recoverable: errorType !== 'auth'
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
    
    if (this.tokenRefreshTimer) {
      clearTimeout(this.tokenRefreshTimer);
      this.tokenRefreshTimer = null;
    }
    
    this.stopHeartbeat();
    
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      this.ws.close();
    }
    
    this.state = 'disconnected';
    this.messageQueue = [];
    this.currentToken = null;
  }

  /**
   * Creates a secure WebSocket connection using proper authentication methods.
   * Uses subprotocol for JWT authentication (browser-compatible method)
   */
  private createSecureWebSocket(url: string, options: WebSocketOptions): WebSocket {
    const token = options.token;
    
    if (!token) {
      logger.debug('Creating WebSocket without authentication');
      return new WebSocket(url);
    }

    // Ensure the token has Bearer prefix for secure subprotocol auth
    const bearerToken = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
    
    // Use subprotocol for secure authentication (browser-compatible)
    // Note: Browser WebSocket API doesn't support custom headers directly
    const protocols = [`jwt.${bearerToken}`];
    logger.debug('Creating secure WebSocket with subprotocol authentication');
    
    return new WebSocket(url, protocols);
  }

  /**
   * Setup token refresh mechanism to handle token expiry during long-lived connections
   */
  private setupTokenRefresh(): void {
    if (!this.options.refreshToken || !this.currentToken) {
      return;
    }

    // Refresh token every 50 minutes (assuming 1-hour token expiry)
    const refreshInterval = 50 * 60 * 1000; // 50 minutes in milliseconds
    
    this.tokenRefreshTimer = setInterval(async () => {
      try {
        const newToken = await this.options.refreshToken!();
        if (newToken && newToken !== this.currentToken) {
          logger.debug('Token refreshed, reconnecting WebSocket with new token');
          this.currentToken = newToken;
          await this.reconnectWithNewToken(newToken);
        }
      } catch (error) {
        logger.error('Failed to refresh WebSocket token', error as Error, {
          component: 'WebSocketService',
          action: 'token_refresh_failed'
        });
        // Continue with existing connection, let it fail naturally if token expires
      }
    }, refreshInterval);

    logger.debug('Token refresh timer setup for WebSocket connection');
  }

  /**
   * Reconnect with a new token while preserving connection state
   */
  private async reconnectWithNewToken(newToken: string): Promise<void> {
    if (this.state !== 'connected') {
      return;
    }

    const wasConnected = this.state === 'connected';
    const currentUrl = this.url;
    const currentOptions = { ...this.options, token: newToken };

    // Close current connection
    if (this.ws) {
      this.ws.close(1000, 'Token refresh');
    }

    // Small delay to ensure clean closure
    await new Promise(resolve => setTimeout(resolve, 100));

    // Reconnect with new token
    if (wasConnected) {
      this.connect(currentUrl, currentOptions);
    }
  }

  /**
   * Handle authentication errors from the server
   */
  private handleAuthError(error: any): void {
    logger.error('WebSocket authentication failed', undefined, {
      component: 'WebSocketService',
      action: 'auth_error',
      metadata: { 
        error: error.reason || error.message || 'Unknown auth error',
        code: error.code
      }
    });

    // Determine if this is a security violation (query param auth)
    const isSecurityViolation = error.reason && (
      error.reason.includes('Use Authorization header') ||
      error.reason.includes('Sec-WebSocket-Protocol') ||
      error.reason.includes('Query parameters not allowed')
    );

    this.options.onError?.({
      code: error.code || 1008,
      message: isSecurityViolation 
        ? 'Security violation: Use proper authentication headers'
        : 'Authentication failed: Invalid or expired token',
      timestamp: Date.now(),
      type: 'auth',
      recoverable: !isSecurityViolation
    });

    // Only attempt refresh for token expiry, not security violations
    if (!isSecurityViolation && this.options.refreshToken) {
      this.attemptTokenRefreshAndReconnect();
    }
  }

  /**
   * Attempt to refresh token and reconnect on auth failure
   */
  private async attemptTokenRefreshAndReconnect(): Promise<void> {
    try {
      const newToken = await this.options.refreshToken!();
      if (newToken) {
        logger.debug('Auth error recovery: refreshed token, attempting reconnection');
        this.currentToken = newToken;
        const newOptions = { ...this.options, token: newToken };
        
        // Wait a bit before reconnecting
        setTimeout(() => {
          this.connect(this.url, newOptions);
        }, 1000);
      }
    } catch (error) {
      logger.error('Failed to refresh token for auth error recovery', error as Error);
    }
  }

  /**
   * Get the secure WebSocket URL without exposing tokens
   * Ensures no tokens are leaked in URLs
   */
  public getSecureUrl(baseUrl: string): string {
    // Ensure the URL never contains tokens in query parameters
    const urlObj = new URL(baseUrl, window.location.origin);
    
    // Remove any existing token parameters (security cleanup)
    urlObj.searchParams.delete('token');
    urlObj.searchParams.delete('auth');
    urlObj.searchParams.delete('jwt');
    
    // Use secure WebSocket endpoint
    if (urlObj.pathname === '/ws' || urlObj.pathname.endsWith('/ws')) {
      urlObj.pathname = urlObj.pathname.replace(/\/ws$/, '/ws/secure');
    }
    
    return urlObj.toString();
  }

  /**
   * Update token for an existing connection
   */
  public async updateToken(newToken: string): Promise<void> {
    if (this.currentToken === newToken) {
      return; // No change needed
    }

    this.currentToken = newToken;
    this.options.token = newToken;

    // If connected, reconnect with new token
    if (this.state === 'connected') {
      await this.reconnectWithNewToken(newToken);
    }
  }

  /**
   * Get current connection security status
   */
  public getSecurityStatus(): {
    isSecure: boolean;
    authMethod: string;
    hasToken: boolean;
    tokenRefreshEnabled: boolean;
  } {
    return {
      isSecure: !!this.currentToken,
      authMethod: this.currentToken ? 'subprotocol' : 'none',
      hasToken: !!this.currentToken,
      tokenRefreshEnabled: !!this.options.refreshToken
    };
  }
}

export const webSocketService = new WebSocketService();