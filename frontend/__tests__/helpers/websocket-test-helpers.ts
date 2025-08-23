/**
 * WebSocket test helpers for frontend tests.
 */

export class MockWebSocket {
  public url: string;
  public protocols: string | string[];
  public readyState: number;
  public bufferedAmount: number = 0;
  public binaryType: BinaryType = 'blob';
  public extensions: string = '';
  public protocol: string = '';
  public onopen: ((event: Event) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;
  public messageQueue: any[] = [];
  private eventListeners: Map<string, Set<EventListener>> = new Map();
  
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  constructor(url: string, protocols?: string | string[]) {
    this.url = url;
    this.protocols = protocols || [];
    this.readyState = MockWebSocket.CONNECTING;
    
    // Auto-simulate connection after creation
    setTimeout(() => {
      this.simulateOpen();
    }, 0);
  }

  send(data: string | ArrayBuffer | Blob) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    this.messageQueue.push(data);
  }

  close(code?: number, reason?: string) {
    if (this.readyState === MockWebSocket.CLOSED || this.readyState === MockWebSocket.CLOSING) {
      return;
    }
    this.readyState = MockWebSocket.CLOSING;
    setTimeout(() => {
      this.readyState = MockWebSocket.CLOSED;
      const closeEvent = new CloseEvent('close', { code: code || 1000, reason: reason || '' });
      this.onclose?.(closeEvent);
      this.dispatchEvent(closeEvent);
    }, 0);
  }

  addEventListener(type: string, listener: EventListener) {
    if (!this.eventListeners.has(type)) {
      this.eventListeners.set(type, new Set());
    }
    this.eventListeners.get(type)!.add(listener);
  }

  removeEventListener(type: string, listener: EventListener) {
    if (this.eventListeners.has(type)) {
      this.eventListeners.get(type)!.delete(listener);
    }
  }

  dispatchEvent(event: Event): boolean {
    if (this.eventListeners.has(event.type)) {
      this.eventListeners.get(event.type)!.forEach(listener => {
        try {
          listener(event);
        } catch (e) {
          // Ignore listener errors in tests
        }
      });
    }
    return true;
  }

  simulateOpen() {
    if (this.readyState === MockWebSocket.CONNECTING) {
      this.readyState = MockWebSocket.OPEN;
      const openEvent = new Event('open');
      this.onopen?.(openEvent);
      this.dispatchEvent(openEvent);
    }
  }

  simulateMessage(data: any) {
    if (this.readyState === MockWebSocket.OPEN) {
      const messageData = typeof data === 'string' ? data : JSON.stringify(data);
      const messageEvent = new MessageEvent('message', { data: messageData });
      this.onmessage?.(messageEvent);
      this.dispatchEvent(messageEvent);
    }
  }

  simulateError(error?: any) {
    const errorEvent = new ErrorEvent('error', { error: error || new Error('WebSocket error') });
    this.onerror?.(errorEvent);
    this.dispatchEvent(errorEvent);
  }

  getSentMessages() {
    return [...this.messageQueue];
  }
  
  clearMessageQueue() {
    this.messageQueue = [];
  }
}

export function createMockWebSocket() {
  return MockWebSocket;
}

export function setupWebSocketMocks() {
  global.WebSocket = MockWebSocket;
  return MockWebSocket;
}

export const mockWebSocketMessage = (type, data) => ({
  type,
  data,
  timestamp: Date.now()
});

export const mockWebSocketConnection = (connected = true) => {
  const mockConnection = {
    connected,
    reconnectAttempts: 0,
    lastError: null,
    readyState: connected ? WebSocket.OPEN : WebSocket.CLOSED,
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
    CONNECTING: WebSocket.CONNECTING,
    OPEN: WebSocket.OPEN,
    CLOSING: WebSocket.CLOSING,
    CLOSED: WebSocket.CLOSED
  };
  
  return mockConnection;
};
