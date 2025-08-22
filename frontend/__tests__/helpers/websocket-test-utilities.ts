/**
 * WebSocket Test Utilities
 * Utilities for testing WebSocket functionality
 */

export interface WebSocketConnectionLifecycle {
  state: 'connecting' | 'connected' | 'disconnected' | 'error';
  connectionTime?: number;
  error?: Error;
}

export function measurePerformance<T>(fn: () => T | Promise<T>): Promise<{ result: T; duration: number }> {
  return new Promise(async (resolve) => {
    const start = performance.now();
    const result = await fn();
    const end = performance.now();
    resolve({ result, duration: end - start });
  });
}

export function createMockWebSocketConnection() {
  const connection = {
    readyState: WebSocket.CONNECTING,
    url: 'ws://localhost:8000/ws',
    protocol: '',
    extensions: '',
    bufferedAmount: 0,
    binaryType: 'blob' as BinaryType,
    send: jest.fn(),
    close: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
    onopen: null,
    onclose: null,
    onerror: null,
    onmessage: null,
    CONNECTING: WebSocket.CONNECTING,
    OPEN: WebSocket.OPEN,
    CLOSING: WebSocket.CLOSING,
    CLOSED: WebSocket.CLOSED,
  };

  return connection as WebSocket;
}

export function simulateWebSocketEvent(ws: WebSocket, eventType: string, data?: any) {
  const event = new Event(eventType);
  if (data && eventType === 'message') {
    (event as any).data = data;
  }
  
  switch (eventType) {
    case 'open':
      (ws as any).readyState = WebSocket.OPEN;
      if (ws.onopen) ws.onopen(event);
      break;
    case 'close':
      (ws as any).readyState = WebSocket.CLOSED;
      if (ws.onclose) ws.onclose(event as CloseEvent);
      break;
    case 'error':
      if (ws.onerror) ws.onerror(event);
      break;
    case 'message':
      if (ws.onmessage) ws.onmessage(event as MessageEvent);
      break;
  }
}

export function waitForWebSocketState(ws: WebSocket, state: number, timeout = 5000): Promise<void> {
  return new Promise((resolve, reject) => {
    if (ws.readyState === state) {
      resolve();
      return;
    }

    const timeoutId = setTimeout(() => {
      reject(new Error(`WebSocket did not reach state ${state} within ${timeout}ms`));
    }, timeout);

    const checkState = () => {
      if (ws.readyState === state) {
        clearTimeout(timeoutId);
        resolve();
      } else {
        setTimeout(checkState, 10);
      }
    };

    checkState();
  });
}