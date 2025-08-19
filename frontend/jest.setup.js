require('whatwg-fetch');
require('@testing-library/jest-dom');
const fetchMock = require('jest-fetch-mock');

fetchMock.enableMocks();

// Mock environment variables
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
process.env.NEXT_PUBLIC_AUTH_SERVICE_URL = 'http://localhost:8081';
process.env.NEXT_PUBLIC_AUTH_API_URL = 'http://localhost:8081';

// Mock scrollIntoView
window.HTMLElement.prototype.scrollIntoView = jest.fn();

// Mock requestAnimationFrame and cancelAnimationFrame
global.requestAnimationFrame = jest.fn(cb => setTimeout(cb, 0));
global.cancelAnimationFrame = jest.fn(id => clearTimeout(id));

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      refresh: jest.fn(),
      pathname: '/',
      query: {},
    };
  },
  usePathname() {
    return '/';
  },
  useSearchParams() {
    return new URLSearchParams();
  },
}));

// Enhanced WebSocket Mock with proper timing and state management
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    this.onopen = null;
    this.onclose = null;
    this.onerror = null;
    this.onmessage = null;
    this.send = jest.fn();
    this.close = jest.fn((code, reason) => {
      this.readyState = MockWebSocket.CLOSING;
      setTimeout(() => {
        this.readyState = MockWebSocket.CLOSED;
        if (this.onclose) {
          this.onclose(new CloseEvent('close', { code, reason }));
        }
      }, 0);
    });
    this.addEventListener = jest.fn((event, handler) => {
      if (event === 'open') this.onopen = handler;
      if (event === 'close') this.onclose = handler;
      if (event === 'error') this.onerror = handler;
      if (event === 'message') this.onmessage = handler;
    });
    this.removeEventListener = jest.fn();
    
    // Simulate async connection with proper state transition
    process.nextTick(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    });
  }

  // Helper method for tests to simulate messages
  simulateMessage(data) {
    if (this.onmessage && this.readyState === MockWebSocket.OPEN) {
      const messageData = typeof data === 'string' ? data : JSON.stringify(data);
      this.onmessage(new MessageEvent('message', { data: messageData }));
    }
  }
}

// Add static properties after class definition
MockWebSocket.CONNECTING = 0;
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSING = 2;
MockWebSocket.CLOSED = 3;

global.WebSocket = MockWebSocket;

// Mock localStorage with quota handling
const localStorageData = new Map();
const localStorageMock = {
  getItem: jest.fn((key) => localStorageData.get(key) || null),
  setItem: jest.fn((key, value) => {
    // Prevent quota exceeded errors by limiting storage
    if (localStorageData.size > 100) {
      localStorageData.clear();
    }
    localStorageData.set(key, String(value));
  }),
  removeItem: jest.fn((key) => localStorageData.delete(key)),
  clear: jest.fn(() => localStorageData.clear()),
  get length() { return localStorageData.size; },
  key: jest.fn((index) => Array.from(localStorageData.keys())[index] || null)
};
global.localStorage = localStorageMock;

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.sessionStorage = sessionStorageMock;

// Suppress console errors in tests
const originalError = console.error;
const originalWarn = console.warn;
beforeAll(() => {
  console.error = (...args) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Not implemented') ||
       args[0].includes('Warning:') ||
       args[0].includes('ReactDOMTestUtils') ||
       args[0].includes('Error parsing WebSocket message') ||
       args[0].includes('WebSocket error occurred'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
  
  console.warn = (...args) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning:')
    ) {
      return;
    }
    originalWarn.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
});

// Ensure Date.now works properly in tests
const originalDateNow = Date.now;
beforeEach(() => {
  Date.now = originalDateNow;
});

// Clean up after each test
afterEach(() => {
  jest.clearAllMocks();
  fetchMock.resetMocks();
  localStorage.clear();
  sessionStorage.clear();
  Date.now = originalDateNow;
});

// Mock the useWebSocket hook to avoid WebSocket connections in tests
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendMessage: jest.fn(),
    connect: jest.fn(),
    disconnect: jest.fn(),
    isConnected: true,
    connectionState: 'connected',
    error: null,
    lastMessage: null,
    reconnectAttempts: 0,
    messageQueue: [],
    status: 'OPEN',
    messages: [],
    ws: null,
    subscribe: jest.fn(),
    unsubscribe: jest.fn(),
  })
}));

// Setup auth service mocks for independent service
require('./__tests__/setup/auth-service-setup');

// Mock the WebSocketProvider context with factory function
jest.mock('@/providers/WebSocketProvider', () => {
  const React = require('react');
  const mockWebSocketContextValue = {
    sendMessage: jest.fn(),
    status: 'OPEN',
    messages: [],
    sendOptimisticMessage: jest.fn(() => ({
      id: 'mock-optimistic-id',
      content: 'mock-content',
      type: 'user',
      role: 'user',
      timestamp: Date.now(),
      tempId: 'mock-temp-id',
      optimisticTimestamp: Date.now(),
      contentHash: 'mock-hash',
      reconciliationStatus: 'pending',
      sequenceNumber: 1,
      retryCount: 0
    })),
    reconciliationStats: {
      totalOptimistic: 0,
      totalConfirmed: 0,
      totalFailed: 0,
      totalTimeout: 0,
      averageReconciliationTime: 0,
      currentPendingCount: 0
    }
  };
  const MockWebSocketContext = React.createContext(mockWebSocketContextValue);
  
  return {
    WebSocketProvider: ({ children }) => React.createElement(MockWebSocketContext.Provider, { value: mockWebSocketContextValue }, children),
    WebSocketContext: MockWebSocketContext,
    useWebSocketContext: () => mockWebSocketContextValue
  };
});

// Mock RawJsonView component for tests
jest.mock('./components/chat/RawJsonView', () => {
  const React = require('react');
  return {
    RawJsonView: ({ data }) => React.createElement('div', { 
      'data-testid': 'raw-json-view' 
    }, JSON.stringify(data, null, 2))
  };
});