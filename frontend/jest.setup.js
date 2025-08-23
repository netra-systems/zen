// ============================================================================
// COMPREHENSIVE JEST SETUP - UNIFIED TEST INFRASTRUCTURE
// ============================================================================
// This file provides complete mocking infrastructure for all frontend tests
// to achieve 100% pass rate with no real HTTP calls, WebSocket connections,
// or external dependencies.
// ============================================================================

require('whatwg-fetch');
require('@testing-library/jest-dom');
const fetchMock = require('jest-fetch-mock');

// ============================================================================
// GLOBAL POLYFILLS FOR NODE.JS ENVIRONMENT
// ============================================================================
// Add missing Web APIs that MSW and other libraries require
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

// Enable fetch mocking
fetchMock.enableMocks();

// ============================================================================
// ENVIRONMENT VARIABLES
// ============================================================================
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
process.env.NEXT_PUBLIC_AUTH_SERVICE_URL = 'http://localhost:8081';
process.env.NEXT_PUBLIC_AUTH_API_URL = 'http://localhost:8081';
process.env.NODE_ENV = 'test';

// ============================================================================
// JSDOM API MOCKS
// ============================================================================
// Mock scroll and animation APIs that JSDOM doesn't implement
Object.defineProperty(window, 'scrollTo', { value: jest.fn(), writable: true });
Object.defineProperty(window, 'scrollBy', { value: jest.fn(), writable: true });
Object.defineProperty(window, 'scroll', { value: jest.fn(), writable: true });
Object.defineProperty(window, 'scrollX', { value: 0, writable: true });
Object.defineProperty(window, 'scrollY', { value: 0, writable: true });
Object.defineProperty(window, 'pageXOffset', { value: 0, writable: true });
Object.defineProperty(window, 'pageYOffset', { value: 0, writable: true });

// Mock element scroll methods
window.HTMLElement.prototype.scrollIntoView = jest.fn();
window.HTMLElement.prototype.scrollIntoViewIfNeeded = jest.fn();

// Mock form methods
if (typeof window !== 'undefined' && window.HTMLFormElement) {
  window.HTMLFormElement.prototype.requestSubmit = jest.fn();
}

// Mock observers
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

// Mock animation frame
global.requestAnimationFrame = jest.fn(cb => setTimeout(cb, 0));
global.cancelAnimationFrame = jest.fn(id => clearTimeout(id));

// ============================================================================
// WEBSOCKET MOCKS
// ============================================================================
class MockWebSocket {
  constructor(url) {
    this.url = url + `-test-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    this.readyState = MockWebSocket.OPEN;
    this.send = jest.fn();
    this.close = jest.fn();
    this.addEventListener = jest.fn();
    this.removeEventListener = jest.fn();
    this.onopen = null;
    this.onclose = null;
    this.onerror = null;
    this.onmessage = null;
    
    // Simulate connection
    setTimeout(() => {
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 0);
  }
  
  simulateMessage(data) {
    const event = new MessageEvent('message', { 
      data: typeof data === 'string' ? data : JSON.stringify(data) 
    });
    if (this.onmessage) {
      this.onmessage(event);
    }
  }
  
  simulateError(error) {
    const event = new ErrorEvent('error', { error });
    if (this.onerror) {
      this.onerror(event);
    }
  }
}

MockWebSocket.CONNECTING = 0;
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSING = 2;
MockWebSocket.CLOSED = 3;

global.WebSocket = MockWebSocket;

// ============================================================================
// STORAGE MOCKS
// ============================================================================
const localStorageData = new Map();
const localStorageMock = {
  getItem: jest.fn((key) => localStorageData.get(key) || null),
  setItem: jest.fn((key, value) => {
    if (localStorageData.size > 100) localStorageData.clear();
    localStorageData.set(key, String(value));
  }),
  removeItem: jest.fn((key) => localStorageData.delete(key)),
  clear: jest.fn(() => localStorageData.clear()),
  get length() { return localStorageData.size; },
  key: jest.fn((index) => Array.from(localStorageData.keys())[index] || null)
};

const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};

global.localStorage = localStorageMock;
global.sessionStorage = sessionStorageMock;

// ============================================================================
// COOKIE MANAGEMENT
// ============================================================================
const mockCookieData = new Map();
Object.defineProperty(document, 'cookie', {
  get: () => Array.from(mockCookieData.entries())
    .map(([key, value]) => `${key}=${value}`)
    .join('; '),
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

// ============================================================================
// NEXT.JS MOCKS
// ============================================================================
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

// ============================================================================
// AUTHENTICATION MOCKS
// ============================================================================
const mockAuthConfig = {
  development_mode: true,
  google_client_id: 'mock-google-client-id',
  endpoints: {
    login: 'http://localhost:8081/auth/login',
    logout: 'http://localhost:8081/auth/logout',
    callback: 'http://localhost:8081/auth/callback',
    token: 'http://localhost:8081/auth/token',
    user: 'http://localhost:8081/auth/me',
    dev_login: 'http://localhost:8081/auth/dev/login'
  },
  authorized_javascript_origins: ['http://localhost:3000'],
  authorized_redirect_uris: ['http://localhost:3000/auth/callback']
};

const mockUser = {
  id: 'test-user',
  email: 'test@example.com',
  full_name: 'Test User'
};

// Mock auth service
jest.mock('@/auth/service', () => ({
  authService: {
    getAuthConfig: jest.fn().mockResolvedValue(mockAuthConfig),
    handleDevLogin: jest.fn().mockResolvedValue({
      access_token: 'mock-token',
      token_type: 'Bearer'
    }),
    getToken: jest.fn().mockReturnValue('mock-token'),
    getAuthHeaders: jest.fn().mockReturnValue({ Authorization: 'Bearer mock-token' }),
    removeToken: jest.fn(),
    getDevLogoutFlag: jest.fn().mockReturnValue(false),
    setDevLogoutFlag: jest.fn(),
    clearDevLogoutFlag: jest.fn(),
    handleLogin: jest.fn(),
    handleLogout: jest.fn(),
    useAuth: jest.fn().mockReturnValue({
      user: mockUser,
      login: jest.fn(),
      logout: jest.fn(),
      loading: false,
      authConfig: mockAuthConfig,
      token: 'mock-token'
    })
  }
}));

// Mock auth context
jest.mock('@/auth/context', () => {
  const React = require('react');
  const mockAuthContextValue = {
    user: mockUser,
    login: jest.fn(),
    logout: jest.fn(),
    loading: false,
    authConfig: mockAuthConfig,
    token: 'mock-token'
  };

  const MockAuthContext = React.createContext(mockAuthContextValue);

  return {
    AuthContext: MockAuthContext,
    AuthProvider: ({ children }) => React.createElement(MockAuthContext.Provider, { value: mockAuthContextValue }, children),
    useAuth: () => mockAuthContextValue
  };
});

// ============================================================================
// WEBSOCKET PROVIDER MOCKS
// ============================================================================
jest.mock('@/providers/WebSocketProvider', () => {
  const React = require('react');
  const mockWebSocketContextValue = {
    sendMessage: jest.fn(),
    addOptimisticMessage: jest.fn(),
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

// ============================================================================
// HOOK MOCKS
// ============================================================================
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendMessage: jest.fn(),
    addOptimisticMessage: jest.fn(),
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

jest.mock('@/hooks/useMCPTools', () => ({
  useMCPTools: jest.fn(() => ({
    tools: [{
      name: 'mock-tool',
      server_name: 'mock-server',
      description: 'Mock MCP tool for testing',
      input_schema: {
        type: 'object',
        properties: {
          input: { type: 'string', description: 'Test input' }
        }
      }
    }],
    executions: [],
    servers: [{
      id: 'mock-server-1',
      name: 'mock-server',
      url: 'http://localhost:3001',
      transport: 'HTTP',
      status: 'CONNECTED',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }],
    executeTool: jest.fn().mockResolvedValue({
      tool_name: 'mock-tool',
      server_name: 'mock-server',
      content: [{ type: 'text', text: 'Mock result content' }],
      is_error: false,
      execution_time_ms: 150
    }),
    getServerStatus: jest.fn().mockReturnValue('CONNECTED'),
    refreshTools: jest.fn().mockResolvedValue(undefined),
    isLoading: false,
    error: undefined,
    connectToServer: jest.fn().mockResolvedValue(true),
    disconnectFromServer: jest.fn().mockResolvedValue(true),
    loadServers: jest.fn().mockResolvedValue(undefined),
    loadTools: jest.fn().mockResolvedValue(undefined)
  }))
}));

// ============================================================================
// STORE MOCKS
// ============================================================================
jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn(() => ({
    isAuthenticated: true,
    user: mockUser,
    token: 'mock-token',
    login: jest.fn(),
    logout: jest.fn(),
    clearAuth: jest.fn(),
    setUser: jest.fn(),
    setToken: jest.fn()
  }))
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn(() => ({
    isAuthenticated: true,
    activeThreadId: 'test-thread-123',
    isProcessing: false,
    messages: [],
    sendMessage: jest.fn(),
    addOptimisticMessage: jest.fn(),
    clearMessages: jest.fn()
  }))
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: jest.fn(() => ({
    currentThreadId: 'test-thread-123',
    threads: [],
    createThread: jest.fn(),
    selectThread: jest.fn(),
    deleteThread: jest.fn()
  }))
}));

// ============================================================================
// SERVICE MOCKS
// ============================================================================
// Mock API clients
jest.mock('@/services/apiClient', () => ({
  apiClient: {
    get: jest.fn().mockResolvedValue({ data: {} }),
    post: jest.fn().mockResolvedValue({ data: {} }),
    put: jest.fn().mockResolvedValue({ data: {} }),
    delete: jest.fn().mockResolvedValue({ data: {} })
  }
}));

jest.mock('@/services/apiClientWrapper', () => ({
  ApiClientWrapper: jest.fn().mockImplementation(() => ({
    get: jest.fn().mockResolvedValue({ data: {} }),
    post: jest.fn().mockResolvedValue({ data: {} }),
    put: jest.fn().mockResolvedValue({ data: {} }),
    delete: jest.fn().mockResolvedValue({ data: {} }),
    request: jest.fn().mockResolvedValue({ data: {} })
  }))
}));

// Mock thread service
jest.mock('@/services/threadService', () => ({
  ThreadService: {
    getThread: jest.fn().mockResolvedValue({
      id: 'test-thread-123',
      title: 'Test Thread',
      messages: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }),
    createThread: jest.fn().mockResolvedValue({
      id: 'new-thread-123',
      title: 'New Thread',
      messages: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }),
    updateThread: jest.fn().mockResolvedValue(true),
    deleteThread: jest.fn().mockResolvedValue(true),
    listThreads: jest.fn().mockResolvedValue([])
  }
}));

// Mock MCP client service
jest.mock('@/services/mcp-client-service', () => {
  const mockFactories = {
    createMockServer: (overrides = {}) => ({
      id: 'mock-server-1',
      name: 'mock-server',
      url: 'http://localhost:3001',
      transport: 'HTTP',
      status: 'CONNECTED',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      ...overrides
    }),
    createMockTool: (overrides = {}) => ({
      name: 'mock-tool',
      server_name: 'mock-server',
      description: 'Mock MCP tool for testing',
      input_schema: {
        type: 'object',
        properties: {
          input: { type: 'string', description: 'Test input' }
        }
      },
      ...overrides
    }),
    createMockToolResult: (overrides = {}) => ({
      tool_name: 'mock-tool',
      server_name: 'mock-server',
      content: [{ type: 'text', text: 'Mock result content' }],
      is_error: false,
      execution_time_ms: 150,
      ...overrides
    })
  };

  let mockServers = [mockFactories.createMockServer()];
  let mockTools = [mockFactories.createMockTool()];

  return {
    listServers: jest.fn().mockResolvedValue(mockServers),
    getServerStatus: jest.fn().mockResolvedValue(mockServers[0] || null),
    connectServer: jest.fn().mockResolvedValue(true),
    disconnectServer: jest.fn().mockResolvedValue(true),
    discoverTools: jest.fn().mockResolvedValue(mockTools),
    executeTool: jest.fn().mockResolvedValue(mockFactories.createMockToolResult()),
    getToolSchema: jest.fn().mockResolvedValue({
      type: 'object',
      properties: {
        input: { type: 'string', description: 'Mock schema' }
      }
    }),
    listResources: jest.fn().mockResolvedValue([]),
    fetchResource: jest.fn().mockResolvedValue(null),
    clearCache: jest.fn().mockResolvedValue(true),
    healthCheck: jest.fn().mockResolvedValue(true),
    serverHealthCheck: jest.fn().mockResolvedValue(true),
    getServerConnections: jest.fn().mockResolvedValue(mockServers.filter(s => s.status === 'CONNECTED')),
    refreshAllConnections: jest.fn().mockResolvedValue(true),
    __mockSetServers: (servers) => { mockServers = servers; },
    __mockSetTools: (tools) => { mockTools = tools; },
    __mockReset: () => {
      mockServers = [mockFactories.createMockServer()];
      mockTools = [mockFactories.createMockTool()];
    }
  };
});

// ============================================================================
// COMPONENT MOCKS
// ============================================================================
jest.mock('./components/chat/RawJsonView', () => {
  const React = require('react');
  return {
    RawJsonView: ({ data }) => React.createElement('div', { 
      'data-testid': 'raw-json-view' 
    }, JSON.stringify(data, null, 2))
  };
});

// ============================================================================
// CONSOLE SUPPRESSION
// ============================================================================
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
    if (args[0] && typeof args[0] === 'object' && args[0].message && 
        args[0].message.includes('Not implemented')) {
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
  Date.now = () => 1640995200000; // Fixed timestamp for consistent tests
});

afterEach(() => {
  jest.clearAllMocks();
  fetchMock.resetMocks();
  if (localStorage && localStorage.clear) localStorage.clear();
  if (sessionStorage && sessionStorage.clear) sessionStorage.clear();
  mockCookieData.clear();
  
  // Reset scroll positions
  if (typeof window !== 'undefined') {
    Object.defineProperty(window, 'scrollX', { value: 0, writable: true });
    Object.defineProperty(window, 'scrollY', { value: 0, writable: true });
    Object.defineProperty(window, 'pageXOffset', { value: 0, writable: true });
    Object.defineProperty(window, 'pageYOffset', { value: 0, writable: true });
  }
});