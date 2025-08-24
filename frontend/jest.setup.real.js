// ============================================================================
// JEST SETUP FOR REAL SERVICE TESTING
// ============================================================================
// This file configures Jest to run frontend tests against real services
// (Docker containers, real LLM endpoints, actual backend services)
// ============================================================================

require('whatwg-fetch');
require('@testing-library/jest-dom');

// Add React for JSX components
global.React = require('react');

// ============================================================================
// ENVIRONMENT CONFIGURATION
// ============================================================================
const USE_REAL_SERVICES = process.env.USE_REAL_SERVICES === 'true';
const USE_DOCKER_SERVICES = process.env.USE_DOCKER_SERVICES === 'true';
const USE_REAL_LLM = process.env.USE_REAL_LLM === 'true';

// Service URLs - use Docker or local services
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL || 'http://localhost:8081';
const WEBSOCKET_URL = process.env.WEBSOCKET_URL || 'ws://localhost:8000';

// Configure environment variables
process.env.NEXT_PUBLIC_API_URL = BACKEND_URL;
process.env.NEXT_PUBLIC_WS_URL = WEBSOCKET_URL;
process.env.NEXT_PUBLIC_AUTH_SERVICE_URL = AUTH_SERVICE_URL;
process.env.NEXT_PUBLIC_AUTH_API_URL = AUTH_SERVICE_URL;
process.env.NODE_ENV = 'test';

console.log('Frontend Test Configuration:');
console.log('  USE_REAL_SERVICES:', USE_REAL_SERVICES);
console.log('  USE_DOCKER_SERVICES:', USE_DOCKER_SERVICES);
console.log('  USE_REAL_LLM:', USE_REAL_LLM);
console.log('  BACKEND_URL:', BACKEND_URL);
console.log('  AUTH_SERVICE_URL:', AUTH_SERVICE_URL);
console.log('  WEBSOCKET_URL:', WEBSOCKET_URL);

// ============================================================================
// GLOBAL POLYFILLS FOR NODE.JS ENVIRONMENT
// ============================================================================
global.BroadcastChannel = class BroadcastChannel {
  constructor(name) {
    this.name = name;
  }
  postMessage() {}
  close() {}
  addEventListener() {}
  removeEventListener() {}
  dispatchEvent() { return true; }
};

global.TransformStream = class TransformStream {
  constructor() {
    this.readable = new ReadableStream();
    this.writable = new WritableStream();
  }
};

// Add TextEncoder/TextDecoder polyfills
if (typeof global.TextEncoder === 'undefined') {
  const { TextEncoder, TextDecoder } = require('util');
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}

// Add StorageEvent polyfill
if (typeof global.StorageEvent === 'undefined') {
  global.StorageEvent = class StorageEvent extends Event {
    constructor(type, eventInitDict = {}) {
      super(type, eventInitDict);
      this.key = eventInitDict.key || null;
      this.newValue = eventInitDict.newValue || null;
      this.oldValue = eventInitDict.oldValue || null;
      this.storageArea = eventInitDict.storageArea || null;
      this.url = eventInitDict.url || 'http://localhost:3000';
    }
  };
}

// ============================================================================
// JSDOM API MOCKS (Still needed for DOM-related features)
// ============================================================================
Object.defineProperty(window, 'scrollTo', { value: jest.fn(), writable: true });
Object.defineProperty(window, 'scrollBy', { value: jest.fn(), writable: true });
Object.defineProperty(window, 'scroll', { value: jest.fn(), writable: true });
Object.defineProperty(window, 'scrollX', { value: 0, writable: true });
Object.defineProperty(window, 'scrollY', { value: 0, writable: true });

window.HTMLElement.prototype.scrollIntoView = jest.fn();
window.HTMLElement.prototype.scrollIntoViewIfNeeded = jest.fn();

if (typeof window !== 'undefined' && window.HTMLFormElement) {
  window.HTMLFormElement.prototype.requestSubmit = jest.fn();
}

global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

global.requestAnimationFrame = jest.fn(cb => setTimeout(cb, 0));
global.cancelAnimationFrame = jest.fn(id => clearTimeout(id));

// ============================================================================
// STORAGE (Real implementation)
// ============================================================================
const localStorageData = new Map();
const sessionStorageData = new Map();

const localStorageMock = {
  getItem: jest.fn((key) => localStorageData.get(key) || null),
  setItem: jest.fn((key, value) => localStorageData.set(key, String(value))),
  removeItem: jest.fn((key) => localStorageData.delete(key)),
  clear: jest.fn(() => localStorageData.clear()),
  get length() { return localStorageData.size; },
  key: jest.fn((index) => Array.from(localStorageData.keys())[index] || null)
};

const sessionStorageMock = {
  getItem: jest.fn((key) => sessionStorageData.get(key) || null),
  setItem: jest.fn((key, value) => sessionStorageData.set(key, String(value))),
  removeItem: jest.fn((key) => sessionStorageData.delete(key)),
  clear: jest.fn(() => sessionStorageData.clear()),
  get length() { return sessionStorageData.size; },
  key: jest.fn((index) => Array.from(sessionStorageData.keys())[index] || null)
};

global.localStorage = localStorageMock;
global.sessionStorage = sessionStorageMock;

// ============================================================================
// REAL SERVICE CONFIGURATION
// ============================================================================
if (USE_REAL_SERVICES) {
  console.log('Configuring tests for REAL SERVICES');
  
  // Don't mock fetch - use real HTTP calls
  // Don't mock WebSocket - use real WebSocket connections
  
  // Configure axios/fetch to use real endpoints
  if (typeof global.fetch !== 'undefined') {
    const originalFetch = global.fetch;
    global.fetch = async (url, options = {}) => {
      // Ensure URLs are absolute
      if (typeof url === 'string' && url.startsWith('/')) {
        url = `${BACKEND_URL}${url}`;
      }
      
      // Add auth headers if token exists
      const token = localStorageData.get('token') || localStorageData.get('auth_token');
      if (token) {
        options.headers = {
          ...options.headers,
          'Authorization': `Bearer ${token}`
        };
      }
      
      return originalFetch(url, options);
    };
  }
  
  // Use real WebSocket
  // Node.js doesn't have WebSocket by default, so we need to add it
  if (typeof global.WebSocket === 'undefined') {
    const WebSocket = require('ws');
    global.WebSocket = WebSocket;
  }
  
} else {
  // Fall back to mocked services for unit tests
  console.log('Using MOCKED services for unit testing');
  
  // Enable fetch mocking
  const fetchMock = require('jest-fetch-mock');
  fetchMock.enableMocks();
  
  // Mock WebSocket
  class MockWebSocket {
    constructor(url, protocols) {
      this.url = url;
      this.protocols = protocols || [];
      this.readyState = MockWebSocket.CONNECTING;
      this.onopen = null;
      this.onclose = null;
      this.onerror = null;
      this.onmessage = null;
      this.send = jest.fn();
      this.close = jest.fn();
      this.addEventListener = jest.fn();
      this.removeEventListener = jest.fn();
      this.dispatchEvent = jest.fn();
      
      // Simulate connection
      setTimeout(() => {
        if (this.readyState === MockWebSocket.CONNECTING) {
          this.readyState = MockWebSocket.OPEN;
          if (this.onopen) this.onopen(new Event('open'));
        }
      }, 10);
    }
  }
  
  MockWebSocket.CONNECTING = 0;
  MockWebSocket.OPEN = 1;
  MockWebSocket.CLOSING = 2;
  MockWebSocket.CLOSED = 3;
  
  global.WebSocket = MockWebSocket;
}

// ============================================================================
// CONDITIONAL MOCKING - Only mock if not using real services
// ============================================================================
if (!USE_REAL_SERVICES) {
  // Mock Next.js navigation
  jest.mock('next/navigation', () => ({
    useRouter() {
      return {
        push: jest.fn(),
        replace: jest.fn(),
        prefetch: jest.fn(),
        back: jest.fn(),
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
  
  // Mock auth service
  jest.mock('@/auth/service', () => ({
    authService: {
      getAuthConfig: jest.fn().mockResolvedValue({
        development_mode: true,
        google_client_id: 'mock-google-client-id',
      }),
      handleDevLogin: jest.fn().mockResolvedValue({
        access_token: 'mock-token',
        token_type: 'Bearer'
      }),
      getToken: jest.fn().mockReturnValue('mock-token'),
      getAuthHeaders: jest.fn().mockReturnValue({ Authorization: 'Bearer mock-token' }),
      removeToken: jest.fn(),
    }
  }));
}

// ============================================================================
// TEST UTILITIES
// ============================================================================
global.waitForBackend = async (maxAttempts = 30, delayMs = 1000) => {
  if (!USE_REAL_SERVICES) return true;
  
  console.log('Waiting for backend services to be ready...');
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const response = await fetch(`${BACKEND_URL}/health`);
      if (response.ok) {
        console.log('Backend is ready!');
        return true;
      }
    } catch (error) {
      // Service not ready yet
    }
    await new Promise(resolve => setTimeout(resolve, delayMs));
  }
  throw new Error('Backend services did not become ready in time');
};

global.waitForAuthService = async (maxAttempts = 30, delayMs = 1000) => {
  if (!USE_REAL_SERVICES) return true;
  
  console.log('Waiting for auth service to be ready...');
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const response = await fetch(`${AUTH_SERVICE_URL}/health`);
      if (response.ok) {
        console.log('Auth service is ready!');
        return true;
      }
    } catch (error) {
      // Service not ready yet
    }
    await new Promise(resolve => setTimeout(resolve, delayMs));
  }
  throw new Error('Auth service did not become ready in time');
};

global.authenticateTestUser = async () => {
  if (!USE_REAL_SERVICES) {
    // Mock authentication
    localStorageData.set('token', 'mock-test-token');
    localStorageData.set('auth_token', 'mock-test-token');
    return { token: 'mock-test-token', user: { id: 'test-user', email: 'test@example.com' } };
  }
  
  // Real authentication
  try {
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/dev/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'test@example.com',
        full_name: 'Test User'
      })
    });
    
    if (!response.ok) {
      throw new Error(`Auth failed: ${response.statusText}`);
    }
    
    const data = await response.json();
    localStorageData.set('token', data.access_token);
    localStorageData.set('auth_token', data.access_token);
    
    return {
      token: data.access_token,
      user: { id: 'test-user', email: 'test@example.com' }
    };
  } catch (error) {
    console.error('Authentication failed:', error);
    throw error;
  }
};

// ============================================================================
// CONSOLE SUPPRESSION (Optional)
// ============================================================================
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
  // Suppress specific warnings in test output
  console.error = (...args) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Not implemented') ||
       args[0].includes('ReactDOMTestUtils'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
  
  console.warn = (...args) => {
    if (typeof args[0] === 'string' && args[0].includes('Warning:')) {
      return;
    }
    originalWarn.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
});

// ============================================================================
// TEST CLEANUP
// ============================================================================
beforeEach(() => {
  // Clear data before each test
  localStorageData.clear();
  sessionStorageData.clear();
});

afterEach(() => {
  jest.clearAllMocks();
  
  // Reset window properties
  if (typeof window !== 'undefined') {
    Object.defineProperty(window, 'scrollX', { value: 0, writable: true });
    Object.defineProperty(window, 'scrollY', { value: 0, writable: true });
  }
});

// ============================================================================
// GLOBAL TEST HOOKS
// ============================================================================
if (USE_REAL_SERVICES) {
  // Wait for services before running tests
  beforeAll(async () => {
    await global.waitForBackend();
    await global.waitForAuthService();
  }, 60000); // 60 second timeout
}