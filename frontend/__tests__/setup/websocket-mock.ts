// WebSocket Mock Setup for Frontend Tests
// Provides stable, deterministic WebSocket behavior for testing

import { EventEmitter } from 'events';

export class MockWebSocket extends EventEmitter {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  binaryType: string = 'blob';
  
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  private connectTimer: NodeJS.Timeout | null = null;
  private messageQueue: any[] = [];
  private isConnected: boolean = false;

  constructor(url: string, protocols?: string | string[]) {
    super();
    this.url = url;
    
    // Simulate async connection with controlled timing
    this.connectTimer = setTimeout(() => {
      this.simulateOpen();
    }, 10); // Fast but async
  }

  private simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.isConnected = true;
    
    const event = new Event('open');
    this.onopen?.(event);
    this.emit('open', event);
    
    // Process any queued messages
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      this.processMessage(message);
    }
  }

  send(data: string | ArrayBuffer | Blob) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    
    // Echo back for testing
    setTimeout(() => {
      if (this.isConnected) {
        const messageEvent = new MessageEvent('message', { data });
        this.onmessage?.(messageEvent);
        this.emit('message', messageEvent);
      }
    }, 5);
  }

  close(code?: number, reason?: string) {
    if (this.connectTimer) {
      clearTimeout(this.connectTimer);
      this.connectTimer = null;
    }
    
    this.readyState = MockWebSocket.CLOSING;
    this.isConnected = false;
    
    setTimeout(() => {
      this.readyState = MockWebSocket.CLOSED;
      const event = new CloseEvent('close', { code, reason });
      this.onclose?.(event);
      this.emit('close', event);
    }, 5);
  }

  // Test helper methods
  simulateMessage(data: any) {
    if (this.readyState === MockWebSocket.OPEN) {
      this.processMessage(data);
    } else {
      this.messageQueue.push(data);
    }
  }

  private processMessage(data: any) {
    const messageData = typeof data === 'string' ? data : JSON.stringify(data);
    const event = new MessageEvent('message', { data: messageData });
    this.onmessage?.(event);
    this.emit('message', event);
  }

  simulateError(error?: any) {
    const event = new Event('error');
    this.onerror?.(event);
    this.emit('error', event);
  }

  simulateReconnect() {
    this.close(1006, 'Connection lost');
    setTimeout(() => {
      this.readyState = MockWebSocket.CONNECTING;
      setTimeout(() => {
        this.simulateOpen();
      }, 10);
    }, 20);
  }
}

// Global WebSocket mock installer
export function installWebSocketMock() {
  (global as any).WebSocket = MockWebSocket;
}

// Test helper to wait for WebSocket connection
export function waitForWebSocketConnection(timeout = 100): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, timeout);
  });
}

// Mock WebSocket provider for React components
// Note: This component is defined in test-utils/providers.tsx
// since this file is .ts and cannot contain JSX