import { WebSocketMessage, AuthMessage, PingMessage, PongMessage } from '@/types/unified';
import { UnifiedWebSocketEvent } from '../types/unified-chat';
import { WebSocketStatus, WebSocketState, WebSocketServiceError } from '../types/domains/websocket';
import { logger } from '@/lib/logger';

// Re-export types for compatibility
export type { WebSocketStatus, WebSocketState, WebSocketServiceError } from '../types/domains/websocket';

import { CircuitBreakerStateValue } from '@/lib/circuit-breaker';

/**
 * Circuit breaker states for connection management
 */

interface CircuitBreakerConfig {
  failureThreshold: number;
  resetTimeout: number;
  halfOpenMaxAttempts: number;
}

interface ConnectionHealthMetrics {
  successfulConnections: number;
  failedConnections: number;
  messagesSent: number;
  messagesReceived: number;
  lastSuccessTime?: number;
  lastFailureTime?: number;
  averageLatency: number;
  connectionUptime: number;
}

interface QueueConfig {
  maxSize: number;
  ttl: number; // Time to live in ms
  priorityLevels: number;
}

interface MessageQueueItem {
  message: WebSocketMessage | UnifiedWebSocketEvent | AuthMessage | PingMessage | PongMessage;
  timestamp: number;
  priority: number;
  retries: number;
  id: string;
}

interface RetryPolicy {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  backoffMultiplier: number;
  jitterRange: number; // 0 to 1
}

interface RateLimitConfig {
  messages: number;
  window: number;
  burstSize?: number;
}

interface WebSocketOptionsResilient {
  onOpen?: () => void;
  onMessage?: (message: WebSocketMessage | UnifiedWebSocketEvent) => void;
  onError?: (error: WebSocketServiceError) => void;
  onClose?: () => void;
  onReconnect?: () => void;
  onBinaryMessage?: (data: ArrayBuffer) => void;
  onRateLimit?: () => void;
  onLargeMessage?: (progress: { chunks_received: number; total_chunks: number; progress_percent: number }) => void;
  onChunkedMessage?: (data: any) => void;
  onHealthChange?: (healthy: boolean, metrics: ConnectionHealthMetrics) => void;
  heartbeatInterval?: number;
  rateLimit?: RateLimitConfig;
  token?: string;
  refreshToken?: () => Promise<string | null>;
  // Ticket authentication support
  getTicket?: () => Promise<{ success: boolean; ticket?: { ticket: string; expires_at: number }; error?: string }>;
  useTicketAuth?: boolean;
  compression?: string[];
  circuitBreaker?: CircuitBreakerConfig;
  queueConfig?: QueueConfig;
  retryPolicy?: RetryPolicy;
  enableMetrics?: boolean;
  enableOfflineQueue?: boolean;
}

/**
 * Enhanced WebSocket service with comprehensive resilience patterns:
 * - Circuit breaker for connection management
 * - Advanced retry with exponential backoff and jitter
 * - Priority message queue with TTL
 * - Connection health monitoring
 * - Offline queue support
 * - Rate limiting with burst handling
 * - Session persistence and recovery
 */
class ResilientWebSocketService {
  private ws: WebSocket | null = null;
  private status: WebSocketStatus = 'CLOSED';
  private state: WebSocketState = 'disconnected';
  private options: WebSocketOptionsResilient = {};
  private url: string = '';
  
  // Circuit breaker
  private circuitBreakerState: CircuitBreakerStateValue = 'closed';
  private circuitBreakerFailures: number = 0;
  private circuitBreakerResetTimer: NodeJS.Timeout | null = null;
  private circuitBreakerConfig: CircuitBreakerConfig = {
    failureThreshold: 5,
    resetTimeout: 30000,
    halfOpenMaxAttempts: 3
  };
  
  // Message queue with priority
  private messageQueue: Map<string, MessageQueueItem> = new Map();
  private offlineQueue: Map<string, MessageQueueItem> = new Map();
  private queueConfig: QueueConfig = {
    maxSize: 1000,
    ttl: 60000,
    priorityLevels: 3
  };
  
  // Retry management
  private retryPolicy: RetryPolicy = {
    maxRetries: 10,
    baseDelay: 1000,
    maxDelay: 30000,
    backoffMultiplier: 2,
    jitterRange: 0.3
  };
  private reconnectAttempts: number = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  
  // Health monitoring
  private healthMetrics: ConnectionHealthMetrics = {
    successfulConnections: 0,
    failedConnections: 0,
    messagesSent: 0,
    messagesReceived: 0,
    averageLatency: 0,
    connectionUptime: 0
  };
  private healthCheckTimer: NodeJS.Timeout | null = null;
  private latencyMeasurements: number[] = [];
  private connectionStartTime: number = 0;
  
  // Rate limiting with token bucket
  private rateLimitTokens: number = 0;
  private rateLimitLastRefill: number = Date.now();
  private rateLimitConfig: RateLimitConfig = {
    messages: 60,
    window: 60000,
    burstSize: 10
  };
  
  // Session management
  private sessionId: string = '';
  private lastAcknowledgedMessageId: string = '';
  private sessionState: Map<string, any> = new Map();
  
  // Heartbeat and token management
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private tokenRefreshTimer: NodeJS.Timeout | null = null;
  private currentToken: string | null = null;
  private isRefreshingToken: boolean = false;
  
  // Ticket authentication support
  private currentTicket: string | null = null;
  private ticketExpiry: number | null = null;
  private isRefreshingTicket: boolean = false;
  
  // Connection lifecycle
  private connectionId: string = '';
  private isReconnecting: boolean = false;
  private isInitialized: boolean = false;
  
  // Event handlers
  public onStatusChange: ((status: WebSocketStatus) => void) | null = null;
  public onMessage: ((message: WebSocketMessage) => void) | null = null;

  constructor() {
    this.initializeService();
  }

  private initializeService(): void {
    this.sessionId = this.generateSessionId();
    this.setupOfflineDetection();
    this.startHealthMonitoring();
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private setupOfflineDetection(): void {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => this.handleOnline());
      window.addEventListener('offline', () => this.handleOffline());
    }
  }

  private handleOnline(): void {
    logger.info('Network online - attempting reconnection', {
      component: 'ResilientWebSocketService',
      action: 'network_online'
    });
    
    if (this.state === 'disconnected' && !this.isReconnecting) {
      this.processOfflineQueue();
      this.reconnect();
    }
  }

  private handleOffline(): void {
    logger.info('Network offline - enabling offline queue', {
      component: 'ResilientWebSocketService',
      action: 'network_offline'
    });
    
    // Move pending messages to offline queue
    if (this.options.enableOfflineQueue) {
      this.messageQueue.forEach((item, id) => {
        this.offlineQueue.set(id, item);
      });
      this.messageQueue.clear();
    }
  }

  private startHealthMonitoring(): void {
    if (!this.options.enableMetrics) return;
    
    this.healthCheckTimer = setInterval(() => {
      this.updateHealthMetrics();
      this.checkConnectionHealth();
    }, 5000);
  }

  private updateHealthMetrics(): void {
    if (this.state === 'connected' && this.connectionStartTime) {
      this.healthMetrics.connectionUptime = Date.now() - this.connectionStartTime;
    }
    
    // Calculate average latency
    if (this.latencyMeasurements.length > 0) {
      const sum = this.latencyMeasurements.reduce((a, b) => a + b, 0);
      this.healthMetrics.averageLatency = sum / this.latencyMeasurements.length;
      
      // Keep only last 100 measurements
      if (this.latencyMeasurements.length > 100) {
        this.latencyMeasurements = this.latencyMeasurements.slice(-100);
      }
    }
  }

  private checkConnectionHealth(): void {
    const isHealthy = this.isConnectionHealthy();
    
    if (this.options.onHealthChange) {
      this.options.onHealthChange(isHealthy, { ...this.healthMetrics });
    }
    
    // Trigger reconnection if unhealthy
    if (!isHealthy && this.state === 'connected') {
      logger.warn('Connection unhealthy - triggering reconnection', {
        component: 'ResilientWebSocketService',
        action: 'health_check_failed',
        metadata: this.healthMetrics
      });
      
      this.reconnect();
    }
  }

  private isConnectionHealthy(): boolean {
    if (this.state !== 'connected') return false;
    
    // Check if we've received messages recently
    const timeSinceLastMessage = this.healthMetrics.lastSuccessTime 
      ? Date.now() - this.healthMetrics.lastSuccessTime
      : Infinity;
    
    // Unhealthy if no messages for 30 seconds
    if (timeSinceLastMessage > 30000) return false;
    
    // Unhealthy if average latency is too high
    if (this.healthMetrics.averageLatency > 5000) return false;
    
    // Unhealthy if too many recent failures
    const recentFailureRate = this.healthMetrics.failedConnections / 
      (this.healthMetrics.successfulConnections + this.healthMetrics.failedConnections);
    if (recentFailureRate > 0.3) return false;
    
    return true;
  }

  // Circuit breaker implementation
  private shouldAllowConnection(): boolean {
    switch (this.circuitBreakerState) {
      case 'closed':
        return true;
      
      case 'open':
        logger.warn('Circuit breaker open - connection blocked', {
          component: 'ResilientWebSocketService',
          action: 'circuit_breaker_block'
        });
        return false;
      
      case 'half-open':
        logger.info('Circuit breaker half-open - testing connection', {
          component: 'ResilientWebSocketService',
          action: 'circuit_breaker_test'
        });
        return true;
      
      default:
        return false;
    }
  }

  private recordConnectionSuccess(): void {
    this.circuitBreakerFailures = 0;
    this.healthMetrics.successfulConnections++;
    this.healthMetrics.lastSuccessTime = Date.now();
    
    if (this.circuitBreakerState === 'half-open') {
      this.closeCircuitBreaker();
    }
  }

  private recordConnectionFailure(): void {
    this.circuitBreakerFailures++;
    this.healthMetrics.failedConnections++;
    this.healthMetrics.lastFailureTime = Date.now();
    
    if (this.circuitBreakerFailures >= this.circuitBreakerConfig.failureThreshold) {
      this.openCircuitBreaker();
    }
  }

  private openCircuitBreaker(): void {
    this.circuitBreakerState = 'open';
    
    logger.error('Circuit breaker opened due to failures', undefined, {
      component: 'ResilientWebSocketService',
      action: 'circuit_breaker_open',
      metadata: {
        failures: this.circuitBreakerFailures,
        threshold: this.circuitBreakerConfig.failureThreshold
      }
    });
    
    // Schedule reset to half-open
    this.circuitBreakerResetTimer = setTimeout(() => {
      this.circuitBreakerState = 'half-open';
      logger.info('Circuit breaker moved to half-open', {
        component: 'ResilientWebSocketService',
        action: 'circuit_breaker_half_open'
      });
      
      // Try reconnection
      this.reconnect();
    }, this.circuitBreakerConfig.resetTimeout);
  }

  private closeCircuitBreaker(): void {
    this.circuitBreakerState = 'closed';
    this.circuitBreakerFailures = 0;
    
    if (this.circuitBreakerResetTimer) {
      clearTimeout(this.circuitBreakerResetTimer);
      this.circuitBreakerResetTimer = null;
    }
    
    logger.info('Circuit breaker closed - connection stable', {
      component: 'ResilientWebSocketService',
      action: 'circuit_breaker_closed'
    });
  }

  // Enhanced retry with jitter
  private calculateRetryDelay(): number {
    const { baseDelay, maxDelay, backoffMultiplier, jitterRange } = this.retryPolicy;
    
    // Exponential backoff
    let delay = Math.min(
      baseDelay * Math.pow(backoffMultiplier, this.reconnectAttempts),
      maxDelay
    );
    
    // Add jitter to prevent thundering herd
    const jitter = delay * jitterRange * (Math.random() - 0.5);
    delay = Math.max(0, delay + jitter);
    
    return delay;
  }

  // Priority queue management
  private addToQueue(
    message: WebSocketMessage | UnifiedWebSocketEvent | AuthMessage | PingMessage | PongMessage,
    priority: number = 1
  ): boolean {
    if (this.messageQueue.size >= this.queueConfig.maxSize) {
      // Remove lowest priority old messages
      this.pruneQueue();
      
      if (this.messageQueue.size >= this.queueConfig.maxSize) {
        logger.warn('Message queue full - dropping message', {
          component: 'ResilientWebSocketService',
          action: 'queue_full'
        });
        return false;
      }
    }
    
    const id = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const item: MessageQueueItem = {
      message,
      timestamp: Date.now(),
      priority,
      retries: 0,
      id
    };
    
    this.messageQueue.set(id, item);
    return true;
  }

  private pruneQueue(): void {
    const now = Date.now();
    const items = Array.from(this.messageQueue.entries());
    
    // Remove expired messages
    items.forEach(([id, item]) => {
      if (now - item.timestamp > this.queueConfig.ttl) {
        this.messageQueue.delete(id);
      }
    });
    
    // If still full, remove lowest priority
    if (this.messageQueue.size >= this.queueConfig.maxSize) {
      items.sort((a, b) => a[1].priority - b[1].priority);
      const toRemove = items.slice(0, Math.floor(this.queueConfig.maxSize * 0.1));
      toRemove.forEach(([id]) => this.messageQueue.delete(id));
    }
  }

  private processQueue(): void {
    if (this.state !== 'connected' || this.messageQueue.size === 0) return;
    
    // Sort by priority and timestamp
    const items = Array.from(this.messageQueue.values());
    items.sort((a, b) => {
      if (a.priority !== b.priority) {
        return b.priority - a.priority; // Higher priority first
      }
      return a.timestamp - b.timestamp; // Older first
    });
    
    // Process messages respecting rate limit
    items.forEach(item => {
      if (this.checkRateLimit()) {
        this.sendInternal(item.message);
        this.messageQueue.delete(item.id);
      }
    });
  }

  private processOfflineQueue(): void {
    if (!this.options.enableOfflineQueue || this.offlineQueue.size === 0) return;
    
    logger.info(`Processing ${this.offlineQueue.size} offline messages`, {
      component: 'ResilientWebSocketService',
      action: 'process_offline_queue'
    });
    
    // Move offline messages back to main queue
    this.offlineQueue.forEach((item, id) => {
      this.messageQueue.set(id, item);
    });
    this.offlineQueue.clear();
    
    // Process queue
    this.processQueue();
  }

  // Rate limiting with token bucket
  private checkRateLimit(): boolean {
    const now = Date.now();
    const timePassed = now - this.rateLimitLastRefill;
    const tokensToAdd = (timePassed / this.rateLimitConfig.window) * this.rateLimitConfig.messages;
    
    this.rateLimitTokens = Math.min(
      this.rateLimitConfig.messages + (this.rateLimitConfig.burstSize || 0),
      this.rateLimitTokens + tokensToAdd
    );
    this.rateLimitLastRefill = now;
    
    if (this.rateLimitTokens >= 1) {
      this.rateLimitTokens--;
      return true;
    }
    
    if (this.options.onRateLimit) {
      this.options.onRateLimit();
    }
    
    return false;
  }

  // Session persistence
  public saveSessionState(key: string, value: any): void {
    this.sessionState.set(key, value);
    
    // Persist to localStorage if available
    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        const state = Object.fromEntries(this.sessionState);
        localStorage.setItem(`ws_session_${this.sessionId}`, JSON.stringify(state));
      } catch (e) {
        logger.warn('Failed to persist session state', {
          component: 'ResilientWebSocketService',
          action: 'persist_session_failed'
        });
      }
    }
  }

  public restoreSessionState(): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        const stored = localStorage.getItem(`ws_session_${this.sessionId}`);
        if (stored) {
          const state = JSON.parse(stored);
          Object.entries(state).forEach(([key, value]) => {
            this.sessionState.set(key, value);
          });
        }
      } catch (e) {
        logger.warn('Failed to restore session state', {
          component: 'ResilientWebSocketService',
          action: 'restore_session_failed'
        });
      }
    }
  }

  // Main connection method
  public connect(url: string, options: WebSocketOptionsResilient = {}): void {
    this.url = url;
    this.options = { ...this.options, ...options };
    
    // Apply custom configs
    if (options.circuitBreaker) {
      this.circuitBreakerConfig = { ...this.circuitBreakerConfig, ...options.circuitBreaker };
    }
    if (options.queueConfig) {
      this.queueConfig = { ...this.queueConfig, ...options.queueConfig };
    }
    if (options.retryPolicy) {
      this.retryPolicy = { ...this.retryPolicy, ...options.retryPolicy };
    }
    if (options.rateLimit) {
      this.rateLimitConfig = { ...this.rateLimitConfig, ...options.rateLimit };
      this.rateLimitTokens = this.rateLimitConfig.messages;
    }
    
    this.isInitialized = true;
    this.restoreSessionState();
    // Note: establishConnection is async but we don't await here to maintain non-blocking behavior
    this.establishConnection().catch(error => {
      logger.error('Failed to establish connection during connect', error as Error, {
        component: 'ResilientWebSocketService',
        action: 'connect_async_error'
      });
    });
  }

  private async establishConnection(): Promise<void> {
    if (!this.shouldAllowConnection()) {
      logger.warn('Connection blocked by circuit breaker', {
        component: 'ResilientWebSocketService',
        action: 'connection_blocked'
      });
      return;
    }
    
    if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || 
                    this.ws.readyState === WebSocket.OPEN)) {
      return;
    }
    
    try {
      this.connectionId = `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      this.connectionStartTime = Date.now();
      
      // Prepare authenticated URL (supports both ticket and JWT)
      const finalUrl = await this.prepareAuthenticatedUrl(this.url);
      
      this.ws = new WebSocket(finalUrl);
      this.setupEventHandlers();
      this.updateStatus('CONNECTING');
      
      logger.info('WebSocket connection initiated', {
        component: 'ResilientWebSocketService',
        action: 'connect',
        metadata: {
          connectionId: this.connectionId,
          attempt: this.reconnectAttempts,
          authMethod: this.currentTicket ? 'ticket' : (this.options.token ? 'jwt' : 'none')
        }
      });
      
    } catch (error) {
      logger.error('Failed to create WebSocket', error as Error, {
        component: 'ResilientWebSocketService',
        action: 'connect_error'
      });
      
      this.recordConnectionFailure();
      this.scheduleReconnect();
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return;
    
    this.ws.onopen = () => {
      this.handleOpen();
    };
    
    this.ws.onmessage = (event) => {
      this.handleMessage(event);
    };
    
    this.ws.onerror = (event) => {
      this.handleError(event);
    };
    
    this.ws.onclose = (event) => {
      this.handleClose(event);
    };
  }

  private handleOpen(): void {
    this.updateStatus('CONNECTED');
    this.state = 'connected';
    this.reconnectAttempts = 0;
    this.recordConnectionSuccess();
    
    logger.info('WebSocket connected', {
      component: 'ResilientWebSocketService',
      action: 'connected',
      metadata: {
        connectionId: this.connectionId,
        sessionId: this.sessionId
      }
    });
    
    // Start heartbeat
    this.startHeartbeat();
    
    // Process queued messages
    this.processQueue();
    this.processOfflineQueue();
    
    if (this.options.onOpen) {
      this.options.onOpen();
    }
  }

  private handleMessage(event: MessageEvent): void {
    this.healthMetrics.messagesReceived++;
    this.healthMetrics.lastSuccessTime = Date.now();
    
    try {
      const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
      
      // Handle system messages
      if (this.isSystemMessage(data)) {
        this.handleSystemMessage(data);
        return;
      }
      
      // Forward to application
      if (this.options.onMessage) {
        this.options.onMessage(data);
      }
      if (this.onMessage) {
        this.onMessage(data);
      }
      
    } catch (error) {
      logger.error('Failed to process message', error as Error, {
        component: 'ResilientWebSocketService',
        action: 'message_processing_error'
      });
    }
  }

  private handleError(event: Event): void {
    logger.error('WebSocket error', undefined, {
      component: 'ResilientWebSocketService',
      action: 'websocket_error',
      metadata: { connectionId: this.connectionId }
    });
    
    this.recordConnectionFailure();
    
    if (this.options.onError) {
      this.options.onError({
        type: 'connection',
        message: 'WebSocket error occurred',
        code: 'WS_ERROR',
        recoverable: true
      });
    }
  }

  private handleClose(event: CloseEvent): void {
    this.updateStatus('CLOSED');
    this.state = 'disconnected';
    this.stopHeartbeat();
    
    logger.info('WebSocket closed', {
      component: 'ResilientWebSocketService',
      action: 'closed',
      metadata: {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      }
    });
    
    if (this.options.onClose) {
      this.options.onClose();
    }
    
    // Schedule reconnection if not manually closed
    if (event.code !== 1000 && this.isInitialized) {
      this.scheduleReconnect();
    }
  }

  private isSystemMessage(data: any): boolean {
    return data.type === 'ping' || data.type === 'pong' || data.type === 'heartbeat';
  }

  private handleSystemMessage(data: any): void {
    switch (data.type) {
      case 'ping':
        this.sendPong();
        break;
      case 'pong':
        this.measureLatency(data);
        break;
      case 'heartbeat':
        this.sendHeartbeatAck();
        break;
    }
  }

  private measureLatency(pongData: any): void {
    if (pongData.timestamp) {
      const latency = Date.now() - pongData.timestamp;
      this.latencyMeasurements.push(latency);
    }
  }

  private startHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
    }
    
    const interval = this.options.heartbeatInterval || 30000;
    
    this.heartbeatTimer = setInterval(() => {
      if (this.state === 'connected') {
        this.sendPing();
      }
    }, interval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private sendPing(): void {
    const ping: PingMessage = {
      type: 'ping',
      timestamp: Date.now()
    };
    this.sendInternal(ping);
  }

  private sendPong(): void {
    const pong: PongMessage = {
      type: 'pong',
      timestamp: Date.now()
    };
    this.sendInternal(pong);
  }

  private sendHeartbeatAck(): void {
    this.sendInternal({ type: 'heartbeat_ack' });
  }

  private reconnect(): void {
    if (this.isReconnecting) return;
    
    this.isReconnecting = true;
    this.reconnectAttempts++;
    
    if (this.reconnectAttempts > this.retryPolicy.maxRetries) {
      logger.error('Max reconnection attempts reached', undefined, {
        component: 'ResilientWebSocketService',
        action: 'max_retries_exceeded',
        metadata: { attempts: this.reconnectAttempts }
      });
      
      this.isReconnecting = false;
      return;
    }
    
    const delay = this.calculateRetryDelay();
    
    logger.info(`Scheduling reconnection in ${delay}ms`, {
      component: 'ResilientWebSocketService',
      action: 'schedule_reconnect',
      metadata: {
        attempt: this.reconnectAttempts,
        delay
      }
    });
    
    this.scheduleReconnect(delay);
  }

  private scheduleReconnect(delay?: number): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    
    const reconnectDelay = delay || this.calculateRetryDelay();
    
    this.reconnectTimer = setTimeout(async () => {
      this.isReconnecting = false;
      
      if (this.options.onReconnect) {
        this.options.onReconnect();
      }
      
      try {
        await this.establishConnection();
      } catch (error) {
        logger.error('Failed to establish connection during reconnect', error as Error, {
          component: 'ResilientWebSocketService',
          action: 'reconnect_async_error'
        });
      }
    }, reconnectDelay);
  }

  private updateStatus(status: WebSocketStatus): void {
    this.status = status;
    
    if (this.onStatusChange) {
      this.onStatusChange(status);
    }
  }

  private addTokenToUrl(url: string, token: string): string {
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}jwt=${token}`;
  }

  private addTicketToUrl(url: string, ticket: string): string {
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}ticket=${ticket}`;
  }

  private async prepareAuthenticatedUrl(baseUrl: string): Promise<string> {
    // Try ticket authentication first if enabled
    if (this.options.useTicketAuth && this.options.getTicket) {
      try {
        logger.debug('Attempting ticket authentication for WebSocket', {
          component: 'ResilientWebSocketService',
          action: 'prepareAuthenticatedUrl'
        });

        const ticketResult = await this.options.getTicket();
        
        if (ticketResult.success && ticketResult.ticket) {
          this.currentTicket = ticketResult.ticket.ticket;
          this.ticketExpiry = ticketResult.ticket.expires_at;
          
          logger.debug('Using ticket authentication for WebSocket connection', {
            component: 'ResilientWebSocketService',
            action: 'prepareAuthenticatedUrl',
            metadata: {
              ticketLength: this.currentTicket.length,
              expiresAt: new Date(this.ticketExpiry).toISOString()
            }
          });
          
          return this.addTicketToUrl(baseUrl, this.currentTicket);
        } else {
          logger.warn('Ticket authentication failed, falling back to JWT', {
            component: 'ResilientWebSocketService',
            action: 'prepareAuthenticatedUrl',
            metadata: {
              error: ticketResult.error
            }
          });
        }
      } catch (error) {
        logger.error('Ticket authentication error, falling back to JWT', error as Error, {
          component: 'ResilientWebSocketService',
          action: 'prepareAuthenticatedUrl'
        });
      }
    }

    // Fallback to JWT token authentication
    if (this.options.token) {
      logger.debug('Using JWT authentication for WebSocket connection', {
        component: 'ResilientWebSocketService',
        action: 'prepareAuthenticatedUrl'
      });
      
      return this.addTokenToUrl(baseUrl, this.options.token);
    }

    // No authentication available
    logger.debug('No authentication method available, using base URL', {
      component: 'ResilientWebSocketService',
      action: 'prepareAuthenticatedUrl'
    });
    
    return baseUrl;
  }

  private sendInternal(
    message: WebSocketMessage | UnifiedWebSocketEvent | AuthMessage | PingMessage | PongMessage | any
  ): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      // Add to queue if not connected
      this.addToQueue(message);
      return false;
    }
    
    try {
      this.ws.send(JSON.stringify(message));
      this.healthMetrics.messagesSent++;
      return true;
    } catch (error) {
      logger.error('Failed to send message', error as Error, {
        component: 'ResilientWebSocketService',
        action: 'send_error'
      });
      
      // Add to queue for retry
      this.addToQueue(message);
      return false;
    }
  }

  // Public methods
  public sendMessage(
    message: WebSocketMessage | UnifiedWebSocketEvent,
    priority: number = 1
  ): void {
    if (!this.checkRateLimit()) {
      this.addToQueue(message, priority);
      return;
    }
    
    if (!this.sendInternal(message)) {
      this.addToQueue(message, priority);
    }
  }

  public disconnect(): void {
    this.isInitialized = false;
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.circuitBreakerResetTimer) {
      clearTimeout(this.circuitBreakerResetTimer);
      this.circuitBreakerResetTimer = null;
    }
    
    this.stopHeartbeat();
    
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    this.updateStatus('CLOSED');
    this.state = 'disconnected';
    
    logger.info('WebSocket disconnected', {
      component: 'ResilientWebSocketService',
      action: 'disconnect'
    });
  }

  public getStatus(): WebSocketStatus {
    return this.status;
  }

  public getState(): WebSocketState {
    return this.state;
  }

  public getHealthMetrics(): ConnectionHealthMetrics {
    return { ...this.healthMetrics };
  }

  public isConnected(): boolean {
    return this.state === 'connected' && this.ws?.readyState === WebSocket.OPEN;
  }

  public getQueueSize(): number {
    return this.messageQueue.size + this.offlineQueue.size;
  }

  public clearQueues(): void {
    this.messageQueue.clear();
    this.offlineQueue.clear();
  }

  public async updateToken(token: string): Promise<void> {
    this.currentToken = token;
    
    // Clear any cached ticket since we have a new token
    this.currentTicket = null;
    this.ticketExpiry = null;
    
    // Reconnect with new token if connected
    if (this.isConnected()) {
      this.disconnect();
      this.options.token = token;
      this.connect(this.url, this.options);
    }
  }

  /**
   * Refresh WebSocket ticket if it's close to expiry
   */
  public async refreshTicketIfNeeded(): Promise<boolean> {
    if (!this.options.useTicketAuth || !this.options.getTicket) {
      return false;
    }

    const refreshThreshold = 60000; // Refresh 1 minute before expiry
    const needsRefresh = !this.currentTicket || 
                        !this.ticketExpiry || 
                        (this.ticketExpiry - Date.now()) < refreshThreshold;

    if (!needsRefresh) {
      return true; // Current ticket is still valid
    }

    if (this.isRefreshingTicket) {
      logger.debug('Ticket refresh already in progress', {
        component: 'ResilientWebSocketService',
        action: 'refreshTicketIfNeeded'
      });
      return false;
    }

    this.isRefreshingTicket = true;

    try {
      logger.debug('Refreshing WebSocket ticket', {
        component: 'ResilientWebSocketService',
        action: 'refreshTicketIfNeeded',
        metadata: {
          currentTicketExpiry: this.ticketExpiry ? new Date(this.ticketExpiry).toISOString() : null
        }
      });

      const ticketResult = await this.options.getTicket();
      
      if (ticketResult.success && ticketResult.ticket) {
        this.currentTicket = ticketResult.ticket.ticket;
        this.ticketExpiry = ticketResult.ticket.expires_at;
        
        logger.debug('WebSocket ticket refreshed successfully', {
          component: 'ResilientWebSocketService',
          action: 'refreshTicketIfNeeded',
          metadata: {
            newTicketExpiry: new Date(this.ticketExpiry).toISOString()
          }
        });
        
        return true;
      } else {
        logger.warn('Failed to refresh WebSocket ticket', {
          component: 'ResilientWebSocketService',
          action: 'refreshTicketIfNeeded',
          metadata: {
            error: ticketResult.error
          }
        });
        
        return false;
      }
    } catch (error) {
      logger.error('Error refreshing WebSocket ticket', error as Error, {
        component: 'ResilientWebSocketService',
        action: 'refreshTicketIfNeeded'
      });
      
      return false;
    } finally {
      this.isRefreshingTicket = false;
    }
  }

  // Get secure URL helper (synchronous version using cached ticket)
  public getSecureUrl(baseUrl: string): string {
    // Prefer ticket authentication if available and not expired
    if (this.currentTicket && this.ticketExpiry && this.ticketExpiry > Date.now()) {
      return this.addTicketToUrl(baseUrl, this.currentTicket);
    }
    
    // Fallback to JWT token
    if (this.options.token) {
      return this.addTokenToUrl(baseUrl, this.options.token);
    }
    
    return baseUrl;
  }

  // Async version for cases where ticket refresh is needed
  public async getSecureUrlAsync(baseUrl: string): Promise<string> {
    return await this.prepareAuthenticatedUrl(baseUrl);
  }
}

// Export singleton instance
const resilientWebSocketService = new ResilientWebSocketService();
export default resilientWebSocketService;