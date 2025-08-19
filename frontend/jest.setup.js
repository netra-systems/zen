require('whatwg-fetch');
require('@testing-library/jest-dom');
const fetchMock = require('jest-fetch-mock');

// Mock Web APIs that MSW needs in Node.js environment
global.BroadcastChannel = class BroadcastChannel {
  constructor(name) {
    this.name = name;
  }
  postMessage() {}
  close() {}
  addEventListener() {}
  removeEventListener() {}
};

global.TransformStream = class TransformStream {
  constructor() {
    this.readable = new ReadableStream();
    this.writable = new WritableStream();
  }
};

fetchMock.enableMocks();

// Add TextEncoder/TextDecoder polyfills for MSW
if (typeof global.TextEncoder === 'undefined') {
  const { TextEncoder, TextDecoder } = require('util');
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}

// Add BroadcastChannel polyfill for MSW
if (typeof global.BroadcastChannel === 'undefined') {
  global.BroadcastChannel = class BroadcastChannel {
    constructor(name) {
      this.name = name;
    }
    postMessage() {}
    addEventListener() {}
    removeEventListener() {}
    close() {}
  };
}

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

// Enhanced WebSocket Mock - Use the comprehensive version from mocks (conditional)
try {
  const { installWebSocketMock } = require('./__tests__/mocks/websocket-mocks');
  // Install the enhanced WebSocket mock globally
  installWebSocketMock();
} catch (error) {
  // Fallback to simple WebSocket mock if enhanced version fails
  class SimpleWebSocket {
    constructor(url) {
      this.url = url;
      this.readyState = 1; // OPEN
      this.send = jest.fn();
      this.close = jest.fn();
      this.addEventListener = jest.fn();
      this.removeEventListener = jest.fn();
    }
  }
  SimpleWebSocket.CONNECTING = 0;
  SimpleWebSocket.OPEN = 1;
  SimpleWebSocket.CLOSING = 2;
  SimpleWebSocket.CLOSED = 3;
  global.WebSocket = SimpleWebSocket;
}

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

// Add StorageEvent polyfill for Node.js test environment
if (typeof global.StorageEvent === 'undefined') {
  global.StorageEvent = class StorageEvent extends Event {
    constructor(type, eventInitDict = {}) {
      super(type, eventInitDict);
      this.key = eventInitDict.key || null;
      this.newValue = eventInitDict.newValue || null;
      this.oldValue = eventInitDict.oldValue || null;
      this.storageArea = eventInitDict.storageArea || null;
      this.url = eventInitDict.url || (typeof window !== 'undefined' ? window.location.href : 'http://localhost:3000');
    }
  };
}

// Enhanced cookie management for tests
const mockCookieData = new Map();
Object.defineProperty(document, 'cookie', {
  get: () => {
    return Array.from(mockCookieData.entries())
      .map(([key, value]) => `${key}=${value}`)
      .join('; ');
  },
  set: (cookie) => {
    const [nameValue] = cookie.split(';');
    const [name, value] = nameValue.split('=');
    if (value === '' || cookie.includes('expires=Thu, 01 Jan 1970')) {
      mockCookieData.delete(name.trim());
    } else {
      mockCookieData.set(name.trim(), value?.trim() || '');
    }
  },
  configurable: true
});

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
       args[0].includes('WebSocket error occurred') ||
       args[0].includes('overlapping act() calls'))
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
  if (localStorage && localStorage.clear) localStorage.clear();
  if (sessionStorage && sessionStorage.clear) sessionStorage.clear();
  mockCookieData.clear();
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

// Optional MSW setup - only load if explicitly enabled via environment variable
if (process.env.ENABLE_MSW_MOCKS === 'true') {
  try {
    const { startMockServer, resetMockHandlers, stopMockServer } = require('./__tests__/mocks/api-mocks');

    // Start MSW server before all tests
    beforeAll(() => {
      startMockServer();
    });

    // Reset handlers after each test to ensure test isolation
    afterEach(() => {
      resetMockHandlers();
    });

    // Stop MSW server after all tests
    afterAll(() => {
      stopMockServer();
    });
  } catch (error) {
    console.warn('MSW mocks not available:', error.message);
  }
}

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