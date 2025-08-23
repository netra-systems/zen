/**
 * WebSocket Test Utilities
 * Core utilities for testing WebSocket functionality
 */

/**
 * Test WebSocket implementation for mocking
 */
export class TestWebSocket extends EventTarget {
  url: string;
  readyState: number;
  CONNECTING = 0;
  OPEN = 1;
  CLOSING = 2;
  CLOSED = 3;
  
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  
  private sentMessages: string[] = [];
  private connected: boolean = false;

  constructor(url: string) {
    super();
    this.url = url;
    this.readyState = this.CONNECTING;
  }

  connect(): void {
    setTimeout(() => {
      this.readyState = this.OPEN;
      this.connected = true;
      const event = new Event('open');
      this.onopen?.(event);
      this.dispatchEvent(event);
    }, 0);
  }

  send(data: string | ArrayBuffer | Blob): void {
    if (this.readyState !== this.OPEN) {
      throw new Error('WebSocket is not open');
    }
    const messageData = typeof data === 'string' ? data : data.toString();
    this.sentMessages.push(messageData);
  }

  close(code?: number, reason?: string): void {
    if (this.readyState === this.CLOSED || this.readyState === this.CLOSING) {
      return;
    }
    this.readyState = this.CLOSING;
    this.connected = false;
    setTimeout(() => {
      this.readyState = this.CLOSED;
      const event = new CloseEvent('close', { code, reason });
      this.onclose?.(event);
      this.dispatchEvent(event);
    }, 0);
  }

  simulateMessage(data: any): void {
    if (this.readyState === this.OPEN) {
      const messageData = typeof data === 'string' ? data : JSON.stringify(data);
      const event = new MessageEvent('message', { data: messageData });
      this.onmessage?.(event);
      this.dispatchEvent(event);
    }
  }

  simulateError(error?: any): void {
    const event = new ErrorEvent('error', { error });
    this.onerror?.(event);
    this.dispatchEvent(event);
  }

  simulateReconnect(): void {
    if (this.readyState === this.CLOSED) {
      this.readyState = this.CONNECTING;
      this.connect();
    }
  }

  getSentMessages(): string[] {
    return [...this.sentMessages];
  }

  isConnected(): boolean {
    return this.connected;
  }
}

/**
 * Connection state manager for tracking WebSocket states
 */
export class ConnectionStateManager {
  private currentState: string = 'disconnected';
  private stateHistory: Array<{ state: string; timestamp: number }> = [];

  setState(state: string): void {
    this.currentState = state;
    this.stateHistory.push({ state, timestamp: Date.now() });
  }

  getState(): string {
    return this.currentState;
  }

  getHistory(): Array<{ state: string; timestamp: number }> {
    return [...this.stateHistory];
  }

  clear(): void {
    this.currentState = 'disconnected';
    this.stateHistory = [];
  }

  clearHistory(): void {
    this.stateHistory = [];
  }
}

/**
 * Message buffer for tracking WebSocket messages
 */
export class MessageBuffer {
  private messages: Array<{ type: 'sent' | 'received'; data: any; timestamp: number }> = [];

  add(data: any): void {
    this.addReceived(data);
  }

  addSent(data: any): void {
    this.messages.push({ type: 'sent', data, timestamp: Date.now() });
  }

  addReceived(data: any): void {
    this.messages.push({ type: 'received', data, timestamp: Date.now() });
  }

  getMessages(): Array<{ type: 'sent' | 'received'; data: any; timestamp: number }> {
    return [...this.messages];
  }

  getSentMessages(): any[] {
    return this.messages.filter(m => m.type === 'sent').map(m => m.data);
  }

  getReceivedMessages(): any[] {
    return this.messages.filter(m => m.type === 'received').map(m => m.data);
  }

  flush(): string[] {
    const received = this.getReceivedMessages();
    this.clear();
    return received;
  }

  clear(): void {
    this.messages = [];
  }
}

/**
 * Measure connection timing
 */
export function measureConnectionTime(): Promise<number> {
  return new Promise((resolve) => {
    const start = performance.now();
    setTimeout(() => {
      const end = performance.now();
      resolve(end - start);
    }, 10);
  });
}

/**
 * Create WebSocket mock for testing
 */
export function createWebSocketMock() {
  return {
    send: jest.fn(),
    close: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    readyState: WebSocket.OPEN,
    url: 'ws://localhost:8000/ws',
    protocol: '',
    extensions: '',
    bufferedAmount: 0,
    binaryType: 'blob',
    onopen: null,
    onclose: null,
    onerror: null,
    onmessage: null,
    dispatchEvent: jest.fn(),
    CONNECTING: WebSocket.CONNECTING,
    OPEN: WebSocket.OPEN,
    CLOSING: WebSocket.CLOSING,
    CLOSED: WebSocket.CLOSED,
  } as any;
}