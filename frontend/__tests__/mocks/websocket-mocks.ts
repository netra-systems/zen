/**
 * WebSocket Mocks for Frontend Testing
 * 
 * CRITICAL CONTEXT: Phase 1, Agent 2 implementation
 * - WebSocket connection simulators
 * - Message streaming mocks  
 * - Connection state management
 * - Reconnection scenarios
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - Maximum file size: 300 lines
 * - Functions ≤8 lines each
 * - Full TypeScript type safety
 * - Support for error scenarios
 * - Delay simulation for timing tests
 */

import { EventEmitter } from 'events';
import { Message } from '@/types/domains/messages';

// ============================================================================
// WEBSOCKET STATE TYPES
// ============================================================================

export type WebSocketState = 'connecting' | 'open' | 'closing' | 'closed';
export type MessageType = 'message' | 'typing' | 'status' | 'error' | 'heartbeat';

export interface MockWebSocketMessage {
  type: MessageType;
  data: unknown;
  timestamp: number;
  id: string;
}

export interface StreamingMessageChunk {
  id: string;
  content: string;
  isComplete: boolean;
  chunkIndex: number;
  totalChunks?: number;
}

// ============================================================================
// ENHANCED WEBSOCKET MOCK CLASS
// ============================================================================

export class EnhancedMockWebSocket extends EventEmitter {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  public url: string;
  public readyState: number = EnhancedMockWebSocket.CONNECTING;
  public binaryType: string = 'blob';
  
  public onopen: ((event: Event) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;

  private connectionTimer: NodeJS.Timeout | null = null;
  private messageQueue: MockWebSocketMessage[] = [];
  private isConnected: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;

  constructor(url: string, protocols?: string | string[]) {
    super();
    this.url = url;
    this.setupEventHandlers();
    this.simulateConnection();
  }

  // ============================================================================
  // EVENT HANDLER SETUP - DOM-compatible methods
  // ============================================================================

  private setupEventHandlers() {
    this.addEventListener = jest.fn((event: string, handler: Function) => {
      this.on(event, handler);
    });
    this.removeEventListener = jest.fn((event: string, handler: Function) => {
      this.off(event, handler);
    });
  }

  public addEventListener!: jest.MockedFunction<(event: string, handler: Function) => void>;
  public removeEventListener!: jest.MockedFunction<(event: string, handler: Function) => void>;

  // ============================================================================
  // CONNECTION SIMULATION - Each function ≤8 lines
  // ============================================================================

  private simulateConnection(delay: number = 50) {
    this.connectionTimer = setTimeout(() => {
      this.readyState = EnhancedMockWebSocket.OPEN;
      this.isConnected = true;
      this.emitOpenEvent();
      this.processQueuedMessages();
    }, delay);
  }

  private emitOpenEvent() {
    const event = new Event('open');
    this.onopen?.(event);
    this.emit('open', event);
  }

  private processQueuedMessages() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (message) this.deliverMessage(message);
    }
  }

  // ============================================================================
  // MESSAGE HANDLING - Each function ≤8 lines
  // ============================================================================

  send(data: string | ArrayBuffer | Blob) {
    if (this.readyState !== EnhancedMockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    
    // Echo back for testing (simulate server response)
    setTimeout(() => {
      this.simulateEchoResponse(data);
    }, 20);
  }

  private simulateEchoResponse(data: string | ArrayBuffer | Blob) {
    if (this.isConnected) {
      const responseMessage = this.createResponseMessage(data);
      this.deliverMessage(responseMessage);
    }
  }

  private createResponseMessage(data: string | ArrayBuffer | Blob): MockWebSocketMessage {
    return {
      type: 'message',
      data: data.toString(),
      timestamp: Date.now(),
      id: `echo_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };
  }

  private deliverMessage(message: MockWebSocketMessage) {
    const messageData = typeof message.data === 'string' 
      ? message.data 
      : JSON.stringify(message.data);
    const event = new MessageEvent('message', { data: messageData });
    this.onmessage?.(event);
    this.emit('message', event);
  }

  // ============================================================================
  // CONNECTION CONTROL - Each function ≤8 lines
  // ============================================================================

  close(code?: number, reason?: string) {
    this.cleanupTimers();
    this.readyState = EnhancedMockWebSocket.CLOSING;
    this.isConnected = false;
    
    setTimeout(() => {
      this.readyState = EnhancedMockWebSocket.CLOSED;
      this.emitCloseEvent(code, reason);
    }, 30);
  }

  private cleanupTimers() {
    if (this.connectionTimer) {
      clearTimeout(this.connectionTimer);
      this.connectionTimer = null;
    }
  }

  private emitCloseEvent(code?: number, reason?: string) {
    const event = new CloseEvent('close', { code, reason });
    this.onclose?.(event);
    this.emit('close', event);
  }

  // ============================================================================
  // TEST SIMULATION METHODS - Each function ≤8 lines
  // ============================================================================

  simulateMessage(data: unknown, type: MessageType = 'message') {
    const message: MockWebSocketMessage = {
      type,
      data,
      timestamp: Date.now(),
      id: `sim_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };

    if (this.readyState === EnhancedMockWebSocket.OPEN) {
      this.deliverMessage(message);
    } else {
      this.messageQueue.push(message);
    }
  }

  simulateStreamingMessage(content: string, chunkSize: number = 50) {
    const chunks = this.createMessageChunks(content, chunkSize);
    chunks.forEach((chunk, index) => {
      setTimeout(() => {
        this.simulateMessage(chunk, 'message');
      }, index * 100);
    });
  }

  private createMessageChunks(content: string, chunkSize: number): StreamingMessageChunk[] {
    const chunks: StreamingMessageChunk[] = [];
    const messageId = `stream_${Date.now()}`;
    
    for (let i = 0; i < content.length; i += chunkSize) {
      const chunkContent = content.slice(i, i + chunkSize);
      const isComplete = i + chunkSize >= content.length;
      
      chunks.push({
        id: messageId,
        content: chunkContent,
        isComplete,
        chunkIndex: chunks.length,
        totalChunks: Math.ceil(content.length / chunkSize)
      });
    }
    
    return chunks;
  }

  simulateError(errorMessage: string = 'Connection error') {
    const event = new Event('error');
    this.onerror?.(event);
    this.emit('error', { message: errorMessage });
  }

  simulateReconnection() {
    this.close(1006, 'Connection lost');
    this.reconnectAttempts++;
    
    if (this.reconnectAttempts <= this.maxReconnectAttempts) {
      setTimeout(() => {
        this.readyState = EnhancedMockWebSocket.CONNECTING;
        this.simulateConnection(200);
      }, 1000);
    }
  }

  simulateTypingIndicator(isTyping: boolean, userId: string = 'agent') {
    this.simulateMessage({
      type: 'typing',
      userId,
      isTyping,
      timestamp: Date.now()
    }, 'typing');
  }

  simulateHeartbeat() {
    this.simulateMessage({
      type: 'heartbeat',
      timestamp: Date.now(),
      status: 'alive'
    }, 'heartbeat');
  }

  // ============================================================================
  // CONNECTION STATE UTILITIES
  // ============================================================================

  getConnectionState(): WebSocketState {
    switch (this.readyState) {
      case EnhancedMockWebSocket.CONNECTING: return 'connecting';
      case EnhancedMockWebSocket.OPEN: return 'open';
      case EnhancedMockWebSocket.CLOSING: return 'closing';
      case EnhancedMockWebSocket.CLOSED: return 'closed';
      default: return 'closed';
    }
  }

  isOpen(): boolean {
    return this.readyState === EnhancedMockWebSocket.OPEN;
  }

  getReconnectAttempts(): number {
    return this.reconnectAttempts;
  }

  resetReconnectAttempts() {
    this.reconnectAttempts = 0;
  }
}

// ============================================================================
// WEBSOCKET MANAGER FOR TESTS
// ============================================================================

export class WebSocketTestManager {
  private connections: Map<string, EnhancedMockWebSocket> = new Map();
  private messageHistory: MockWebSocketMessage[] = [];

  createConnection(url: string): EnhancedMockWebSocket {
    const connection = new EnhancedMockWebSocket(url);
    this.connections.set(url, connection);
    
    // Track all messages for testing
    connection.on('message', (event) => {
      this.messageHistory.push({
        type: 'message',
        data: event.data,
        timestamp: Date.now(),
        id: `tracked_${Date.now()}`
      });
    });
    
    return connection;
  }

  getConnection(url: string): EnhancedMockWebSocket | undefined {
    return this.connections.get(url);
  }

  closeAllConnections() {
    this.connections.forEach(connection => connection.close());
    this.connections.clear();
  }

  getMessageHistory(): MockWebSocketMessage[] {
    return [...this.messageHistory];
  }

  clearMessageHistory() {
    this.messageHistory = [];
  }

  simulateNetworkIssue() {
    this.connections.forEach(connection => {
      connection.simulateError('Network connection lost');
    });
  }
}

// ============================================================================
// GLOBAL MOCK INSTALLATION
// ============================================================================

export function installWebSocketMock() {
  (global as any).WebSocket = EnhancedMockWebSocket;
}

export function createWebSocketTestManager(): WebSocketTestManager {
  return new WebSocketTestManager();
}

// ============================================================================
// TEST UTILITIES
// ============================================================================

export function waitForWebSocketOpen(ws: EnhancedMockWebSocket, timeout: number = 1000): Promise<void> {
  return new Promise((resolve, reject) => {
    if (ws.isOpen()) {
      resolve();
      return;
    }

    const timer = setTimeout(() => {
      reject(new Error('WebSocket connection timeout'));
    }, timeout);

    ws.addEventListener('open', () => {
      clearTimeout(timer);
      resolve();
    });
  });
}

export function waitForMessage(ws: EnhancedMockWebSocket, timeout: number = 1000): Promise<MessageEvent> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error('Message timeout'));
    }, timeout);

    ws.addEventListener('message', (event) => {
      clearTimeout(timer);
      resolve(event);
    });
  });
}

// Default export for convenience
export default {
  EnhancedMockWebSocket,
  WebSocketTestManager,
  installWebSocketMock,
  createWebSocketTestManager,
  waitForWebSocketOpen,
  waitForMessage
};