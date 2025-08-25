/**
 * Startup Test Utilities
 * Provides common utilities for system startup tests
 */

export const setupTestEnvironment = () => {
  // Set up test environment variables
  process.env.NODE_ENV = 'test';
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8081';
  
  // Setup DOM environment
  if (typeof window !== 'undefined') {
    try {
      Object.defineProperty(window, 'location', {
        value: { href: 'http://localhost:3000' },
        writable: true
      });
    } catch (e) {
      // Property already exists, modify it instead
      if (window.location) {
        window.location.href = 'http://localhost:3000';
      }
    }
  }
  
  return {
    environment: 'test',
    apiUrl: 'http://localhost:8081'
  };
};

export const cleanupTestEnvironment = () => {
  // Clean up environment variables
  delete process.env.NEXT_PUBLIC_API_URL;
  
  // Clear any global state
  if (typeof window !== 'undefined') {
    window.localStorage.clear();
    window.sessionStorage.clear();
  }
  
  // Reset all mocks
  jest.clearAllMocks();
};

export const setupLocalStorageMocks = () => {
  const mockLocalStorage = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn()
  };
  
  Object.defineProperty(window, 'localStorage', {
    value: mockLocalStorage,
    writable: true
  });
  
  return mockLocalStorage;
};

export const createMockUser = (overrides: any = {}) => {
  return {
    id: 'test-user-id',
    email: 'test@example.com',
    name: 'Test User',
    ...overrides
  };
};

export const setupServiceWorkerMocks = () => {
  // Mock service worker registration
  Object.defineProperty(navigator, 'serviceWorker', {
    value: {
      register: jest.fn().mockResolvedValue({
        installing: null,
        waiting: null,
        active: null,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      }),
      ready: Promise.resolve({
        installing: null,
        waiting: null,
        active: null,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      })
    },
    writable: true
  });
  
  return navigator.serviceWorker;
};

export const setupThemeMocks = () => {
  // Mock theme detection
  Object.defineProperty(window, 'matchMedia', {
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
    writable: true
  });
  
  return window.matchMedia;
};

export const createAppConfig = (overrides: any = {}) => {
  return {
    apiUrl: 'http://localhost:8081',
    wsUrl: 'ws://localhost:8081/ws',
    environment: 'test',
    version: '1.0.0',
    features: {
      websockets: true,
      auth: true,
      notifications: true
    },
    ...overrides
  };
};

export const createMockResponse = (data: any, options: any = {}) => {
  return {
    ok: options.ok !== false,
    status: options.status || 200,
    statusText: options.statusText || 'OK',
    json: jest.fn().mockResolvedValue(data),
    text: jest.fn().mockResolvedValue(JSON.stringify(data)),
    headers: new Map(Object.entries(options.headers || {}))
  };
};

export const clearStorage = () => {
  if (typeof window !== 'undefined') {
    window.localStorage.clear();
    window.sessionStorage.clear();
  }
};