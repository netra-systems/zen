import '@testing-library/jest-dom';
import 'jest-websocket-mock';
import { TextEncoder, TextDecoder } from 'util';
import fetch from 'cross-fetch';

// Polyfills
global.TextEncoder = TextEncoder as any;
global.TextDecoder = TextDecoder as any;
global.fetch = fetch;

// Performance: Disable animations and transitions
if (typeof window !== 'undefined') {
  // Disable CSS animations
  const style = document.createElement('style');
  style.innerHTML = `
    *, *::before, *::after {
      animation-duration: 0s !important;
      animation-delay: 0s !important;
      transition-duration: 0s !important;
      transition-delay: 0s !important;
    }
  `;
  document.head.appendChild(style);
  
  // Mock IntersectionObserver for performance
  global.IntersectionObserver = class IntersectionObserver {
    root = null;
    rootMargin = '';
    thresholds = [];
    constructor() {}
    disconnect() {}
    observe() {}
    unobserve() {}
    takeRecords() {
      return [];
    }
  } as any;
  
  // Mock ResizeObserver for performance
  global.ResizeObserver = class ResizeObserver {
    constructor() {}
    disconnect() {}
    observe() {}
    unobserve() {}
  } as any;
}

// Fast fail for unhandled promises
process.on('unhandledRejection', (reason) => {
  console.error('Unhandled Promise Rejection:', reason);
  process.exit(1);
});

// Suppress specific console messages for cleaner output
const originalError = console.error;
const originalWarn = console.warn;
const originalLog = console.log;

console.error = (...args: any[]) => {
  // Filter out known noise
  if (
    args[0]?.includes?.('Not implemented: navigation') ||
    args[0]?.includes?.('Failed to fetch config and connect to WebSocket') ||
    args[0]?.includes?.('WebSocket connection error') ||
    args[0]?.includes?.('Error: Network request failed')
  ) {
    return;
  }
  originalError.call(console, ...args);
};

console.warn = (...args: any[]) => {
  // Filter out React warnings in tests
  if (
    args[0]?.includes?.('ReactDOM.render') ||
    args[0]?.includes?.('componentWillReceiveProps') ||
    args[0]?.includes?.('componentWillMount')
  ) {
    return;
  }
  originalWarn.call(console, ...args);
};

console.log = (...args: any[]) => {
  // Filter out verbose logs
  if (
    args[0]?.includes?.('Attempting dev login') ||
    args[0]?.includes?.('WebSocket connecting')
  ) {
    return;
  }
  originalLog.call(console, ...args);
};

// Mock localStorage with fast implementation
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (index: number) => {
      const keys = Object.keys(store);
      return keys[index] || null;
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

// Mock sessionStorage
Object.defineProperty(window, 'sessionStorage', {
  value: localStorageMock,
  writable: true,
});

// Fast mock for window.location
delete (window as any).location;
(window as any).location = {
  href: 'http://localhost/',
  origin: 'http://localhost',
  protocol: 'http:',
  host: 'localhost',
  hostname: 'localhost',
  port: '',
  pathname: '/',
  search: '',
  hash: '',
  assign: jest.fn(),
  replace: jest.fn(),
  reload: jest.fn(),
};

// Mock window.matchMedia for responsive tests
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock crypto.randomUUID for consistent test IDs
if (!global.crypto) {
  global.crypto = {} as any;
}
global.crypto.randomUUID = (() => {
  return `test-uuid-${Math.random().toString(36).substr(2, 9)}`;
}) as any;

// Set default test environment variables
process.env.NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
process.env.NEXT_PUBLIC_WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

// Cleanup after each test for performance
afterEach(() => {
  jest.clearAllMocks();
  localStorageMock.clear();
});

// Global test timeout for faster failure detection
jest.setTimeout(10000);

// Mock apiClientWrapper to prevent connection attempts in tests
jest.mock('@/services/apiClientWrapper', () => ({
  apiClientWrapper: {
    request: jest.fn().mockRejectedValue(new Error('API mocked in tests')),
    retryRequest: jest.fn().mockRejectedValue(new Error('API mocked in tests')),
    checkConnection: jest.fn().mockResolvedValue(false),
    isConnected: false,
  }
}));