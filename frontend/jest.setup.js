import 'whatwg-fetch';
import '@testing-library/jest-dom';
import fetchMock from 'jest-fetch-mock';
import React from 'react';

fetchMock.enableMocks();

// Mock environment variables
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';

// Mock scrollIntoView
window.HTMLElement.prototype.scrollIntoView = jest.fn();

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

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
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

// Mock the WebSocketProvider context
jest.mock('@/providers/WebSocketProvider', () => ({
  WebSocketProvider: ({ children }) => children,
  WebSocketContext: React.createContext(null),
  useWebSocketContext: () => ({
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
  })
}));