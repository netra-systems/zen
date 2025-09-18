import { WebSocketMessage, AuthMessage, PingMessage, PongMessage } from '@/types/unified';
import { UnifiedWebSocketEvent } from '../types/unified-chat';
import { WebSocketStatus, WebSocketState, WebSocketServiceError } from '../types/domains/websocket';
import { config } from '@/config';
import { logger } from '@/lib/logger';
import { isWindowsPlatform, shouldUseWindowsStagingFallback } from '@/lib/unified-api-config';
import { websocketTicketService } from './websocketTicketService';
import type { TicketRequestResult } from '@/types/websocket-ticket';


// WebSocketStatus, WebSocketState, and WebSocketServiceError types imported from domains/websocket.ts
// Re-export for backward compatibility
export type { WebSocketStatus, WebSocketState, WebSocketServiceError } from '../types/domains/websocket';

interface RateLimitConfig {
  messages: number;
  window: number;
}

interface TicketRequestResult {
  success: boolean;
  ticket?: {
    ticket: string;
    expires_at: number;
  };
  error?: string;
}

interface WebSocketOptions {
  onOpen?: () => void;
  onMessage?: (message: WebSocketMessage | UnifiedWebSocketEvent) => void;
  onError?: (error: WebSocketServiceError) => void;
  onClose?: () => void;
  onReconnect?: () => void;
  onBinaryMessage?: (data: ArrayBuffer) => void;
  onRateLimit?: () => void;
  onLargeMessage?: (progress: { chunks_received: number; total_chunks: number; progress_percent: number }) => void;
  onChunkedMessage?: (data: any) => void;
  heartbeatInterval?: number;
  rateLimit?: RateLimitConfig;
  // Ticket authentication options (Method 4 in auth chain)
  useTicketAuth?: boolean;
  ticketTtl?: number; // TTL in seconds for ticket requests
  // JWT authentication options (fallback)
  token?: string;
  // refreshToken removed - JWT authentication no longer supported
  compression?: string[];  // Supported compression algorithms
}

class WebSocketService {
  // Environment-specific timeout configuration
  private getEnvironmentTimeouts() {
    const isStaging = typeof window !== 'undefined' &&
      (window.location.hostname.includes('staging') ||
       process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging' ||
       process.env.NODE_ENV === 'staging');

    // Issue #860: Windows platform compatibility adjustments
    const isWindows = isWindowsPlatform();
    const usingWindowsFallback = shouldUseWindowsStagingFallback();

    if (isStaging || usingWindowsFallback) {
      // Enhanced timeouts for staging or Windows fallback
      const windowsMultiplier = isWindows ? 1.5 : 1.0; // 50% longer timeouts on Windows

      return {
        baseReconnectDelay: Math.floor(1000 * windowsMultiplier),     // 1s-1.5s for staging/Windows
        maxReconnectDelay: Math.floor(30000 * windowsMultiplier),     // 30s-45s for staging/Windows
        connectionInterval: Math.floor(3000 * windowsMultiplier),     // 3s-4.5s minimum for staging/Windows
        heartbeatInterval: Math.floor(30000 * windowsMultiplier),     // 30s-45s heartbeat for staging/Windows
        maxMessageAssemblyTime: 300000, // 5 minutes for large messages
        authCooldown: Math.floor(10000 * windowsMultiplier)           // 10s-15s auth cooldown for staging/Windows
      };
    }

    return {
      baseReconnectDelay: 100,        // Keep fast for dev
      maxReconnectDelay: 10000,       // 10s for dev
      connectionInterval: 1000,       // 1s for dev
      heartbeatInterval: 15000,       // 15s for dev
      maxMessageAssemblyTime: 60000,  // 1 minute for dev
      authCooldown: 5000              // 5s auth cooldown for dev
    };
  }

  private ws: WebSocket | null = null;
  private status: WebSocketStatus = 'CLOSED';
  private state: WebSocketState = 'disconnected';
  private options: WebSocketOptions = {};
  private messageQueue: (WebSocketMessage | UnifiedWebSocketEvent | AuthMessage | PingMessage | PongMessage)[] = [];
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private url: string = '';
  private messageTimestamps: number[] = [];
  private pendingMessages: (WebSocketMessage | UnifiedWebSocketEvent | AuthMessage | PingMessage | PongMessage)[] = [];
  private isConnecting: boolean = false;  // Prevent multiple simultaneous connections
  private isIntentionalDisconnect: boolean = false;  // Track manual disconnections
  
  // Connection deduplication and throttling
  private connectionAttemptId: string | null = null;
  private lastConnectionAttempt: number = 0;
  private get MIN_CONNECTION_INTERVAL() { 
    return this.getEnvironmentTimeouts().connectionInterval; 
  }
  
  // Enhanced refresh handling
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 10;
  private baseReconnectDelay: number = this.getEnvironmentTimeouts().baseReconnectDelay;
  private maxReconnectDelay: number = this.getEnvironmentTimeouts().maxReconnectDelay;
  
  // Auth refresh coordination to prevent spam
  private lastRefreshAttempt: number = 0;
  private readonly MIN_REFRESH_INTERVAL_MS = 2000; // Same as auth service
  private lastSuccessfulConnection: number = 0;
  private connectionId: string = '';
  private beforeUnloadHandler: (() => void) | null = null;
  
  // Auth failure handling
  private authRetryCount: number = 0;
  private readonly MAX_AUTH_RETRIES = 3;
  private get AUTH_COOLDOWN_MS() { 
    return this.getEnvironmentTimeouts().authCooldown; 
  }
  private lastAuthFailure: number = 0;
  
  // Large message handling
  private messageAssemblies: Map<string, {
    messageId: string;
    totalChunks: number;
    receivedChunks: Map<number, any>;
    metadata: any;
    startedAt: number;
    isCompressed: boolean;
    compression: string;
  }> = new Map();
  private supportedCompression: string[] = ['gzip', 'deflate', 'lz4'];
  private maxMessageSize: number = 10 * 1024 * 1024; // 10MB
  private chunkSize: number = 64 * 1024; // 64KB

  public onStatusChange: ((status: WebSocketStatus) => void) | null = null;
  public onMessage: ((message: WebSocketMessage) => void) | null = null;

  // Type guards and validation
  private isBasicWebSocketMessage(obj: any): obj is WebSocketMessage {
    return obj && 
           typeof obj === 'object' && 
           typeof obj.type === 'string';
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
    const agentTypes = [
      'agent_started', 'tool_executing', 'agent_thinking', 'partial_result', 'agent_completed',
      // Additional backend agent types
      'start_agent', 'agent_response', 'agent_progress', 'agent_error'
    ];
    if (!agentTypes.includes(obj.type)) return null;
    
    // Backend messages use 'data' field, frontend expects 'payload'
    if (!obj.payload && obj.data) {
      obj.payload = obj.data;
    }
    
    // Agent messages should have payload, but allow empty objects
    if (!obj.payload) {
      obj.payload = {};
    }
    
    return obj;
  }

  private validateThreadMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    const threadTypes = [
      'thread_created', 'thread_loading', 'thread_loaded', 'thread_renamed',
      // Additional backend thread types
      'thread_update', 'thread_message'
    ];
    if (!threadTypes.includes(obj.type)) return null;
    
    // Backend messages use 'data' field, frontend expects 'payload'
    if (!obj.payload && obj.data) {
      obj.payload = obj.data;
    }
    
    // Thread messages should have payload, but allow empty objects
    if (!obj.payload) {
      obj.payload = {};
    }
    
    return obj;
  }

  private validateSystemMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    const systemTypes = [
      'auth', 'ping', 'pong', 'server_shutdown', 'system_message', 'error_message',
      // Additional backend connection lifecycle types
      'connect', 'disconnect', 'heartbeat', 'heartbeat_ack',
      // Backend user message types
      'user_message',
      // Broadcasting types
      'broadcast', 'room_message',
      // JSON-RPC types for MCP compatibility
      'jsonrpc_request', 'jsonrpc_response', 'jsonrpc_notification'
    ];
    if (!systemTypes.includes(obj.type)) return null;
    
    // Backend messages use 'data' field, frontend expects 'payload'
    if (obj.data && !obj.payload) {
      obj.payload = obj.data;
    }
    
    return obj;
  }

  private validateReportMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    const reportTypes = ['final_report', 'error', 'step_created'];
    if (!reportTypes.includes(obj.type)) return null;
    // Report messages may or may not have payload
    return obj;
  }

  private handleUnknownMessageType(obj: any): WebSocketMessage | UnifiedWebSocketEvent {
    logger.debug('Unknown WebSocket message type', undefined, {
      component: 'WebSocketService',
      action: 'unknown_message_type',
      metadata: { type: obj.type }
    });
    // Unknown messages should at least have a type field
    // Add a default empty payload if missing to maintain compatibility
    if (!obj.payload) {
      obj.payload = {};
    }
    return obj as WebSocketMessage;
  }

  private validateWebSocketMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    // First check if it's a valid object
    if (!obj || typeof obj !== 'object') {
      logger.warn('WebSocket message is not an object', undefined, {
        component: 'WebSocketService',
        action: 'validate_message',
        metadata: { messageType: typeof obj }
      });
      return null;
    }

    // Check for large message types first (they have different structure)
    if (this.isLargeMessage(obj)) {
      return obj as WebSocketMessage;
    }

    // Check if it has a type field (required for all standard messages)
    if (!obj.type || typeof obj.type !== 'string') {
      logger.warn('WebSocket message missing type field', undefined, {
        component: 'WebSocketService',
        action: 'validate_message',
        metadata: { hasType: !!obj.type, typeType: typeof obj.type }
      });
      return null;
    }
    
    // Try to categorize and validate based on message type
    const validated = this.validateAgentMessage(obj) ||
                     this.validateThreadMessage(obj) ||
                     this.validateSystemMessage(obj) ||
                     this.validateReportMessage(obj);
    
    // If no specific validator matched, handle as unknown type
    if (!validated) {
      return this.handleUnknownMessageType(obj);
    }
    
    return validated;
  }

  private setupConnectionState(url: string, options: WebSocketOptions): boolean {
    this.url = url;
    this.options = options;
    if (this.state === 'connected' || this.state === 'connecting') return false;
    this.state = 'connecting';
    this.status = 'CONNECTING';
    // Debounce status changes to prevent UI flicker
    if (this.onStatusChange) {
      clearTimeout(this.statusChangeTimer);
      this.statusChangeTimer = setTimeout(() => {
        this.onStatusChange?.(this.status);
      }, 10);
    }
    return true;
  }
  
  private statusChangeTimer: NodeJS.Timeout | null = null;

  private handleConnectionOpen(url: string, options: WebSocketOptions): void {
    logger.debug('[WebSocketService] Connection opened to:', url);
    this.state = 'connected';
    this.status = 'OPEN';
    
    // Reset all retry attempts on successful connection
    this.reconnectAttempts = 0;
    this.authRetryCount = 0;
    this.lastAuthFailure = 0;
    this.lastSuccessfulConnection = Date.now();
    this.connectionId = this.generateConnectionId();
    
    // Use immediate status change for connection open
    clearTimeout(this.statusChangeTimer);
    this.onStatusChange?.(this.status);
    
    // Restore session state if available
    this.restoreSessionState();
    
    // Authentication is handled via subprotocol during connection establishment
    this.processQueuedMessages();
    this.startHeartbeatIfConfigured(options);
    options.onOpen?.();
  }
  
  private generateConnectionId(): string {
    return `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
  
  private restoreSessionState(): void {
    // Attempt to restore session state from localStorage
    try {
      const sessionState = localStorage.getItem('websocket_session_state');
      if (sessionState) {
        const state = JSON.parse(sessionState);
        const stateAge = Date.now() - state.timestamp;
        
        // Only restore if state is less than 5 minutes old
        if (stateAge < 5 * 60 * 1000) {
          logger.debug('Restoring WebSocket session state', undefined, {
            component: 'WebSocketService',
            action: 'restore_session',
            metadata: { stateAge, threadId: state.threadId }
          });
          
          // Send session restore message
          this.send({
            type: 'session_restore',
            payload: {
              threadId: state.threadId,
              lastMessageId: state.lastMessageId,
              connectionId: this.connectionId
            }
          } as WebSocketMessage);
        }
      }
    } catch (error) {
      logger.debug('Failed to restore session state', undefined, {
        component: 'WebSocketService',
        action: 'restore_session_failed'
      });
    }
  }
  
  public saveSessionState(threadId: string, lastMessageId?: string): void {
    try {
      const state = {
        threadId,
        lastMessageId,
        connectionId: this.connectionId,
        timestamp: Date.now()
      };
      localStorage.setItem('websocket_session_state', JSON.stringify(state));
    } catch (error) {
      logger.debug('Failed to save session state', undefined, {
        component: 'WebSocketService',
        action: 'save_session_failed'
      });
    }
  }

  private processQueuedMessages(): void {
    // Limit batch processing to prevent blocking and memory issues
    const maxBatchSize = 50;
    let processed = 0;
    
    while (this.messageQueue.length > 0 && processed < maxBatchSize) {
      const msg = this.messageQueue.shift();
      if (msg) {
        this.send(msg);
        processed++;
      }
    }
    
    // If more messages remain, schedule next batch to prevent blocking
    if (this.messageQueue.length > 0) {
      setTimeout(() => this.processQueuedMessages(), 10);
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
    // Check if this is a large message
    if (this.isLargeMessage(rawMessage)) {
      this.handleLargeMessage(rawMessage, options);
      return;
    }

    const validatedMessage = this.validateWebSocketMessage(rawMessage);
    if (!validatedMessage) {
      this.handleInvalidMessage(rawMessage, options);
      return;
    }

    // Handle lifecycle messages first
    if (this.handleLifecycleMessage(validatedMessage)) {
      return;
    }

    this.onMessage?.(validatedMessage);
    options.onMessage?.(validatedMessage);
  }

  private handleLifecycleMessage(message: WebSocketMessage | UnifiedWebSocketEvent): boolean {
    const messageType = message.type;

    switch (messageType) {
      case 'ping':
        this.handleServerPing(message);
        return true;
      case 'pong':
        this.handleServerPong(message);
        return true;
      case 'heartbeat':
        // Respond to heartbeat with heartbeat_ack
        this.send({ type: 'heartbeat_ack', timestamp: Date.now() });
        logger.debug('Responded to server heartbeat');
        return true;
      case 'heartbeat_ack':
        // Server acknowledged our heartbeat
        logger.debug('Heartbeat acknowledged by server');
        return true;
      case 'server_shutdown':
        this.handleServerShutdown(message);
        return true;
      case 'connect':
      case 'system_message':
        // Connection-related messages, pass through to application
        return false;
      default:
        return false;
    }
  }

  private handleServerPing(message: any): void {
    // Respond to server ping with pong
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const pongResponse = {
        type: 'pong',
        timestamp: Date.now(),
        original_timestamp: message.timestamp,
        connection_id: this.getConnectionId()
      };
      
      this.send(pongResponse as PongMessage);
      logger.debug('Responded to server ping with pong');
    }
  }

  private handleServerPong(message: any): void {
    // Server responded to our ping
    logger.debug('Received pong from server', undefined, {
      component: 'WebSocketService',
      action: 'pong_received',
      metadata: { 
        latency: message.timestamp ? Date.now() - message.original_timestamp : undefined
      }
    });
  }

  private handleServerShutdown(message: any): void {
    // Server is shutting down gracefully
    logger.info('Server shutdown notification received', undefined, {
      component: 'WebSocketService',
      action: 'server_shutdown',
      metadata: { 
        drain_timeout: message.drain_timeout,
        server_message: message.message
      }
    });

    // Stop heartbeat to allow graceful shutdown
    this.stopHeartbeat();
    
    // Notify application of shutdown
    this.options.onError?.({
      code: 1001,
      message: message.message || 'Server is shutting down',
      timestamp: Date.now(),
      type: 'connection',
      recoverable: true
    });
  }

  private handleInvalidMessage(rawMessage: any, options: WebSocketOptions): void {
    const errorDetails = this.getInvalidMessageDetails(rawMessage);
    
    logger.warn('Invalid WebSocket message received', undefined, {
      component: 'WebSocketService',
      action: 'invalid_message',
      metadata: { 
        message: rawMessage,
        reason: errorDetails
      }
    });
    
    options.onError?.({
      code: 1003,
      message: `Invalid message structure: ${errorDetails}`,
      timestamp: Date.now(),
      type: 'parse',
      recoverable: true
    });
  }

  private getInvalidMessageDetails(rawMessage: any): string {
    if (rawMessage === null || rawMessage === undefined) {
      return 'message is null or undefined';
    }
    if (typeof rawMessage !== 'object') {
      return `message is not an object (type: ${typeof rawMessage})`;
    }
    if (!rawMessage.type) {
      return 'missing required type field';
    }
    if (typeof rawMessage.type !== 'string') {
      return `type field is not a string (type: ${typeof rawMessage.type})`;
    }
    return 'unknown validation failure';
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
    clearTimeout(this.statusChangeTimer);
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
    clearTimeout(this.statusChangeTimer);
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
    clearTimeout(this.statusChangeTimer);
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
    
    // Prevent unlimited growth of messageTimestamps array
    const oldLength = this.messageTimestamps.length;
    this.messageTimestamps = this.messageTimestamps.filter(ts => ts > windowStart);
    
    // Log if we cleaned up many old timestamps (potential memory leak indicator)
    if (oldLength - this.messageTimestamps.length > 100) {
      logger.debug(`Cleaned up ${oldLength - this.messageTimestamps.length} old message timestamps`);
    }
    
    // Hard limit on array size to prevent memory exhaustion
    if (this.messageTimestamps.length > 1000) {
      this.messageTimestamps = this.messageTimestamps.slice(-500); // Keep only last 500
      logger.warn('Message timestamps array exceeded 1000 entries, truncated to 500');
    }
    
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

  // Large message handling methods
  private isLargeMessage(message: any): boolean {
    const messageType = message?.message_type;
    return messageType && [
      'chunked_start', 'chunked_data', 'chunked_end',
      'binary', 'compressed', 'upload_progress'
    ].includes(messageType);
  }

  private handleLargeMessage(message: any, options: WebSocketOptions): void {
    const messageType = message.message_type;

    switch (messageType) {
      case 'chunked_start':
        this.handleChunkedStart(message, options);
        break;
      case 'chunked_data':
        this.handleChunkedData(message, options);
        break;
      case 'chunked_end':
        this.handleChunkedEnd(message, options);
        break;
      case 'binary':
      case 'compressed':
        this.handleBinaryCompressed(message, options);
        break;
      case 'upload_progress':
        this.handleUploadProgress(message, options);
        break;
      default:
        logger.warn('Unknown large message type:', messageType);
    }
  }

  private handleChunkedStart(message: any, options: WebSocketOptions): void {
    const { message_id, total_chunks, compression = 'none', is_binary = false } = message;
    
    this.messageAssemblies.set(message_id, {
      messageId: message_id,
      totalChunks: total_chunks,
      receivedChunks: new Map(),
      metadata: message,
      startedAt: Date.now(),
      isCompressed: compression !== 'none',
      compression
    });

    logger.debug(`Started chunked message assembly: ${message_id} (${total_chunks} chunks)`);
  }

  private handleChunkedData(message: any, options: WebSocketOptions): void {
    const { metadata, data } = message;
    const { message_id, chunk_index } = metadata;

    const assembly = this.messageAssemblies.get(message_id);
    if (!assembly) {
      logger.warn(`Received chunk for unknown message: ${message_id}`);
      return;
    }

    // Decode chunk data
    try {
      const chunkData = atob(data); // Base64 decode
      assembly.receivedChunks.set(chunk_index, chunkData);

      // Update progress
      const progress = {
        chunks_received: assembly.receivedChunks.size,
        total_chunks: assembly.totalChunks,
        progress_percent: (assembly.receivedChunks.size / assembly.totalChunks) * 100
      };

      options.onLargeMessage?.(progress);
      logger.debug(`Received chunk ${chunk_index + 1}/${assembly.totalChunks} for message ${message_id}`);
    } catch (error) {
      logger.error('Failed to decode chunk data:', error);
    }
  }

  private handleChunkedEnd(message: any, options: WebSocketOptions): void {
    const { message_id } = message;
    const assembly = this.messageAssemblies.get(message_id);
    
    if (!assembly) {
      logger.warn(`Received end for unknown message: ${message_id}`);
      return;
    }

    // Check if all chunks received
    if (assembly.receivedChunks.size !== assembly.totalChunks) {
      logger.error(`Missing chunks for message ${message_id}`);
      this.messageAssemblies.delete(message_id);
      return;
    }

    try {
      // Assemble message
      let assembledData = '';
      for (let i = 0; i < assembly.totalChunks; i++) {
        assembledData += assembly.receivedChunks.get(i) || '';
      }

      // Decompress if needed
      if (assembly.isCompressed) {
        assembledData = this.decompressData(assembledData, assembly.compression);
      }

      // Parse assembled message
      let finalMessage;
      try {
        finalMessage = JSON.parse(assembledData);
      } catch {
        finalMessage = { data: assembledData };
      }

      logger.info(`Successfully assembled message: ${message_id} (${assembledData.length} chars)`);
      
      // Clean up
      this.messageAssemblies.delete(message_id);

      // Process assembled message
      options.onChunkedMessage?.(finalMessage);
      this.onMessage?.(finalMessage);
      options.onMessage?.(finalMessage);

    } catch (error) {
      logger.error(`Failed to assemble message ${message_id}:`, error);
      this.messageAssemblies.delete(message_id);
    }
  }

  private handleBinaryCompressed(message: any, options: WebSocketOptions): void {
    const { data, compression = 'none', encoding = 'base64' } = message;
    
    try {
      // Decode data
      let decodedData = encoding === 'base64' ? atob(data) : data;

      // Decompress if needed
      if (compression !== 'none') {
        decodedData = this.decompressData(decodedData, compression);
      }

      // Try to parse as JSON, otherwise treat as binary
      let finalData;
      try {
        finalData = JSON.parse(decodedData);
      } catch {
        finalData = { data: decodedData, type: 'binary' };
      }

      this.onMessage?.(finalData);
      options.onMessage?.(finalData);

    } catch (error) {
      logger.error('Failed to process binary/compressed message:', error);
    }
  }

  private handleUploadProgress(message: any, options: WebSocketOptions): void {
    const { chunks_received, total_chunks, progress_percent } = message;
    
    const progress = {
      chunks_received,
      total_chunks,
      progress_percent
    };

    options.onLargeMessage?.(progress);
    logger.debug(`Upload progress: ${progress_percent.toFixed(1)}% (${chunks_received}/${total_chunks})`);
  }

  private decompressData(data: string, algorithm: string): string {
    // Note: Browser-based decompression would require additional libraries
    // For now, we'll assume data is already decompressed on the server side
    // or implement client-side decompression with libraries like pako
    logger.debug(`Decompression requested for algorithm: ${algorithm}`);
    return data;
  }

  // Large message sending support
  public async sendLargeMessage(message: any, compression: string = 'gzip'): Promise<boolean> {
    const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
    
    if (messageStr.length <= this.chunkSize) {
      // Send as regular message
      this.send(message);
      return true;
    }

    // Prepare chunked message
    const messageId = this.generateMessageId();
    const chunks = this.createMessageChunks(messageStr, messageId);

    try {
      // Send all chunks
      for (const chunk of chunks) {
        this.send(chunk);
        // Small delay between chunks to avoid overwhelming
        await new Promise(resolve => setTimeout(resolve, 10));
      }
      return true;
    } catch (error) {
      logger.error('Failed to send large message:', error);
      return false;
    }
  }

  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private createMessageChunks(data: string, messageId: string): any[] {
    const chunks = [];
    const totalChunks = Math.ceil(data.length / this.chunkSize);

    // Start message
    chunks.push({
      message_type: 'chunked_start',
      message_id: messageId,
      total_chunks: totalChunks,
      total_size: data.length,
      compression: 'none',
      is_binary: false,
      timestamp: Date.now()
    });

    // Data chunks
    for (let i = 0; i < data.length; i += this.chunkSize) {
      const chunk = data.slice(i, i + this.chunkSize);
      const chunkIndex = Math.floor(i / this.chunkSize);
      
      chunks.push({
        message_type: 'chunked_data',
        metadata: {
          chunk_id: this.generateMessageId(),
          message_id: messageId,
          chunk_index: chunkIndex,
          total_chunks: totalChunks,
          chunk_size: chunk.length,
          chunk_hash: this.hashString(chunk),
          compression: 'none',
          timestamp: Date.now(),
          is_final: chunkIndex === totalChunks - 1
        },
        data: btoa(chunk), // Base64 encode
        encoding: 'base64'
      });
    }

    // End message
    chunks.push({
      message_type: 'chunked_end',
      message_id: messageId,
      total_chunks: totalChunks,
      timestamp: Date.now()
    });

    return chunks;
  }

  private hashString(str: string): string {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return hash.toString(16);
  }

  public connect(url: string, options: WebSocketOptions = {}) {
    // Generate unique ID for this connection attempt
    const attemptId = `attempt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Check minimum interval between connection attempts
    const timeSinceLastAttempt = Date.now() - this.lastConnectionAttempt;
    if (timeSinceLastAttempt < this.MIN_CONNECTION_INTERVAL) {
      logger.debug('Connection attempt throttled due to minimum interval', undefined, {
        component: 'WebSocketService',
        action: 'connection_throttled',
        metadata: { 
          timeSinceLastAttempt, 
          minInterval: this.MIN_CONNECTION_INTERVAL,
          attemptId,
          rejectedReason: 'min_interval_violation'
        }
      });
      return;
    }
    
    // Check if another connection is in progress
    if (this.connectionAttemptId && this.isConnecting) {
      logger.debug('Connection already in progress, rejecting duplicate attempt', undefined, {
        component: 'WebSocketService',
        action: 'duplicate_connect_prevented',
        metadata: { 
          currentAttemptId: this.connectionAttemptId,
          rejectedAttemptId: attemptId,
          state: this.state
        }
      });
      return;
    }
    
    // If already connected, don't reconnect
    if (this.state === 'connected') {
      logger.debug('Already connected, ignoring connect call', undefined, {
        component: 'WebSocketService',
        action: 'already_connected',
        metadata: { attemptId }
      });
      return;
    }
    
    // Set connection attempt tracking
    this.connectionAttemptId = attemptId;
    this.lastConnectionAttempt = Date.now();
    
    // Issue #860: Windows platform logging and compatibility
    const isWindows = isWindowsPlatform();
    const usingWindowsFallback = shouldUseWindowsStagingFallback();

    logger.info('Starting WebSocket connection attempt', undefined, {
      component: 'WebSocketService',
      action: 'connection_attempt_start',
      metadata: {
        attemptId,
        url,
        hasToken: !!options.token,
        currentState: this.state,
        isWindows,
        usingWindowsFallback,
        issue860: isWindows ? 'Windows platform detected' : 'Non-Windows platform'
      }
    });
    
    // Close existing connection if in unexpected state
    if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
      logger.warn('Closing stale connecting WebSocket', undefined, {
        component: 'WebSocketService',
        action: 'close_stale_connecting'
      });
      this.ws.close();
      this.ws = null;
    }
    
    this.url = url;
    this.options = options;
    // JWT authentication removed - only ticket authentication supported
    this.isIntentionalDisconnect = false;  // Reset on new connection
    this.isConnecting = true;
    
    // Register page unload handler for graceful disconnect
    if (!this.beforeUnloadHandler && typeof window !== 'undefined') {
      this.beforeUnloadHandler = () => this.handlePageUnload();
      window.addEventListener('beforeunload', this.beforeUnloadHandler);
    }

    this.state = 'connecting';
    this.status = 'CONNECTING';
    // Use debounced status change to prevent flicker
    if (this.onStatusChange) {
      clearTimeout(this.statusChangeTimer);
      this.statusChangeTimer = setTimeout(() => {
        this.onStatusChange?.(this.status);
      }, 10);
    }

    try {
      // Create WebSocket connection (may be async for ticket auth)
      const wsResult = this.createSecureWebSocket(url, options);
      
      // Handle both sync (JWT) and async (ticket) WebSocket creation
      if (wsResult instanceof Promise) {
        wsResult.then((ws) => {
          this.ws = ws;
          this.setupWebSocketHandlers(ws, url, options);
        }).catch((error) => {
          this.handleConnectionCreationError(error, options);
        });
      } else {
        this.ws = wsResult;
        this.setupWebSocketHandlers(wsResult, url, options);
      }
    } catch (error) {
      this.handleConnectionCreationError(error, options);
    }
  }

  /**
   * Setup WebSocket event handlers
   */
  private setupWebSocketHandlers(ws: WebSocket, url: string, options: WebSocketOptions): void {
      // Issue #860: Windows platform compatibility
      const isWindows = isWindowsPlatform();
      const usingWindowsFallback = shouldUseWindowsStagingFallback();
      
      ws.onopen = () => {
        this.isConnecting = false;  // Connection established
        const currentAttemptId = this.connectionAttemptId;
        this.connectionAttemptId = null; // Clear attempt tracking
        
        logger.info('WebSocket connection established successfully', undefined, {
          component: 'WebSocketService',
          action: 'connection_success',
          metadata: { 
            attemptId: currentAttemptId,
            hasToken: !!options.token,
            useTicketAuth: !!options.useTicketAuth,
            connectionDuration: Date.now() - this.lastConnectionAttempt
          }
        });
        
        this.handleConnectionOpen(url, options);
        
        // Handle authenticated connections
        if (options.useTicketAuth) {
          logger.debug('WebSocket connected with ticket authentication');
        } else if (options.token) {
          logger.debug('WebSocket connected with JWT authentication');
        } else {
          logger.debug('WebSocket connected in development mode (no authentication required)');
        }

        // Only setup token refresh if we have JWT token
        if (options.token && !options.useTicketAuth) {
          this.setupTokenRefresh();
        }
      };

      ws.onmessage = (event) => {
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
        this.isConnecting = false;  // No longer connecting
        const currentAttemptId = this.connectionAttemptId;
        this.connectionAttemptId = null; // Clear attempt tracking
        
        this.state = 'disconnected';
        this.status = 'CLOSED';
        clearTimeout(this.statusChangeTimer);
        this.onStatusChange?.(this.status);
        this.stopHeartbeat();
        
        logger.info('WebSocket connection closed', undefined, {
          component: 'WebSocketService',
          action: 'connection_closed',
          metadata: { 
            attemptId: currentAttemptId,
            code: event.code,
            reason: event.reason,
            wasIntentional: this.isIntentionalDisconnect
          }
        });
        
        // Handle authentication errors appropriately based on environment
        if (event.code === 1008) {
          this.handleAuthFailure(event, options);
        } else {
          // Reset auth retry count on non-auth errors
          this.authRetryCount = 0;
          
          options.onClose?.();
          
          // Only attempt reconnection for non-auth errors
          if (this.options.onReconnect && !this.isIntentionalDisconnect) {
            this.scheduleReconnect();
          }
        }
      };

      this.ws.onerror = (error) => {
        this.isConnecting = false;  // Connection failed
        const currentAttemptId = this.connectionAttemptId;
        this.connectionAttemptId = null; // Clear attempt tracking
        
        // Only log as error if we're not in a known disconnection state
        const isExpectedError = this.state === 'disconnecting' || this.state === 'disconnected';
        // Issue #860: Windows platform error context
        const windowsErrorContext = {
          isWindows,
          usingWindowsFallback,
          issue860Note: isWindows && !usingWindowsFallback ? 'Consider setting NEXT_PUBLIC_ENVIRONMENT=staging for Windows compatibility' : null
        };

        if (!isExpectedError) {
          logger.error('WebSocket error occurred', undefined, {
            component: 'WebSocketService',
            action: 'websocket_error',
            metadata: {
              attemptId: currentAttemptId,
              error,
              state: this.state,
              hasToken: false, // JWT authentication removed
              ...windowsErrorContext
            }
          });
        }
        
        this.status = 'CLOSED';
        this.state = 'disconnected';
        clearTimeout(this.statusChangeTimer);
        this.onStatusChange?.(this.status);
        
        // Better error type detection:
        // - If we have a token but still got an error, it's likely an auth issue
        // - If we don't have a token, it's expected in production (not an error)
        // - Connection errors happen regardless of token status
        const errorType = 'connection'; // JWT removed - no token tracking
        const isDevelopment = typeof window !== 'undefined' && window.location.hostname === 'localhost';
        
        // Don't report auth errors in production when there's no token (expected behavior)
        if (!isDevelopment) { // No token tracking - auth handled by tickets
          logger.debug('WebSocket connection requires authentication');
          return;
        }
        
        // Issue #860: Windows-specific error messages
        let errorMessage = errorType === 'auth' ? 'Authentication error' : 'WebSocket connection error';
        if (isWindows && !usingWindowsFallback && errorType === 'connection') {
          errorMessage = 'WebSocket connection error (Windows detected - try setting NEXT_PUBLIC_ENVIRONMENT=staging for better compatibility)';
        }

        options.onError?.({
          code: 1006,
          message: errorMessage,
          timestamp: Date.now(),
          type: errorType,
          recoverable: errorType !== 'auth'
        });
      };
  }

  /**
   * Handle connection creation errors
   */
  private handleConnectionCreationError(error: any, options: WebSocketOptions): void {
    this.isConnecting = false;
    this.connectionAttemptId = null; // Clear attempt tracking
    
    logger.error('Failed to create WebSocket connection', error as Error, {
      component: 'WebSocketService',
      action: 'connection_creation_failed',
      metadata: {
        useTicketAuth: !!options.useTicketAuth,
        hasToken: !!options.token
      }
    });
    
    this.status = 'CLOSED';
    this.state = 'disconnected';
    this.onStatusChange?.(this.status);
    
    options.onError?.({
      code: 1000,
      message: (error as Error).message || 'Failed to create WebSocket connection',
      timestamp: Date.now(),
      type: 'connection',
      recoverable: true
    });
  }
  
  private startHeartbeat(interval: number) {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ 
          type: 'ping', 
          timestamp: Date.now(),
          connection_id: this.getConnectionId()
        } as PingMessage);
      }
    }, interval);
  }

  private getConnectionId(): string | undefined {
    // Extract connection ID from WebSocket if available
    return (this.ws as any)?._connectionId;
  }
  
  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
  
  private scheduleReconnect() {
    // Prevent reconnect if intentionally disconnected
    if (this.isIntentionalDisconnect) {
      logger.debug('Skipping reconnect - intentional disconnect', undefined, {
        component: 'WebSocketService',
        action: 'skip_reconnect'
      });
      return;
    }
    
    // Prevent if already connecting
    if (this.isConnecting) {
      logger.debug('Already connecting, skipping reconnect', undefined, {
        component: 'WebSocketService',
        action: 'skip_reconnect_already_connecting'  
      });
      return;
    }
    
    // Check auth failure cooldown period
    const timeSinceLastAuthFailure = Date.now() - this.lastAuthFailure;
    if (this.lastAuthFailure > 0 && timeSinceLastAuthFailure < this.AUTH_COOLDOWN_MS) {
      const waitTime = this.AUTH_COOLDOWN_MS - timeSinceLastAuthFailure;
      logger.debug('Delaying reconnect due to auth failure cooldown', undefined, {
        component: 'WebSocketService',
        action: 'reconnect_auth_cooldown',
        metadata: { waitTime, timeSinceLastAuthFailure }
      });
      
      setTimeout(() => {
        this.scheduleReconnect();
      }, waitTime);
      return;
    }
    
    if (this.reconnectTimer) return;
    
    // Check if we've exceeded max reconnect attempts
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      logger.error('Max reconnection attempts reached', undefined, {
        component: 'WebSocketService',
        action: 'max_reconnect_attempts',
        metadata: { attempts: this.reconnectAttempts }
      });
      this.status = 'CLOSED';
      this.state = 'disconnected';
      this.onStatusChange?.(this.status);
      return;
    }
    
    // First reconnect should be immediate (likely a page refresh)
    let delay: number;
    if (this.reconnectAttempts === 0) {
      delay = 0;  // Immediate reconnect on first attempt
    } else {
      // Calculate exponential backoff with jitter for subsequent attempts
      delay = Math.min(
        this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts - 1) + Math.random() * 100,
        this.maxReconnectDelay
      );
    }
    
    this.state = 'reconnecting';
    this.reconnectAttempts++;
    
    logger.debug(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`, undefined, {
      component: 'WebSocketService',
      action: 'schedule_reconnect',
      metadata: { attempt: this.reconnectAttempts, delay }
    });
    
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.options.onReconnect?.();
      this.connect(this.url, this.options);
    }, delay);
  }

  public send(message: WebSocketMessage | UnifiedWebSocketEvent | AuthMessage | PingMessage | PongMessage) {
    // Check rate limit if configured
    if (this.options.rateLimit) {
      if (!this.checkRateLimit()) {
        this.options.onRateLimit?.();
        
        // Prevent unbounded queue growth
        if (this.messageQueue.length < 100) {
          this.messageQueue.push(message);
        } else {
          logger.warn('Message queue full, dropping message to prevent memory leak');
        }
        return;
      }
      
      // Add current timestamp
      this.messageTimestamps.push(Date.now());
    }
    
    // JWT token refresh logic removed - using ticket authentication only
    
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message));
      } catch (error) {
        logger.error('Failed to send WebSocket message:', error);
        // Queue for retry if connection is still valid
        if (this.messageQueue.length < 100) {
          this.messageQueue.push(message);
        }
      }
    } else {
      // Queue message for sending when connected with size limit
      if (this.messageQueue.length < 100) {
        this.messageQueue.push(message);
      } else {
        logger.warn('Message queue full, dropping message to prevent memory leak');
      }
    }
  }

  public sendMessage(message: WebSocketMessage) {
    this.send(message);
  }
  
  public getState(): WebSocketState {
    return this.state;
  }

  public disconnect() {
    // Mark as intentional disconnect to prevent auto-reconnect
    this.isIntentionalDisconnect = true;
    this.isConnecting = false;
    
    // Clear ALL timers to prevent memory leaks
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.statusChangeTimer) {
      clearTimeout(this.statusChangeTimer);
      this.statusChangeTimer = null;
    }
    
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    
    // Clear token refresh timers
    this.clearTokenRefreshTimers();
    
    // Remove all event handlers to prevent memory leaks
    this.onStatusChange = null;
    this.onMessage = null;
    
    // Remove page unload handler
    if (this.beforeUnloadHandler && typeof window !== 'undefined') {
      window.removeEventListener('beforeunload', this.beforeUnloadHandler);
      this.beforeUnloadHandler = null;
    }
    
    // Close WebSocket connection
    if (this.ws) {
      // Remove all event listeners to prevent memory leaks
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      
      // Send graceful disconnect message if possible
      if (this.ws.readyState === WebSocket.OPEN) {
        try {
          this.send({
            type: 'disconnect',
            payload: {
              connectionId: this.connectionId,
              reason: 'client_disconnect'
            }
          } as WebSocketMessage);
        } catch (error) {
          // Ignore errors during disconnect
        }
      }
      
      if (this.ws.readyState !== WebSocket.CLOSED) {
        this.ws.close(1000, 'Normal closure');
      }
      
      this.ws = null;
    }
    
    // Clear all state and data structures to free memory
    this.state = 'disconnected';
    this.status = 'CLOSED';
    this.messageQueue.length = 0;
    this.pendingMessages.length = 0;
    this.messageTimestamps.length = 0;
    // JWT authentication removed - tokens not tracked
    this.reconnectAttempts = 0;
    this.options = {};
    this.url = '';
    
    // Reset connection tracking
    this.connectionAttemptId = null;
    this.lastConnectionAttempt = 0;
    this.authRetryCount = 0;
    this.lastAuthFailure = 0;
    this.lastRefreshAttempt = 0;
    this.lastSuccessfulConnection = 0;
    this.connectionId = '';
    
    // Clean up large message assemblies and clear memory
    this.messageAssemblies.clear();
    
    logger.debug('WebSocketService fully disconnected and cleaned up');
  }
  
  private handlePageUnload(): void {
    // Send graceful disconnect on page unload
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        // Use sendBeacon if available for reliability
        if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
          const data = JSON.stringify({
            type: 'page_unload',
            connectionId: this.connectionId,
            timestamp: Date.now()
          });
          const blob = new Blob([data], { type: 'application/json' });
          navigator.sendBeacon(`${this.url.replace(/^ws/, 'http')}/beacon`, blob);
        }
        
        // Also try to send via WebSocket
        this.ws.send(JSON.stringify({
          type: 'disconnect',
          payload: {
            connectionId: this.connectionId,
            reason: 'page_unload'
          }
        }));
      } catch (error) {
        // Ignore errors during unload
      }
    }
  }

  // Get statistics about large message handling
  public getLargeMessageStats(): {
    activeAssemblies: number;
    assemblyDetails: any[];
    supportedCompression: string[];
    maxMessageSize: number;
    chunkSize: number;
  } {
    const assemblyDetails = Array.from(this.messageAssemblies.values()).map(assembly => ({
      messageId: assembly.messageId,
      totalChunks: assembly.totalChunks,
      receivedChunks: assembly.receivedChunks.size,
      progress: (assembly.receivedChunks.size / assembly.totalChunks) * 100,
      isCompressed: assembly.isCompressed,
      compression: assembly.compression,
      startedAt: assembly.startedAt,
      ageSeconds: (Date.now() - assembly.startedAt) / 1000
    }));

    return {
      activeAssemblies: this.messageAssemblies.size,
      assemblyDetails,
      supportedCompression: this.supportedCompression,
      maxMessageSize: this.maxMessageSize,
      chunkSize: this.chunkSize
    };
  }

  /**
   * Creates a ticket-authenticated WebSocket connection using the integrated ticket service
   */
  private async createTicketAuthenticatedWebSocket(url: string, options: WebSocketOptions): Promise<WebSocket> {
    try {
      const ttlSeconds = options.ticketTtl || 300; // Default 5 minutes
      logger.debug('Requesting WebSocket ticket', {
        component: 'WebSocketService',
        action: 'ticket_request',
        metadata: { ttlSeconds }
      });

      const ticketResult = await websocketTicketService.acquireTicket(ttlSeconds);
      
      if (ticketResult.success && ticketResult.ticket) {
        // Add ticket to WebSocket URL as query parameter
        const wsUrl = new URL(url);
        wsUrl.searchParams.set('ticket', ticketResult.ticket.ticket);
        
        logger.debug('Creating WebSocket with ticket authentication', {
          component: 'WebSocketService',
          action: 'ticket_auth',
          metadata: {
            ticketLength: ticketResult.ticket.ticket.length,
            ticketExpiry: new Date(ticketResult.ticket.expires_at).toISOString(),
            hasUrl: !!ticketResult.ticket.websocket_url
          }
        });
        
        return new WebSocket(wsUrl.toString());
      } else {
        logger.warn('Ticket authentication failed, falling back to JWT', {
          component: 'WebSocketService',
          action: 'ticket_auth_failed',
          metadata: { 
            error: ticketResult.error,
            recoverable: ticketResult.recoverable 
          }
        });
        
        // Fallback to JWT authentication
        throw new Error(ticketResult.error || 'Failed to generate ticket');
      }
    } catch (error) {
      logger.error('Ticket authentication error', error as Error, {
        component: 'WebSocketService',
        action: 'ticket_auth_error'
      });
      throw error;
    }
  }

  /**
   * Creates a secure WebSocket connection using ticket-based authentication.
   * This is the primary authentication method - JWT fallback has been removed.
   * Supports both authenticated and development mode connections.
   */
  private createSecureWebSocket(url: string, options: WebSocketOptions): WebSocket | Promise<WebSocket> {
    // Use ticket-based authentication if enabled
    if (options.useTicketAuth && options.getTicket) {
      return this.createTicketAuthenticatedWebSocket(url, options);
    }

    // In development mode, allow connections without authentication
    const isDevelopment = typeof window !== 'undefined' && window.location.hostname === 'localhost';
    if (isDevelopment) {
      logger.debug('Creating WebSocket without authentication (development mode)');
      return new WebSocket(url);
    }
    
    // For production, require ticket authentication
    logger.error('WebSocket connection requires ticket authentication in production mode');
    throw new Error('Authentication required: ticket authentication not available');
  }



  /**
   * Handle authentication failures with exponential backoff and retry limits
   */
  private handleAuthFailure(event: CloseEvent, options: WebSocketOptions): void {
    this.lastAuthFailure = Date.now();
    this.authRetryCount++;
    
    logger.error('WebSocket authentication failed', undefined, {
      component: 'WebSocketService',
      action: 'auth_failure',
      metadata: { 
        code: event.code,
        reason: event.reason,
        authRetryCount: this.authRetryCount,
        maxRetries: this.MAX_AUTH_RETRIES,
        useTicketAuth: !!options.useTicketAuth
      }
    });

    // Handle ticket-specific authentication failures
    if (options.useTicketAuth) {
      const isTicketExpired = event.reason && (
        event.reason.includes('Ticket expired') ||
        event.reason.includes('ticket has expired') ||
        event.reason.includes('Invalid ticket') ||
        event.reason.includes('ticket')
      );
      
      if (isTicketExpired) {
        logger.debug('WebSocket closed due to ticket expiry, clearing cache and retrying');
        
        // Clear ticket cache to force fresh ticket generation
        websocketTicketService.clearTicketCache();
        
        // Attempt reconnection with fresh ticket
        if (this.authRetryCount < this.MAX_AUTH_RETRIES) {
          this.scheduleAuthRetry(options);
        } else {
          logger.error('Maximum ticket retry attempts exceeded', undefined, {
            component: 'WebSocketService',
            action: 'ticket_max_retries_exceeded'
          });
          
          // No JWT fallback available - connection failed
          this.setState('error');
          options.onClose?.();
        }
        return;
      }
    }

    // In development mode without ticket auth, don't treat auth errors as fatal  
    if (!options.useTicketAuth) {
      logger.debug('WebSocket auth error in development mode (no auth), ignoring');
      options.onClose?.();
      return;
    }

    // Check if we've exceeded max auth retries
    if (this.authRetryCount >= this.MAX_AUTH_RETRIES) {
      logger.error('Maximum auth retry attempts exceeded, giving up', undefined, {
        component: 'WebSocketService',
        action: 'auth_max_retries_exceeded',
        metadata: { 
          authRetryCount: this.authRetryCount,
          maxRetries: this.MAX_AUTH_RETRIES
        }
      });
      
      this.options.onError?.({
        code: event.code,
        message: 'Authentication failed: Maximum retry attempts exceeded. Please re-authenticate.',
        timestamp: Date.now(),
        type: 'auth',
        recoverable: false
      });
      
      options.onClose?.();
      return;
    }

    // JWT token expiry logic removed - handle all auth failures with exponential backoff
    this.scheduleAuthRetry(options);
  }

  /**
   * Schedule auth retry with exponential backoff and cooldown period
   */
  private scheduleAuthRetry(options: WebSocketOptions): void {
    // Calculate exponential backoff delay
    const baseDelay = this.AUTH_COOLDOWN_MS;
    const backoffMultiplier = Math.pow(2, this.authRetryCount - 1);
    const jitter = Math.random() * 1000; // Add jitter to prevent thundering herd
    const delay = Math.min(baseDelay * backoffMultiplier + jitter, 30000); // Cap at 30 seconds
    
    logger.info('Scheduling auth retry with exponential backoff', undefined, {
      component: 'WebSocketService',
      action: 'schedule_auth_retry',
      metadata: {
        attempt: this.authRetryCount,
        maxRetries: this.MAX_AUTH_RETRIES,
        delayMs: delay,
        baseDelay,
        backoffMultiplier
      }
    });
    
    // Use reconnect timer for auth retries
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      
      if (this.authRetryCount < this.MAX_AUTH_RETRIES) {
        logger.debug('Attempting auth retry', undefined, {
          component: 'WebSocketService',
          action: 'auth_retry_attempt',
          metadata: { attempt: this.authRetryCount }
        });
        
        // Attempt token refresh first, then reconnect
        if (this.options.refreshToken) {
          this.attemptTokenRefreshAndReconnect();
        } else {
          // No refresh capability, try reconnecting with existing token
          this.connect(this.url, this.options);
        }
      }
    }, delay);
    
    options.onClose?.();
  }

  /**
   * Handle authentication errors from the server (legacy method)
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
   * Attempt to refresh authentication (ticket or token) and reconnect on auth failure
   */
  private async attemptTokenRefreshAndReconnect(): Promise<void> {
    // If using ticket auth, attempt ticket refresh
    if (this.options.useTicketAuth) {
      try {
        // Clear ticket cache to force fresh ticket generation
        websocketTicketService.clearTicketCache();
        
        const ttlSeconds = this.options.ticketTtl || 300;
        const freshTicket = await websocketTicketService.acquireTicket(ttlSeconds);
        
        if (freshTicket.success) {
          logger.debug('Ticket refreshed after auth failure, reconnecting');
          
          // Reset retry counts on successful ticket refresh
          this.reconnectAttempts = 0;
          this.authRetryCount = 0;
          
          // Reconnect with fresh ticket
          setTimeout(() => {
            this.connect(this.url, this.options);
          }, 1000);
          return;
        } else {
          logger.warn('Failed to refresh ticket - no JWT fallback available', {
            error: freshTicket.error,
            recoverable: freshTicket.recoverable
          });
          // No JWT fallback available - end process here
        }
      } catch (error) {
        logger.error('Ticket refresh failed - no JWT fallback available', error as Error);
        // No JWT refresh available
      }
    }
    
    // JWT refresh logic removed - only ticket authentication supported
    logger.error('WebSocket: Authentication failed and no JWT fallback available');
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
    
    // Use unified WebSocket endpoint 
    // All WebSocket connections now use the single unified '/ws' endpoint
    if (urlObj.pathname !== '/ws') {
      urlObj.pathname = '/ws';
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
    
    // Setup new refresh timer for the new token
    this.setupTokenRefresh();
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
      isSecure: !!this.options.useTicketAuth,
      authMethod: this.options.useTicketAuth ? 'ticket' : 'none', 
      hasToken: false, // JWT tracking removed
      tokenRefreshEnabled: false // JWT refresh removed
    };
  }
}

export const webSocketService = new WebSocketService();