/**
 * WebSocket Bridge Client - Integrates with backend AgentWebSocketBridge
 * 
 * CRITICAL: Implements resilient WebSocket connection with circuit breaker,
 * retry logic, and idempotent initialization per CLAUDE.md requirements.
 * 
 * Business Value: Reliable real-time communication for substantive chat value
 */

import { logger } from '@/lib/logger';
import { WebSocketService } from '../webSocketService';
import { WebSocketMessage } from '@/types/unified';

interface CircuitBreakerConfig {
  failureThreshold: number;
  resetTimeout: number;
  halfOpenMaxAttempts: number;
}

interface RetryConfig {
  maxAttempts: number;
  baseDelay: number;
  maxDelay: number;
  backoffFactor: number;
}

enum CircuitBreakerState {
  CLOSED = 'CLOSED',     // Normal operation
  OPEN = 'OPEN',         // Circuit broken, rejecting requests
  HALF_OPEN = 'HALF_OPEN' // Testing if service recovered
}

interface WebSocketEvent {
  type: string;
  data: any;
  runId?: string;
  threadId?: string;
  timestamp: number;
}

/**
 * Circuit Breaker implementation for fault tolerance
 */
class CircuitBreaker {
  private state: CircuitBreakerState = CircuitBreakerState.CLOSED;
  private failureCount = 0;
  private lastFailureTime = 0;
  private successCount = 0;
  private config: CircuitBreakerConfig;
  
  constructor(config: Partial<CircuitBreakerConfig> = {}) {
    this.config = {
      failureThreshold: config.failureThreshold ?? 5,
      resetTimeout: config.resetTimeout ?? 60000, // 60 seconds
      halfOpenMaxAttempts: config.halfOpenMaxAttempts ?? 3
    };
  }
  
  async call<T>(fn: () => Promise<T>): Promise<T> {
    // Check if circuit should transition from OPEN to HALF_OPEN
    if (this.state === CircuitBreakerState.OPEN) {
      const timeSinceLastFailure = Date.now() - this.lastFailureTime;
      if (timeSinceLastFailure >= this.config.resetTimeout) {
        this.state = CircuitBreakerState.HALF_OPEN;
        this.successCount = 0;
        logger.info('Circuit breaker transitioning to HALF_OPEN');
      } else {
        throw new Error(`Circuit breaker is OPEN. Wait ${Math.ceil((this.config.resetTimeout - timeSinceLastFailure) / 1000)}s`);
      }
    }
    
    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }
  
  private onSuccess(): void {
    this.failureCount = 0;
    
    if (this.state === CircuitBreakerState.HALF_OPEN) {
      this.successCount++;
      if (this.successCount >= this.config.halfOpenMaxAttempts) {
        this.state = CircuitBreakerState.CLOSED;
        logger.info('Circuit breaker recovered to CLOSED');
      }
    }
  }
  
  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    this.successCount = 0;
    
    if (this.failureCount >= this.config.failureThreshold) {
      this.state = CircuitBreakerState.OPEN;
      logger.error('🚨 Circuit breaker opened due to failures', { 
        failureCount: this.failureCount 
      });
    }
  }
  
  getState(): CircuitBreakerState {
    return this.state;
  }
  
  reset(): void {
    this.state = CircuitBreakerState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
    this.lastFailureTime = 0;
  }
}

/**
 * Exponential Backoff implementation for retry logic
 */
class ExponentialBackoff {
  private attempt = 0;
  private config: RetryConfig;
  
  constructor(config: Partial<RetryConfig> = {}) {
    this.config = {
      maxAttempts: config.maxAttempts ?? 5,
      baseDelay: config.baseDelay ?? 100,
      maxDelay: config.maxDelay ?? 10000,
      backoffFactor: config.backoffFactor ?? 2
    };
  }
  
  async retry<T>(fn: () => Promise<T>): Promise<T> {
    this.attempt = 0;
    
    while (this.attempt < this.config.maxAttempts) {
      try {
        return await fn();
      } catch (error) {
        this.attempt++;
        
        if (this.attempt >= this.config.maxAttempts) {
          logger.error('🚨 Max retry attempts reached', { 
            attempts: this.attempt,
            error 
          });
          throw error;
        }
        
        const delay = this.calculateDelay();
        logger.warn(`Retry attempt ${this.attempt}/${this.config.maxAttempts} after ${delay}ms`);
        await this.sleep(delay);
      }
    }
    
    throw new Error('Retry failed');
  }
  
  private calculateDelay(): number {
    const delay = Math.min(
      this.config.baseDelay * Math.pow(this.config.backoffFactor, this.attempt - 1),
      this.config.maxDelay
    );
    // Add jitter (±20%)
    const jitter = delay * 0.2 * (Math.random() - 0.5);
    return Math.floor(delay + jitter);
  }
  
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  reset(): void {
    this.attempt = 0;
  }
}

/**
 * WebSocket Bridge Client - Main class
 * Integrates with backend AgentWebSocketBridge pattern
 */
export class WebSocketBridgeClient {
  private userId: string;
  private wsService: WebSocketService | null = null;
  private circuitBreaker: CircuitBreaker;
  private retryPolicy: ExponentialBackoff;
  private isIntegrated = false;
  private integrationPromise: Promise<void> | null = null;
  private disposed = false;
  
  // Event tracking for validation
  private supportedEvents = new Set<string>([
    'agent_started',
    'agent_thinking',
    'tool_executing',
    'tool_completed',
    'agent_completed',
    'agent_error',
    'progress_update',
    'status_update'
  ]);
  
  // Event handlers
  private eventHandlers = new Map<string, Set<(event: WebSocketEvent) => void>>();
  
  constructor(userId: string) {
    this.userId = userId;
    this.circuitBreaker = new CircuitBreaker();
    this.retryPolicy = new ExponentialBackoff();
    
    logger.info('WebSocketBridgeClient created', { userId });
  }
  
  /**
   * Ensure integration with backend bridge (idempotent)
   * Per websocket_agent_integration_critical.xml requirement
   */
  async ensureIntegration(): Promise<void> {
    // Idempotent check
    if (this.isIntegrated && this.wsService?.isConnected()) {
      logger.debug('Already integrated and connected');
      return;
    }
    
    // Prevent concurrent integration attempts
    if (this.integrationPromise) {
      logger.debug('Integration already in progress, waiting...');
      return this.integrationPromise;
    }
    
    this.integrationPromise = this.performIntegration();
    
    try {
      await this.integrationPromise;
    } finally {
      this.integrationPromise = null;
    }
  }
  
  private async performIntegration(): Promise<void> {
    logger.info('Starting WebSocket bridge integration', { userId: this.userId });
    
    try {
      await this.circuitBreaker.call(async () => {
        // Initialize WebSocket service
        if (!this.wsService) {
          this.wsService = new WebSocketService();
        }
        
        // Connect with retry logic
        await this.retryPolicy.retry(async () => {
          await this.wsService!.connect({
            onOpen: () => this.handleOpen(),
            onMessage: (msg) => this.handleMessage(msg),
            onError: (error) => this.handleError(error),
            onClose: () => this.handleClose(),
            onReconnect: () => this.handleReconnect()
          });
        });
        
        // Validate event flow
        await this.validateEventFlow();
        
        this.isIntegrated = true;
        logger.info('✅ WebSocket bridge integration complete', { userId: this.userId });
      });
    } catch (error) {
      logger.error('🚨 WebSocket bridge integration failed', { error, userId: this.userId });
      this.isIntegrated = false;
      throw error;
    }
  }
  
  /**
   * Validate that all critical events are supported
   * Per CLAUDE.md §6 requirements
   */
  private async validateEventFlow(): Promise<void> {
    const requiredEvents = [
      'agent_started',
      'agent_thinking',
      'tool_executing',
      'tool_completed',
      'agent_completed'
    ];
    
    for (const event of requiredEvents) {
      if (!this.supportsEvent(event)) {
        throw new Error(`Missing critical event support: ${event}`);
      }
    }
    
    logger.info('✅ Event flow validation passed');
  }
  
  /**
   * Check if event is supported
   */
  supportsEvent(eventType: string): boolean {
    return this.supportedEvents.has(eventType);
  }
  
  /**
   * Send agent update
   */
  async sendAgentUpdate(
    runId: string,
    eventType: string,
    data: any,
    threadId?: string
  ): Promise<void> {
    await this.ensureIntegration();
    
    const message: WebSocketMessage = {
      type: 'agent_update',
      data: {
        run_id: runId,
        event_type: eventType,
        data,
        thread_id: threadId,
        timestamp: Date.now()
      }
    };
    
    await this.circuitBreaker.call(async () => {
      await this.wsService!.send(message);
    });
  }
  
  /**
   * Send user message
   */
  async sendUserMessage(message: string, threadId?: string): Promise<void> {
    await this.ensureIntegration();
    
    const wsMessage: WebSocketMessage = {
      type: 'user_message',
      data: {
        message,
        thread_id: threadId,
        timestamp: Date.now()
      }
    };
    
    await this.circuitBreaker.call(async () => {
      await this.wsService!.send(wsMessage);
    });
  }
  
  /**
   * Subscribe to events
   */
  on(eventType: string, handler: (event: WebSocketEvent) => void): () => void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set());
    }
    
    this.eventHandlers.get(eventType)!.add(handler);
    
    // Return unsubscribe function
    return () => {
      const handlers = this.eventHandlers.get(eventType);
      if (handlers) {
        handlers.delete(handler);
      }
    };
  }
  
  /**
   * Handle incoming WebSocket message
   */
  private handleMessage(message: WebSocketMessage): void {
    try {
      // Convert to internal event format
      const event: WebSocketEvent = {
        type: message.type || 'unknown',
        data: message.data,
        runId: message.data?.run_id,
        threadId: message.data?.thread_id,
        timestamp: Date.now()
      };
      
      // Dispatch to handlers
      const handlers = this.eventHandlers.get(event.type);
      if (handlers) {
        for (const handler of handlers) {
          try {
            handler(event);
          } catch (error) {
            logger.error('🚨 Event handler error', { 
              eventType: event.type,
              error 
            });
          }
        }
      }
      
      // Also dispatch to wildcard handlers
      const wildcardHandlers = this.eventHandlers.get('*');
      if (wildcardHandlers) {
        for (const handler of wildcardHandlers) {
          try {
            handler(event);
          } catch (error) {
            logger.error('🚨 Wildcard handler error', { error });
          }
        }
      }
    } catch (error) {
      logger.error('🚨 Message processing error', { error, message });
    }
  }
  
  private handleOpen(): void {
    logger.info('WebSocket connection opened', { userId: this.userId });
    this.circuitBreaker.reset();
    this.retryPolicy.reset();
  }
  
  private handleError(error: any): void {
    logger.error('🚨 WebSocket error', { error, userId: this.userId });
  }
  
  private handleClose(): void {
    logger.warn('WebSocket connection closed', { userId: this.userId });
    this.isIntegrated = false;
  }
  
  private handleReconnect(): void {
    logger.info('WebSocket reconnected', { userId: this.userId });
    this.isIntegrated = true;
  }
  
  /**
   * Get connection status
   */
  isConnected(): boolean {
    return this.wsService?.isConnected() ?? false;
  }
  
  /**
   * Get circuit breaker state
   */
  getCircuitBreakerState(): CircuitBreakerState {
    return this.circuitBreaker.getState();
  }
  
  /**
   * Dispose and cleanup
   */
  dispose(): void {
    if (this.disposed) {
      return;
    }
    
    logger.info('Disposing WebSocketBridgeClient', { userId: this.userId });
    
    // Clear all event handlers
    this.eventHandlers.clear();
    
    // Disconnect WebSocket
    if (this.wsService) {
      this.wsService.disconnect();
      this.wsService = null;
    }
    
    this.isIntegrated = false;
    this.disposed = true;
    
    logger.info('✅ WebSocketBridgeClient disposed', { userId: this.userId });
  }
}