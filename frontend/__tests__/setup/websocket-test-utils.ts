// Centralized WebSocket test utilities
export function setupMockWebSocket() {
  // Create mock WebSocket instance if it doesn't exist
  if (!global.mockWebSocket) {
    global.mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      readyState: 1, // WebSocket.OPEN
      url: 'ws://localhost:8000/ws',
      binaryType: 'blob',
      onopen: null,
      onclose: null,
      onerror: null,
      onmessage: null,
      simulateMessage: jest.fn(),
      simulateError: jest.fn(),
      simulateReconnect: jest.fn()
    };
    
    // Mock WebSocket constructor
    global.WebSocket = jest.fn(() => global.mockWebSocket) as any;
  }
  
  return global.mockWebSocket;
}

export function resetMockWebSocket() {
  if (global.mockWebSocket) {
    global.mockWebSocket.readyState = 1;
    global.mockWebSocket.send.mockClear();
    global.mockWebSocket.close.mockClear();
    global.mockWebSocket.addEventListener.mockClear();
    global.mockWebSocket.removeEventListener.mockClear();
    global.mockWebSocket.simulateMessage.mockClear();
    global.mockWebSocket.simulateError.mockClear();
    global.mockWebSocket.simulateReconnect.mockClear();
  }
}

export function simulateWebSocketOpen() {
  if (global.mockWebSocket) {
    global.mockWebSocket.readyState = 1; // WebSocket.OPEN
    const openHandler = global.mockWebSocket.addEventListener.mock.calls
      .find((call: any[]) => call[0] === 'open')?.[1];
    if (openHandler) {
      openHandler(new Event('open'));
    }
    if (global.mockWebSocket.onopen) {
      global.mockWebSocket.onopen(new Event('open'));
    }
  }
}

export function simulateWebSocketMessage(data: any) {
  if (global.mockWebSocket) {
    const messageData = typeof data === 'string' ? data : JSON.stringify(data);
    const event = new MessageEvent('message', { data: messageData });
    
    const messageHandler = global.mockWebSocket.addEventListener.mock.calls
      .find((call: any[]) => call[0] === 'message')?.[1];
    if (messageHandler) {
      messageHandler(event);
    }
    if (global.mockWebSocket.onmessage) {
      global.mockWebSocket.onmessage(event);
    }
  }
}

export function simulateWebSocketClose(code = 1000, reason = 'Normal closure') {
  if (global.mockWebSocket) {
    global.mockWebSocket.readyState = 3; // WebSocket.CLOSED
    const event = new CloseEvent('close', { code, reason });
    
    const closeHandler = global.mockWebSocket.addEventListener.mock.calls
      .find((call: any[]) => call[0] === 'close')?.[1];
    if (closeHandler) {
      closeHandler(event);
    }
    if (global.mockWebSocket.onclose) {
      global.mockWebSocket.onclose(event);
    }
  }
}

export function simulateWebSocketError(error?: any) {
  if (global.mockWebSocket) {
    const event = new ErrorEvent('error', { error });
    
    const errorHandler = global.mockWebSocket.addEventListener.mock.calls
      .find((call: any[]) => call[0] === 'error')?.[1];
    if (errorHandler) {
      errorHandler(event);
    }
    if (global.mockWebSocket.onerror) {
      global.mockWebSocket.onerror(event);
    }
  }
}