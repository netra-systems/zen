/**
 * Mock WebSocket Service for Tests
 * Provides comprehensive mocking of WebSocket service functionality
 */

import { WebSocketStatus, WebSocketState, WebSocketServiceError } from '../../types/domains/websocket';

// WebSocketStatus, WebSocketState, and WebSocketServiceError types imported from domains/websocket.ts
// Re-export for mock compatibility
export type { WebSocketStatus, WebSocketState, WebSocketServiceError } from '../../types/domains/websocket';

class MockWebSocketService {
  private _status: WebSocketStatus = 'CLOSED';
  private _state: WebSocketState = 'disconnected';
  private _url: string | null = null;
  private _messageQueue: any[] = [];
  private _connectionAttempts = 0;
  private _listeners: Map<string, Function[]> = new Map();
  private _connected = false;
  
  // Mock properties and methods
  public onStatusChange: ((status: WebSocketStatus) => void) | null = null;
  public onStateChange: ((state: WebSocketState) => void) | null = null;
  public onMessage: ((message: any) => void) | null = null;
  
  // Jest mock functions for compatibility
  public connect = jest.fn((url: string) => {
    this._url = url;
    this._status = 'CONNECTING';
    this._state = 'connecting';
    this._connectionAttempts++;
    
    // Notify listeners immediately for sync behavior in tests
    this.onStatusChange?.('CONNECTING');
    this.onStateChange?.('connecting');
    
    // Simulate connection process
    setTimeout(() => {
      this._status = 'OPEN';
      this._state = 'connected';
      this._connected = true;
      
      // Notify listeners
      this.onStatusChange?.('OPEN');
      this.onStateChange?.('connected');
      this._notifyListeners('open', { url });
    }, 10);
  });
  
  public disconnect = jest.fn(() => {
    this._status = 'CLOSING';
    this._state = 'disconnected';
    
    setTimeout(() => {
      this._status = 'CLOSED';
      this._connected = false;
      this._url = null;
      
      // Notify listeners
      this.onStatusChange?.('CLOSED');
      this.onStateChange?.('disconnected');
      this._notifyListeners('close', { code: 1000, reason: 'Normal closure' });
    }, 10);
  });
  
  public sendMessage = jest.fn((message: any) => {
    if (this._status === 'OPEN') {
      this._messageQueue.push(message);
      this._notifyListeners('message_sent', message);
    } else {
      // Queue message for later sending
      this._messageQueue.push(message);
    }
  });
  
  public send = jest.fn((message: any) => this.sendMessage(message));
  
  public getStatus = jest.fn((): WebSocketStatus => this._status);
  
  public getState = jest.fn((): WebSocketState => this._state);
  
  public isConnected = jest.fn((): boolean => this._connected && this._status === 'OPEN');
  
  public getUrl = jest.fn((): string | null => this._url);
  
  public getConnectionAttempts = jest.fn((): number => this._connectionAttempts);
  
  public getMessageQueue = jest.fn((): any[] => [...this._messageQueue]);
  
  public clearMessageQueue = jest.fn(() => {
    this._messageQueue = [];
  });
  
  // Event listener management
  public addEventListener = jest.fn((event: string, listener: Function) => {
    if (!this._listeners.has(event)) {
      this._listeners.set(event, []);
    }
    this._listeners.get(event)!.push(listener);
  });
  
  public removeEventListener = jest.fn((event: string, listener: Function) => {
    if (this._listeners.has(event)) {
      const listeners = this._listeners.get(event)!;
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  });
  
  private _notifyListeners(event: string, data?: any): void {
    if (this._listeners.has(event)) {
      this._listeners.get(event)!.forEach(listener => {
        try {
          listener(data);
        } catch (e) {
          // Ignore listener errors in tests
        }
      });
    }
  }
  
  // Test utilities
  public simulateMessage = jest.fn((message: any) => {
    this.onMessage?.(message);
    this._notifyListeners('message', message);
  });
  
  public simulateError = jest.fn((error: WebSocketServiceError) => {
    this._notifyListeners('error', error);
  });
  
  public simulateReconnect = jest.fn(() => {
    if (this._url) {
      this._state = 'reconnecting';
      this.onStateChange?.('reconnecting');
      
      setTimeout(() => {
        this.connect(this._url!);
      }, 100);
    }
  });
  
  // Reset for testing
  public reset = jest.fn(() => {
    this._status = 'CLOSED';
    this._state = 'disconnected';
    this._url = null;
    this._messageQueue = [];
    this._connectionAttempts = 0;
    this._connected = false;
    this._listeners.clear();
    this.onStatusChange = null;
    this.onStateChange = null;
    this.onMessage = null;
    
    // Reset all mock functions
    jest.clearAllMocks();
  });
}

// Export singleton instance for consistent behavior across tests
export const webSocketService = new MockWebSocketService();

// Export class for creating new instances if needed
export { MockWebSocketService };