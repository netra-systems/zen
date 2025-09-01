/**
 * WebSocket Test Helpers
 * 
 * Provides utilities for testing WebSocket functionality without requiring real connections.
 * These helpers ensure tests run reliably in isolated environments.
 * 
 * NOTE: This module works with the comprehensive WebSocket mock defined in jest.setup.js
 */

// Type definitions for better TypeScript support
export interface MockWebSocketEventOptions {
  data?: any;
  code?: number;
  reason?: string;
  error?: Error | string;
}

// Re-export the global mock WebSocket class that's defined in jest.setup.js
export const MockWebSocket = global.WebSocket;

/**
 * Enhanced WebSocket test helper that works with the global mock from jest.setup.js
 */
export class WebSocketTestHelper {
  private mockWs: any;

  constructor(mockWs?: any) {
    this.mockWs = mockWs || global.WebSocket;
  }

  /**
   * Create a new mock WebSocket instance for testing
   */
  createMockWebSocket(url = 'ws://localhost:8000/ws'): any {
    const ws = new (global.WebSocket as any)(url);
    // Track instances for cleanup (done in jest.setup.js)
    if (global.mockWebSocketInstances) {
      global.mockWebSocketInstances.push(ws);
    }
    return ws;
  }

  /**
   * Simulate WebSocket connection opening
   */
  simulateOpen(ws?: any): void {
    const target = ws || this.mockWs;
    if (target && typeof target.simulateOpen === 'function') {
      target.simulateOpen();
    }
  }

  /**
   * Simulate receiving a WebSocket message
   */
  simulateMessage(data: any, ws?: any): void {
    const target = ws || this.mockWs;
    if (target && typeof target.simulateMessage === 'function') {
      target.simulateMessage(data);
    }
  }

  /**
   * Simulate WebSocket connection closing
   */
  simulateClose(options: MockWebSocketEventOptions = {}, ws?: any): void {
    const { code = 1000, reason = 'Test close' } = options;
    const target = ws || this.mockWs;
    if (target && typeof target.simulateClose === 'function') {
      target.simulateClose(code, reason);
    }
  }

  /**
   * Simulate WebSocket error
   */
  simulateError(error: Error | string = 'Test error', ws?: any): void {
    const target = ws || this.mockWs;
    if (target && typeof target.simulateError === 'function') {
      const errorObj = typeof error === 'string' ? new Error(error) : error;
      target.simulateError(errorObj);
    }
  }

  /**
   * Get the current ready state of the WebSocket
   */
  getReadyState(ws?: any): number {
    const target = ws || this.mockWs;
    return target?.readyState || 0;
  }

  /**
   * Check if WebSocket is in CONNECTING state
   */
  isConnecting(ws?: any): boolean {
    return this.getReadyState(ws) === 0; // WebSocket.CONNECTING
  }

  /**
   * Check if WebSocket is in OPEN state
   */
  isOpen(ws?: any): boolean {
    return this.getReadyState(ws) === 1; // WebSocket.OPEN
  }

  /**
   * Check if WebSocket is in CLOSING state
   */
  isClosing(ws?: any): boolean {
    return this.getReadyState(ws) === 2; // WebSocket.CLOSING
  }

  /**
   * Check if WebSocket is in CLOSED state
   */
  isClosed(ws?: any): boolean {
    return this.getReadyState(ws) === 3; // WebSocket.CLOSED
  }

  /**
   * Wait for WebSocket to reach specific state (useful for async tests)
   */
  async waitForState(targetState: number, ws?: any, timeout = 1000): Promise<void> {
    const target = ws || this.mockWs;
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      
      const checkState = () => {
        if (this.getReadyState(target) === targetState) {
          resolve();
          return;
        }
        
        if (Date.now() - startTime > timeout) {
          reject(new Error(`WebSocket did not reach state ${targetState} within ${timeout}ms`));
          return;
        }
        
        setTimeout(checkState, 10);
      };
      
      checkState();
    });
  }

  /**
   * Get sent messages from the WebSocket mock
   */
  getSentMessages(ws?: any): any[] {
    const target = ws || this.mockWs;
    return target?.messageQueue || [];
  }

  /**
   * Clear message queue
   */
  clearMessageQueue(ws?: any): void {
    const target = ws || this.mockWs;
    if (target && target.messageQueue) {
      target.messageQueue = [];
    }
  }
}

/**
 * WebSocket Mock Factory - provides different mock configurations
 */
export class WebSocketMockFactory {
  /**
   * Create a WebSocket that immediately connects successfully
   */
  static createConnectedMock(url = 'ws://localhost:8000/ws'): any {
    const ws = new (global.WebSocket as any)(url);
    // Force immediate connection
    setTimeout(() => ws.simulateOpen(), 0);
    return ws;
  }

  /**
   * Create a WebSocket that fails to connect
   */
  static createFailedConnectionMock(url = 'ws://localhost:8000/ws'): any {
    const ws = new (global.WebSocket as any)(url);
    // Force immediate connection error
    setTimeout(() => ws.simulateError(new Error('Connection failed')), 0);
    return ws;
  }

  /**
   * Create a WebSocket that connects then disconnects
   */
  static createUnstableMock(url = 'ws://localhost:8000/ws'): any {
    const ws = new (global.WebSocket as any)(url);
    setTimeout(() => {
      ws.simulateOpen();
      setTimeout(() => ws.simulateClose(1006, 'Abnormal closure'), 100);
    }, 0);
    return ws;
  }

  /**
   * Create a WebSocket that can send and receive messages
   */
  static createInteractiveMock(url = 'ws://localhost:8000/ws'): any {
    const ws = new (global.WebSocket as any)(url);
    setTimeout(() => ws.simulateOpen(), 0);
    
    // Add helper method to respond to messages
    ws.respondToMessage = (response: any) => {
      setTimeout(() => ws.simulateMessage(response), 10);
    };
    
    return ws;
  }
}

/**
 * Legacy compatibility functions (maintained for existing tests)
 */
export function createMockWebSocket() {
  return global.WebSocket;
}

export function setupWebSocketMocks() {
  // WebSocket is already mocked in jest.setup.js
  return global.WebSocket;
}

export const mockWebSocketMessage = (type: string, data: any) => ({
  type,
  data,
  timestamp: Date.now()
});

export const mockWebSocketConnection = (connected = true) => {
  const mockConnection = {
    connected,
    reconnectAttempts: 0,
    lastError: null,
    readyState: connected ? 1 : 3, // WebSocket.OPEN or WebSocket.CLOSED
    url: 'ws://localhost:8000/ws',
    protocol: '',
    extensions: '',
    bufferedAmount: 0,
    binaryType: 'blob' as BinaryType,
    send: jest.fn(),
    close: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(() => true),
    onopen: null,
    onclose: null,
    onerror: null,
    onmessage: null,
    CONNECTING: 0,
    OPEN: 1,
    CLOSING: 2,
    CLOSED: 3
  };
  
  return mockConnection;
};

/**
 * WebSocket Event Validator - helps verify events are properly handled
 */
export class WebSocketEventValidator {
  private events: Array<{ type: string; data: any; timestamp: number }> = [];

  recordEvent(type: string, data: any): void {
    this.events.push({ type, data, timestamp: Date.now() });
  }

  getEvents(): Array<{ type: string; data: any; timestamp: number }> {
    return [...this.events];
  }

  getEventsByType(type: string): Array<{ type: string; data: any; timestamp: number }> {
    return this.events.filter(event => event.type === type);
  }

  hasEvent(type: string, data?: any): boolean {
    return this.events.some(event => {
      if (event.type !== type) return false;
      if (data === undefined) return true;
      return JSON.stringify(event.data) === JSON.stringify(data);
    });
  }

  clear(): void {
    this.events.length = 0;
  }

  getEventCount(type?: string): number {
    if (!type) return this.events.length;
    return this.getEventsByType(type).length;
  }
}

// Export singleton instances for convenience
export const webSocketTestHelper = new WebSocketTestHelper();
export const webSocketEventValidator = new WebSocketEventValidator();

/**
 * Utility function to ensure WebSocket mocks are working properly
 */
export function ensureWebSocketMocksWork(): boolean {
  try {
    // Test that global WebSocket is mocked
    if (typeof global.WebSocket !== 'function') {
      console.warn('WebSocket mock not found on global object');
      return false;
    }

    // Test that we can create instances
    const testWs = new (global.WebSocket as any)('ws://test');
    if (!testWs) {
      console.warn('Unable to create WebSocket mock instance');
      return false;
    }

    // Test that mock methods exist
    if (typeof testWs.simulateMessage !== 'function') {
      console.warn('WebSocket mock missing simulation methods');
      return false;
    }

    // Clean up test instance
    if (testWs.cleanup) testWs.cleanup();
    
    return true;
  } catch (error) {
    console.warn('WebSocket mock validation failed:', error);
    return false;
  }
}

// Auto-verify mocks are working when this module is imported in test environment
if (process.env.NODE_ENV === 'test' && typeof global !== 'undefined') {
  ensureWebSocketMocksWork();
}
