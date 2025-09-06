/**
 * Enhanced Jest Setup with Comprehensive Mocking
 * Ensures all tests have proper mocks and environment
 */

// Set up test environment
global.IS_REACT_ACT_ENVIRONMENT = true;
process.env.NODE_ENV = 'test';
process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000';
process.env.NEXT_PUBLIC_WS_BASE_URL = 'ws://localhost:8000';

// Mock fetch globally
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
    headers: new Headers(),
    status: 200,
    statusText: 'OK',
  })
);

// Mock WebSocket globally
class MockWebSocket {
  constructor(url, protocols) {
    this.url = url;
    this.protocols = protocols;
    this.readyState = MockWebSocket.CONNECTING;
    this.onopen = null;
    this.onclose = null;
    this.onerror = null;
    this.onmessage = null;
    
    // Simulate connection after a small delay
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }
  
  send(data) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Mock sending data
    return true;
  }
  
  close(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSING;
    setTimeout(() => {
      this.readyState = MockWebSocket.CLOSED;
      if (this.onclose) {
        this.onclose(new CloseEvent('close', { code, reason }));
      }
    }, 0);
  }
  
  addEventListener(type, listener) {
    this[`on${type}`] = listener;
  }
  
  removeEventListener(type, listener) {
    if (this[`on${type}`] === listener) {
      this[`on${type}`] = null;
    }
  }
}

MockWebSocket.CONNECTING = 0;
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSING = 2;
MockWebSocket.CLOSED = 3;

global.WebSocket = MockWebSocket;

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn((key) => null),
  setItem: jest.fn((key, value) => {}),
  removeItem: jest.fn((key) => {}),
  clear: jest.fn(),
  length: 0,
  key: jest.fn((index) => null),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn((key) => null),
  setItem: jest.fn((key, value) => {}),
  removeItem: jest.fn((key) => {}),
  clear: jest.fn(),
  length: 0,
  key: jest.fn((index) => null),
};
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
  writable: true,
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  observe() { return null; }
  unobserve() { return null; }
  disconnect() { return null; }
};

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  observe() { return null; }
  unobserve() { return null; }
  disconnect() { return null; }
};

// Mock requestAnimationFrame
global.requestAnimationFrame = (cb) => setTimeout(cb, 0);
global.cancelAnimationFrame = (id) => clearTimeout(id);

// Mock console methods to reduce noise
const originalConsole = {
  log: console.log,
  error: console.error,
  warn: console.warn,
  info: console.info,
  debug: console.debug,
};

// Suppress certain console outputs during tests
console.error = (...args) => {
  const message = args[0]?.toString() || '';
  // Suppress known React warnings
  if (
    message.includes('Warning: ReactDOM.render') ||
    message.includes('Warning: useLayoutEffect') ||
    message.includes('Warning: An update to') ||
    message.includes('not wrapped in act')
  ) {
    return;
  }
  originalConsole.error(...args);
};

console.warn = (...args) => {
  const message = args[0]?.toString() || '';
  // Suppress known warnings
  if (
    message.includes('Warning:') ||
    message.includes('deprecated')
  ) {
    return;
  }
  originalConsole.warn(...args);
};

// Mock common services
jest.mock('@/services/webSocketService', () => ({
  webSocketService: {
    connect: jest.fn(),
    disconnect: jest.fn(),
    send: jest.fn(),
    sendMessage: jest.fn(),
    onStatusChange: null,
    onMessage: null,
    getStatus: jest.fn(() => 'CLOSED'),
    getState: jest.fn(() => 'disconnected'),
    isConnected: jest.fn(() => false),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  }
}));

jest.mock('@/services/authService', () => ({
  authService: {
    login: jest.fn(() => Promise.resolve({ token: 'mock-token' })),
    logout: jest.fn(() => Promise.resolve()),
    getToken: jest.fn(() => 'mock-token'),
    isAuthenticated: jest.fn(() => true),
    refreshToken: jest.fn(() => Promise.resolve({ token: 'mock-refresh-token' })),
    validateToken: jest.fn(() => Promise.resolve(true)),
  }
}));

jest.mock('@/lib/api', () => ({
  api: {
    get: jest.fn(() => Promise.resolve({ data: {} })),
    post: jest.fn(() => Promise.resolve({ data: {} })),
    put: jest.fn(() => Promise.resolve({ data: {} })),
    delete: jest.fn(() => Promise.resolve({ data: {} })),
    patch: jest.fn(() => Promise.resolve({ data: {} })),
  },
  fetchWithAuth: jest.fn(() => Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
  })),
}));

jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
    log: jest.fn(),
  }
}));

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

// Mock Next.js dynamic imports
jest.mock('next/dynamic', () => ({
  __esModule: true,
  default: (func) => {
    const Component = func();
    if (Component instanceof Promise) {
      Component.then((mod) => mod.default || mod);
    }
    return Component;
  },
}));

// Increase default timeout for all tests
jest.setTimeout(10000);

// Clean up after each test
afterEach(() => {
  jest.clearAllMocks();
  jest.clearAllTimers();
  localStorageMock.clear();
  sessionStorageMock.clear();
});

// Export for use in tests
module.exports = {
  originalConsole,
  localStorageMock,
  sessionStorageMock,
  MockWebSocket,
};