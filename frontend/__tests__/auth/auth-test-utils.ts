/**
 * Auth Test Utils - Shared Testing Utilities
 * ==========================================
 * Shared utilities for auth testing including mocks, helpers, and validation functions
 * BVJ: Enterprise segment - ensures consistent, reliable auth testing
 * Architecture: ≤300 lines, functions ≤8 lines
 */

import { mockAuthServiceClient, mockLogger, defaultMockAuthConfig, mockGetAuthServiceConfig, mockUseContext } from './auth-test-setup';

// Test Environment Setup
export function setupAuthTestEnvironment() {
  const fetchMock = jest.fn();
  const localStorageMock = createLocalStorageMock();
  
  global.fetch = fetchMock;
  global.localStorage = localStorageMock;
  
  return { fetchMock, localStorageMock };
}

export function resetAuthTestMocks(testEnv: any) {
  testEnv.fetchMock.mockClear();
  testEnv.localStorageMock.clear();
  
  // Clear localStorage mock call history
  if (testEnv.localStorageMock.getItem && jest.isMockFunction(testEnv.localStorageMock.getItem)) {
    testEnv.localStorageMock.getItem.mockClear();
  }
  if (testEnv.localStorageMock.setItem && jest.isMockFunction(testEnv.localStorageMock.setItem)) {
    testEnv.localStorageMock.setItem.mockClear();
  }
  if (testEnv.localStorageMock.removeItem && jest.isMockFunction(testEnv.localStorageMock.removeItem)) {
    testEnv.localStorageMock.removeItem.mockClear();
  }
  
  // Clear mock calls but keep implementations
  Object.values(mockAuthServiceClient).forEach(mock => {
    if (jest.isMockFunction(mock)) {
      mock.mockClear();
    }
  });
  
  Object.values(mockLogger).forEach(mock => {
    if (jest.isMockFunction(mock)) {
      mock.mockClear();
    }
  });
  
  // Clear the getAuthServiceConfig mock as well
  if (jest.isMockFunction(mockGetAuthServiceConfig)) {
    mockGetAuthServiceConfig.mockClear();
  }
  
  // Clear useContext mock if it exists and is a function
  if (mockUseContext && jest.isMockFunction(mockUseContext)) {
    mockUseContext.mockClear();
  }
  
  // Ensure getConfig has the default implementation
  mockAuthServiceClient.getConfig.mockResolvedValue(defaultMockAuthConfig);
}

// Mock Data Factories
export function createMockAuthConfig() {
  return {
    development_mode: false,
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
    authorized_redirect_uris: ['http://localhost:3000/callback']
  };
}

export function createMockDevConfig() {
  return {
    ...createMockAuthConfig(),
    development_mode: true
  };
}

export function createMockToken() {
  return 'mock-token'; // Align with existing mock setup
}

export function createMockDevLoginResponse() {
  return {
    access_token: 'mock-token',
    token_type: 'Bearer'
  };
}

// HTTP Response Helpers
export function createSuccessResponse(data: any) {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(data)
  };
}

export function createErrorResponse(status: number) {
  return {
    ok: false,
    status,
    json: () => Promise.resolve({ error: 'Test error' })
  };
}

export function createNetworkError(message: string) {
  return new Error(message);
}

// Console Mock Helpers
export function mockConsoleMethod(method: keyof Console) {
  const original = console[method];
  console[method] = jest.fn();
  return original;
}

export function restoreConsoleMock(method: keyof Console, original: any) {
  console[method] = original;
}

// Validation Helpers
export function expectFetchCall(fetchMock: any, url: string, options?: any) {
  expect(fetchMock).toHaveBeenCalledWith(url, options);
}

export function validateTokenOperation(localStorageMock: any, operation: string) {
  if (operation === 'get') {
    expect(localStorageMock.getItem).toHaveBeenCalledWith('jwt_token');
  } else if (operation === 'remove') {
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('jwt_token');
  } else {
    expect(localStorageMock.setItem).toHaveBeenCalledWith('jwt_token', operation);
  }
}

export function validateDevLoginCall(fetchMock: any, config: any) {
  expect(fetchMock).toHaveBeenCalledWith(
    config.endpoints.dev_login,
    expect.objectContaining({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'dev@example.com' })
    })
  );
}

export function validateSecureTokenStorage(localStorageMock: any, token: string) {
  expect(localStorageMock.setItem).toHaveBeenCalledWith('jwt_token', token);
}

export function validateLogoutCall(authServiceMock: any) {
  expect(authServiceMock.logout).toHaveBeenCalled();
}

export function expectLocalStorageRemove(localStorageMock: any, key: string) {
  expect(localStorageMock.removeItem).toHaveBeenCalledWith(key);
}

export function validateSecureLogout(localStorageMock: any) {
  expect(localStorageMock.removeItem).toHaveBeenCalledWith('jwt_token');
}

// Auth header validation helpers  
export function expectAuthHeaders(headers: Record<string, string>, token: string) {
  expect(headers).toEqual({
    Authorization: `Bearer ${token}`
  });
}

export function expectEmptyHeaders(headers: Record<string, string>) {
  expect(headers).toEqual({});
}

// Mock auth context factory
export function createMockAuthContext() {
  return {
    user: null,
    login: jest.fn(),
    logout: jest.fn(),
    loading: false,
    authConfig: null,
    token: null
  };
}

// LocalStorage Mock
export function createLocalStorageMock() {
  let store: Record<string, string> = {};
  
  const mock = {
    getItem: jest.fn((key: string) => {
      return store[key] || null;
    }),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
      // Also clear all mock call history
      mock.getItem.mockClear();
      mock.setItem.mockClear();
      mock.removeItem.mockClear();
    }),
    key: jest.fn((index: number) => Object.keys(store)[index] || null),
    get length() {
      return Object.keys(store).length;
    }
  };
  
  return mock;
}

// Export mocks for direct access
export { mockAuthServiceClient, mockLogger, defaultMockAuthConfig, mockGetAuthServiceConfig };

