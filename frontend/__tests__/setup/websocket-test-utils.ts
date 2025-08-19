/**
 * Real WebSocket Test Utilities - Simulates actual WebSocket behavior
 * Replaces excessive jest.fn() mocking with realistic WebSocket simulation
 */

export interface WebSocketLike {
  readonly readyState: number;
  readonly url: string;
  send(data: string | ArrayBuffer | Blob): void;
  close(code?: number, reason?: string): void;
  addEventListener(type: string, listener: EventListener): void;
  removeEventListener(type: string, listener: EventListener): void;
  onopen: ((event: Event) => void) | null;
  onclose: ((event: CloseEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent) => void) | null;
}

/**
 * Real WebSocket simulation that mimics actual WebSocket behavior
 */
export class TestWebSocket implements WebSocketLike {
  public readyState: number = 0; // CONNECTING
  public readonly url: string;
  public onopen: ((event: Event) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;
  
  private listeners: Map<string, EventListener[]> = new Map();
  private messageQueue: string[] = [];
  private connectionDelay: number = 10;
  private isClosing: boolean = false;
  
  constructor(url: string, protocols?: string | string[]) {
    this.url = url;
    // Simulate async connection
    setTimeout(() => this.simulateOpen(), this.connectionDelay);
  }
  
  send(data: string | ArrayBuffer | Blob): void {
    if (this.readyState !== 1) { // Not OPEN
      throw new Error('WebSocket is not in OPEN state');
    }
    
    // Immediately add to queue for testing synchronization
    this.messageQueue.push(data.toString());
  }
  
  close(code: number = 1000, reason: string = ''): void {
    if (this.readyState === 2 || this.readyState === 3) return; // Already closing/closed
    
    this.isClosing = true;
    this.readyState = 2; // CLOSING
    
    setTimeout(() => {
      this.readyState = 3; // CLOSED
      this.triggerClose(code, reason);
    }, 5);
  }
  
  addEventListener(type: string, listener: EventListener): void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type)!.push(listener);
  }
  
  removeEventListener(type: string, listener: EventListener): void {
    const listeners = this.listeners.get(type);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }
  
  // Test utilities for simulating WebSocket behavior
  simulateMessage(data: any): void {
    if (this.readyState !== 1) return;
    
    const messageData = typeof data === 'string' ? data : JSON.stringify(data);
    const event = new MessageEvent('message', { data: messageData });
    
    this.triggerEvent('message', event);
    if (this.onmessage) {
      this.onmessage(event);
    }
  }
  
  simulateError(error?: any): void {
    const event = new ErrorEvent('error', { error });
    this.readyState = 3; // CLOSED
    
    this.triggerEvent('error', event);
    if (this.onerror) {
      this.onerror(event);
    }
  }
  
  simulateReconnect(): void {
    this.readyState = 0; // CONNECTING
    setTimeout(() => this.simulateOpen(), this.connectionDelay);
  }
  
  private simulateOpen(): void {
    if (this.isClosing) return;
    
    this.readyState = 1; // OPEN
    const event = new Event('open');
    
    this.triggerEvent('open', event);
    if (this.onopen) {
      this.onopen(event);
    }
  }
  
  private triggerClose(code: number, reason: string): void {
    const event = new CloseEvent('close', { code, reason });
    
    this.triggerEvent('close', event);
    if (this.onclose) {
      this.onclose(event);
    }
  }
  
  private triggerEvent(type: string, event: Event): void {
    const listeners = this.listeners.get(type);
    if (listeners) {
      listeners.forEach(listener => listener(event));
    }
  }
  
  // Test utilities
  getSentMessages(): string[] {
    return [...this.messageQueue];
  }
  
  clearMessageQueue(): void {
    this.messageQueue = [];
  }
  
  setConnectionDelay(ms: number): void {
    this.connectionDelay = ms;
  }
}

/**
 * WebSocket test setup with real behavior simulation
 */
export function setupMockWebSocket(): TestWebSocket {
  const testWebSocket = new TestWebSocket('ws://localhost:8000/ws');
  
  // Replace global WebSocket with our test implementation
  global.WebSocket = jest.fn().mockImplementation((url: string, protocols?: string | string[]) => {
    return new TestWebSocket(url, protocols);
  });
  
  global.mockWebSocket = testWebSocket;
  return testWebSocket;
}

/**
 * Reset WebSocket test state
 */
export function resetMockWebSocket(): void {
  if (global.mockWebSocket && global.mockWebSocket instanceof TestWebSocket) {
    global.mockWebSocket.clearMessageQueue();
    global.mockWebSocket.readyState = 1; // OPEN
  }
}

/**
 * Simulate WebSocket open event with real behavior
 */
export function simulateWebSocketOpen(): void {
  if (global.mockWebSocket && global.mockWebSocket instanceof TestWebSocket) {
    global.mockWebSocket.simulateReconnect();
  }
}

/**
 * Simulate WebSocket message with real event handling
 */
export function simulateWebSocketMessage(data: any): void {
  if (global.mockWebSocket && global.mockWebSocket instanceof TestWebSocket) {
    global.mockWebSocket.simulateMessage(data);
  }
}

/**
 * Simulate WebSocket close with real state transitions
 */
export function simulateWebSocketClose(code: number = 1000, reason: string = 'Normal closure'): void {
  if (global.mockWebSocket && global.mockWebSocket instanceof TestWebSocket) {
    global.mockWebSocket.close(code, reason);
  }
}

/**
 * Simulate WebSocket error with real error handling
 */
export function simulateWebSocketError(error?: any): void {
  if (global.mockWebSocket && global.mockWebSocket instanceof TestWebSocket) {
    global.mockWebSocket.simulateError(error);
  }
}

/**
 * Connection state manager for testing WebSocket states
 */
export class ConnectionStateManager {
  private state: string = 'disconnected';
  private callbacks: ((state: string) => void)[] = [];
  private stateHistory: { state: string; timestamp: number }[] = [];
  
  setState(newState: string): void {
    this.state = newState;
    this.stateHistory.push({ state: newState, timestamp: Date.now() });
    this.notifyCallbacks();
  }
  
  getState(): string {
    return this.state;
  }
  
  getStateHistory(): { state: string; timestamp: number }[] {
    return [...this.stateHistory];
  }
  
  addCallback(callback: (state: string) => void): void {
    this.callbacks.push(callback);
  }
  
  clearHistory(): void {
    this.stateHistory = [];
  }
  
  private notifyCallbacks(): void {
    this.callbacks.forEach(callback => callback(this.state));
  }
}

/**
 * Message buffer for testing message queuing and processing
 */
export class MessageBuffer {
  private messages: string[] = [];
  private maxSize: number = 1000;
  private processingTime: number = 0;
  
  add(message: string): boolean {
    if (this.messages.length >= this.maxSize) {
      return false;
    }
    this.messages.push(message);
    return true;
  }
  
  flush(): string[] {
    const messages = [...this.messages];
    this.messages = [];
    return messages;
  }
  
  size(): number {
    return this.messages.length;
  }
  
  peek(): string | undefined {
    return this.messages[0];
  }
  
  setMaxSize(size: number): void {
    this.maxSize = size;
  }
  
  getProcessingTime(): number {
    return this.processingTime;
  }
  
  simulateProcessing(timeMs: number): void {
    this.processingTime = timeMs;
  }
}

/**
 * Performance measurement utilities for WebSocket testing
 */
export const measureConnectionTime = async (connectionFn: () => Promise<void>): Promise<number> => {
  const start = performance.now();
  await connectionFn();
  return performance.now() - start;
};

export const measureMessageLatency = (sendTime: number): number => {
  return performance.now() - sendTime;
};

/**
 * Advanced WebSocket test utilities
 */
export class AdvancedWebSocketTester {
  private connections: TestWebSocket[] = [];
  private messageLog: { connection: number; message: string; timestamp: number }[] = [];
  
  createConnection(url: string): TestWebSocket {
    const connection = new TestWebSocket(url);
    this.connections.push(connection);
    return connection;
  }
  
  broadcastMessage(message: string): void {
    this.connections.forEach((connection, index) => {
      if (connection.readyState === 1) {
        connection.simulateMessage(message);
        this.messageLog.push({
          connection: index,
          message,
          timestamp: Date.now()
        });
      }
    });
  }
  
  getMessageLog(): { connection: number; message: string; timestamp: number }[] {
    return [...this.messageLog];
  }
  
  closeAllConnections(): void {
    this.connections.forEach(connection => {
      if (connection.readyState === 1) {
        connection.close();
      }
    });
  }
  
  getActiveConnections(): number {
    return this.connections.filter(conn => conn.readyState === 1).length;
  }
  
  clearLog(): void {
    this.messageLog = [];
  }
}