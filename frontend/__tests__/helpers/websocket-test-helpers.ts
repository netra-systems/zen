/**
 * WebSocket test helpers for frontend tests.
 */

export class MockWebSocket {
  constructor(url, protocols) {
    this.url = url;
    this.protocols = protocols;
    this.readyState = WebSocket.CONNECTING;
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;
    this.messageQueue = [];
  }

  send(data) {
    this.messageQueue.push(data);
  }

  close(code, reason) {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose({ code, reason });
    }
  }

  simulateOpen() {
    this.readyState = WebSocket.OPEN;
    if (this.onopen) {
      this.onopen({});
    }
  }

  simulateMessage(data) {
    if (this.onmessage) {
      this.onmessage({ data });
    }
  }

  simulateError(error) {
    if (this.onerror) {
      this.onerror(error);
    }
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

export const mockWebSocketConnection = (connected = true) => ({
  connected,
  reconnectAttempts: 0,
  lastError: null,
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn()
});
