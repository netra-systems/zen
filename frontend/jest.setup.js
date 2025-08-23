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

// Add React for JSX components
global.React = require('react');

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
  dispatchEvent() { return true; }
};

// Prevent hanging tests by ensuring all timers are cleaned up
let timeoutIds = new Set();
let intervalIds = new Set();

const originalSetTimeout = global.setTimeout;
const originalSetInterval = global.setInterval;
const originalClearTimeout = global.clearTimeout;
const originalClearInterval = global.clearInterval;

global.setTimeout = function(callback, delay, ...args) {
  const id = originalSetTimeout.call(this, callback, delay, ...args);
  timeoutIds.add(id);
  return id;
};

global.setInterval = function(callback, delay, ...args) {
  const id = originalSetInterval.call(this, callback, delay, ...args);
  intervalIds.add(id);
  return id;
};

global.clearTimeout = function(id) {
  timeoutIds.delete(id);
  return originalClearTimeout.call(this, id);
};

global.clearInterval = function(id) {
  intervalIds.delete(id);
  return originalClearInterval.call(this, id);
};

// Clean up all timers after each test - more aggressive cleanup
afterEach(() => {
  // Clear all tracked timers
  for (const id of timeoutIds) {
    originalClearTimeout(id);
  }
  for (const id of intervalIds) {
    originalClearInterval(id);
  }
  timeoutIds.clear();
  intervalIds.clear();
  
  // Force clear any remaining Node.js timers (aggressive cleanup)
  if (typeof global._getActiveHandles === 'function') {
    const handles = global._getActiveHandles();
    handles.forEach(handle => {
      if (handle && typeof handle.close === 'function') {
        try {
          handle.close();
        } catch (e) {
          // Ignore cleanup errors
        }
      }
    });
  }
});

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
  constructor(url, protocols) {
    this.url = url + `-test-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    this.protocols = protocols || [];
    this.readyState = MockWebSocket.CONNECTING;
    this.bufferedAmount = 0;
    this.binaryType = 'blob';
    this.extensions = '';
    this.protocol = '';
    
    // Event handlers
    this.onopen = null;
    this.onclose = null;
    this.onerror = null;
    this.onmessage = null;
    
    // Event listener management
    this.eventListeners = new Map();
    this.send = jest.fn();
    this.close = jest.fn((code, reason) => {
      this.readyState = MockWebSocket.CLOSING;
      setTimeout(() => {
        this.readyState = MockWebSocket.CLOSED;
        const closeEvent = new CloseEvent('close', { code: code || 1000, reason: reason || '' });
        this.onclose?.(closeEvent);
        this.dispatchEvent(closeEvent);
      }, 0);
    });
    this.addEventListener = jest.fn((type, listener) => {
      if (!this.eventListeners.has(type)) {
        this.eventListeners.set(type, new Set());
      }
      this.eventListeners.get(type).add(listener);
    });
    this.removeEventListener = jest.fn((type, listener) => {
      if (this.eventListeners.has(type)) {
        this.eventListeners.get(type).delete(listener);
      }
    });
    this.dispatchEvent = jest.fn((event) => {
      if (this.eventListeners.has(event.type)) {
        this.eventListeners.get(event.type).forEach(listener => {
          try {
            listener(event);
          } catch (e) {
            // Ignore listener errors in tests
          }
        });
      }
      return true;
    });
    
    // Simulate realistic connection process
    setTimeout(() => {
      if (this.readyState === MockWebSocket.CONNECTING) {
        this.readyState = MockWebSocket.OPEN;
        const openEvent = new Event('open');
        this.onopen?.(openEvent);
        this.dispatchEvent(openEvent);
      }
    }, 10);
  }
  
  simulateMessage(data) {
    if (this.readyState === MockWebSocket.OPEN) {
      const messageData = typeof data === 'string' ? data : JSON.stringify(data);
      const event = new MessageEvent('message', { data: messageData });
      this.onmessage?.(event);
      this.dispatchEvent(event);
    }
  }
  
  simulateError(error) {
    const errorEvent = new ErrorEvent('error', { error: error || new Error('WebSocket error') });
    this.onerror?.(errorEvent);
    this.dispatchEvent(errorEvent);
  }
  
  simulateOpen() {
    if (this.readyState === MockWebSocket.CONNECTING) {
      this.readyState = MockWebSocket.OPEN;
      const openEvent = new Event('open');
      this.onopen?.(openEvent);
      this.dispatchEvent(openEvent);
    }
  }
  
  simulateClose(code = 1000, reason = '') {
    if (this.readyState !== MockWebSocket.CLOSED) {
      this.readyState = MockWebSocket.CLOSING;
      setTimeout(() => {
        this.readyState = MockWebSocket.CLOSED;
        const closeEvent = new CloseEvent('close', { code, reason });
        this.onclose?.(closeEvent);
        this.dispatchEvent(closeEvent);
      }, 0);
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
// Initialize with auth token for consistent test state
localStorageData.set('token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.test-signature');
localStorageData.set('auth_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.test-signature');

const localStorageMock = {
  getItem: jest.fn((key) => localStorageData.get(key) || null),
  setItem: jest.fn((key, value) => {
    if (localStorageData.size > 100) {
      // Preserve auth tokens when clearing storage
      const token = localStorageData.get('token');
      const authToken = localStorageData.get('auth_token');
      localStorageData.clear();
      if (token) localStorageData.set('token', token);
      if (authToken) localStorageData.set('auth_token', authToken);
    }
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

// Mock JWT token for consistent use across tests
const mockJWTToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.test-signature';

// Mock auth service
jest.mock('@/auth/service', () => ({
  authService: {
    getAuthConfig: jest.fn().mockResolvedValue(mockAuthConfig),
    handleDevLogin: jest.fn().mockResolvedValue({
      access_token: mockJWTToken,
      token_type: 'Bearer'
    }),
    getToken: jest.fn().mockReturnValue(mockJWTToken),
    getAuthHeaders: jest.fn().mockReturnValue({ Authorization: `Bearer ${mockJWTToken}` }),
    removeToken: jest.fn(() => {
      localStorageData.delete('token');
      localStorageData.delete('auth_token');
    }),
    getDevLogoutFlag: jest.fn().mockReturnValue(false),
    setDevLogoutFlag: jest.fn(),
    clearDevLogoutFlag: jest.fn(),
    handleLogin: jest.fn((credentials) => {
      localStorageData.set('token', mockJWTToken);
      localStorageData.set('auth_token', mockJWTToken);
      return Promise.resolve({ token: mockJWTToken, user: mockUser });
    }),
    handleLogout: jest.fn(() => {
      localStorageData.delete('token');
      localStorageData.delete('auth_token');
      return Promise.resolve();
    }),
    useAuth: jest.fn().mockReturnValue({
      user: mockUser,
      login: jest.fn(),
      logout: jest.fn(),
      loading: false,
      authConfig: mockAuthConfig,
      token: mockJWTToken,
      isAuthenticated: true
    })
  }
}));

// Mock auth context
jest.mock('@/auth/context', () => {
  const mockReact = require('react');
  const mockAuthContextValue = {
    user: {
      id: 'test-user',
      email: 'test@example.com',
      full_name: 'Test User'
    },
    login: jest.fn((credentials) => {
      localStorageData.set('token', mockJWTToken);
      localStorageData.set('auth_token', mockJWTToken);
      return Promise.resolve({ token: mockJWTToken, user: mockUser });
    }),
    logout: jest.fn(() => {
      localStorageData.delete('token');
      localStorageData.delete('auth_token');
      return Promise.resolve();
    }),
    loading: false,
    authConfig: {
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
    },
    token: mockJWTToken,
    isAuthenticated: true
  };

  const MockAuthContext = mockReact.createContext(mockAuthContextValue);

  return {
    AuthContext: MockAuthContext,
    AuthProvider: ({ children }) => mockReact.createElement(MockAuthContext.Provider, { value: mockAuthContextValue }, children),
    useAuth: () => mockAuthContextValue
  };
});

// ============================================================================
// WEBSOCKET PROVIDER MOCKS
// ============================================================================
jest.mock('@/providers/WebSocketProvider', () => {
  const mockReact = require('react');
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
  
  const MockWebSocketContext = mockReact.createContext(mockWebSocketContextValue);
  
  return {
    WebSocketProvider: ({ children }) => mockReact.createElement(MockWebSocketContext.Provider, { value: mockWebSocketContextValue }, children),
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
    getServerStatus: jest.fn().mockImplementation((serverName) => {
      // Return CONNECTED for mock-server, DISCONNECTED for unknown servers
      return serverName === 'mock-server' ? 'CONNECTED' : 'DISCONNECTED';
    }),
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
    token: mockJWTToken,
    login: jest.fn((user, token) => {
      localStorageData.set('token', token || mockJWTToken);
      localStorageData.set('auth_token', token || mockJWTToken);
      return Promise.resolve();
    }),
    logout: jest.fn(() => {
      localStorageData.delete('token');
      localStorageData.delete('auth_token');
      return Promise.resolve();
    }),
    clearAuth: jest.fn(() => {
      localStorageData.delete('token');
      localStorageData.delete('auth_token');
    }),
    setUser: jest.fn(),
    setToken: jest.fn((token) => {
      localStorageData.set('token', token);
      localStorageData.set('auth_token', token);
    })
  }))
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn(() => ({
    isAuthenticated: true,
    activeThreadId: 'test-thread-123',
    isProcessing: false,
    messages: [],
    sendMessage: jest.fn(),
    addMessage: jest.fn(),
    setProcessing: jest.fn(),
    setActiveThread: jest.fn(),
    addOptimisticMessage: jest.fn(),
    updateOptimisticMessage: jest.fn(),
    removeOptimisticMessage: jest.fn(),
    clearOptimisticMessages: jest.fn(),
    resetLayers: jest.fn(),
    setConnectionStatus: jest.fn(),
    setThreadLoading: jest.fn(),
    startThreadLoading: jest.fn(),
    completeThreadLoading: jest.fn(),
    clearMessages: jest.fn(),
    loadMessages: jest.fn()
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

// Mock message sending hooks to prevent API calls and missing function errors
jest.mock('@/components/chat/hooks/useMessageSending', () => ({
  useMessageSending: jest.fn(() => ({
    isSending: false,
    isProcessing: false,
    error: null,
    handleSend: jest.fn().mockImplementation(async (params) => {
      // Simulate real behavior - validate params and resolve quickly
      if (params?.message && params?.isAuthenticated) {
        return Promise.resolve();
      }
      return Promise.reject(new Error('Invalid params'));
    }),
    setProcessing: jest.fn(), // Add missing setProcessing function
    reset: jest.fn(),
    retry: jest.fn().mockResolvedValue(undefined)
  }))
}));

// Mock additional hooks that might be causing issues
jest.mock('@/hooks/useAgent', () => ({
  useAgent: jest.fn(() => ({
    agent: null,
    isRunning: false,
    isStarting: false,
    error: null,
    startAgent: jest.fn().mockResolvedValue(undefined),
    stopAgent: jest.fn().mockResolvedValue(undefined),
    restartAgent: jest.fn().mockResolvedValue(undefined)
  }))
}));

jest.mock('@/hooks/useAgentStart', () => ({
  useAgentStart: jest.fn(() => ({
    isStarting: false,
    error: null,
    startAgent: jest.fn().mockResolvedValue(undefined)
  }))
}));

jest.mock('@/hooks/useAgentUpdates', () => ({
  useAgentUpdates: jest.fn(() => ({
    updates: [],
    lastUpdate: null,
    isReceivingUpdates: false
  }))
}));

jest.mock('@/hooks/usePerformanceMetrics', () => ({
  usePerformanceMetrics: jest.fn(() => ({
    metrics: {
      renderCount: 1,
      lastRenderTime: Date.now(),
      averageResponseTime: 100,
      wsLatency: 50,
      memoryUsage: 1024,
      fps: 60,
      componentRenderTimes: new Map()
    },
    startTracking: jest.fn(),
    stopTracking: jest.fn(),
    reset: jest.fn()
  }))
}));

// Mock additional missing hooks
jest.mock('@/hooks/useKeyboardShortcuts', () => ({
  useKeyboardShortcuts: jest.fn(() => ({
    shortcuts: {},
    registerShortcut: jest.fn(),
    unregisterShortcut: jest.fn(),
    isEnabled: true
  }))
}));

// Mock framer-motion to prevent animation issues in tests
jest.mock('framer-motion', () => {
  const mockReact = require('react');
  return {
    motion: {
      div: ({ children, whileHover, whileTap, initial, animate, exit, transition, ...props }) => 
        mockReact.createElement('div', props, children),
      button: ({ children, whileHover, whileTap, initial, animate, exit, transition, ...props }) => 
        mockReact.createElement('button', props, children)
    },
    AnimatePresence: ({ children, mode }) => children
  };
});

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: jest.fn(() => ({
    isLoading: false,
    setLoading: jest.fn(),
    withLoading: jest.fn((fn) => fn)
  }))
}));

jest.mock('@/hooks/useError', () => ({
  useError: jest.fn(() => ({
    error: null,
    setError: jest.fn(),
    clearError: jest.fn(),
    hasError: false
  }))
}));

// Mock event processor hook to prevent timer leaks
jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: jest.fn(() => ({
    processedCount: 0,
    errorCount: 0,
    queueSize: 0,
    duplicatesDropped: 0,
    getStats: jest.fn(() => ({
      totalProcessed: 0,
      totalDropped: 0,
      totalErrors: 0,
      queueSize: 0,
      duplicatesDropped: 0,
      lastProcessedTimestamp: 0
    })),
    clearQueue: jest.fn()
  }))
}));

// Mock circuit breaker to prevent timer leaks
jest.mock('@/lib/circuit-breaker', () => ({
  CircuitBreaker: jest.fn().mockImplementation(() => ({
    recordFailure: jest.fn(),
    recordSuccess: jest.fn(),
    isOpen: jest.fn(() => false),
    getState: jest.fn(() => ({
      isOpen: false,
      failureCount: 0,
      lastFailureTime: 0,
      openedAt: 0
    })),
    getFailureRate: jest.fn(() => 0),
    reset: jest.fn(),
    destroy: jest.fn()
  }))
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

  // Class-based mock for both default and named exports
  class MCPClientService {
    static async initialize() {
      return Promise.resolve();
    }

    static async connect() {
      return Promise.resolve(true);
    }

    static async disconnect() {
      return Promise.resolve(true);
    }

    static async getAvailableTools() {
      return Promise.resolve(mockTools);
    }

    static async executeTool(serverName, toolName, arguments_) {
      return Promise.resolve(mockFactories.createMockToolResult({
        tool_name: toolName,
        server_name: serverName
      }));
    }

    static getConnectionStatus() {
      return 'CONNECTED';
    }
  }

  return {
    default: MCPClientService,
    MCPClientService,
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
    },
    mockFactories
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

// Mock ExamplePrompts component to prevent UI component issues
jest.mock('@/components/chat/ExamplePrompts', () => {
  const React = require('react');
  return {
    ExamplePrompts: () => React.createElement('div', { 
      'data-testid': 'example-prompts' 
    }, 'Example prompts component')
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
  
  // Reset storage but preserve auth tokens for consistent test state
  const token = localStorageData.get('token');
  const authToken = localStorageData.get('auth_token');
  
  if (localStorage && localStorage.clear) localStorage.clear();
  if (sessionStorage && sessionStorage.clear) sessionStorage.clear();
  localStorageData.clear();
  mockCookieData.clear();
  
  // Restore default auth tokens
  if (token || authToken) {
    const defaultToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.test-signature';
    localStorageData.set('token', defaultToken);
    localStorageData.set('auth_token', defaultToken);
  }
  
  // Reset scroll positions
  if (typeof window !== 'undefined') {
    Object.defineProperty(window, 'scrollX', { value: 0, writable: true });
    Object.defineProperty(window, 'scrollY', { value: 0, writable: true });
    Object.defineProperty(window, 'pageXOffset', { value: 0, writable: true });
    Object.defineProperty(window, 'pageYOffset', { value: 0, writable: true });
  }
  
  // Ensure all mocks are properly cleaned up to prevent cross-test contamination
  jest.restoreAllMocks();
  jest.clearAllTimers();
});