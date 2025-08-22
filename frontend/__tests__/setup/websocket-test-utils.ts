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

  constructor(url: string) {
    super();
    this.url = url;
    this.readyState = this.CONNECTING;
  }

  send(data: string | ArrayBuffer | Blob): void {
    if (this.readyState !== this.OPEN) {
      throw new Error('WebSocket is not open');
    }
  }

  close(code?: number, reason?: string): void {
    if (this.readyState === this.CLOSED || this.readyState === this.CLOSING) {
      return;
    }
    this.readyState = this.CLOSING;
    setTimeout(() => {
      this.readyState = this.CLOSED;
      const event = new CloseEvent('close', { code, reason });
      this.onclose?.(event);
      this.dispatchEvent(event);
    }, 0);
  }
}

/**
 * Connection state manager for tracking WebSocket states
 */
export class ConnectionStateManager {
  private states: Map<string, number> = new Map();
  private stateHistory: Array<{ url: string; state: number; timestamp: number }> = [];

  setState(url: string, state: number): void {
    this.states.set(url, state);
    this.stateHistory.push({ url, state, timestamp: Date.now() });
  }

  getState(url: string): number | undefined {
    return this.states.get(url);
  }

  getHistory(): Array<{ url: string; state: number; timestamp: number }> {
    return [...this.stateHistory];
  }

  clear(): void {
    this.states.clear();
    this.stateHistory = [];
  }
}

/**
 * Message buffer for tracking WebSocket messages
 */
export class MessageBuffer {
  private messages: Array<{ type: 'sent' | 'received'; data: any; timestamp: number }> = [];

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

  clear(): void {
    this.messages = [];
  }
}