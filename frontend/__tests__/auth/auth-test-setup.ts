/**
 * Auth Test Setup - Jest Module Mocks
 * ===================================
 * Centralized module mocks for auth testing - must be imported before auth modules
 * BVJ: Enterprise segment - ensures security compliance test coverage
 */

// Mock React hooks properly
const mockUseContext = jest.fn();
jest.mock('react', () => ({
  ...jest.requireActual('react'),
  useContext: mockUseContext
}));

// Default mock auth config data
const defaultMockAuthConfig = {
  development_mode: process.env.NODE_ENV === 'development',
  google_client_id: 'mock-google-client-id',
  endpoints: {
    login: 'http://localhost:8081/api/auth/login',
    logout: 'http://localhost:8081/api/auth/logout',
    callback: 'http://localhost:8081/api/auth/callback',
    token: 'http://localhost:8081/api/auth/token',
    user: 'http://localhost:8081/api/auth/me',
    dev_login: 'http://localhost:8081/api/auth/dev/login'
  },
  authorized_javascript_origins: ['http://localhost:3000'],
  authorized_redirect_uris: ['http://localhost:3000/auth/callback']
};

// Mock auth service client to prevent real navigation
const mockAuthServiceClient = {
  getConfig: jest.fn().mockResolvedValue(defaultMockAuthConfig),
  initiateLogin: jest.fn(),
  logout: jest.fn().mockResolvedValue({ success: true }),
  getSession: jest.fn(),
  getCurrentUser: jest.fn(),
  validateToken: jest.fn(),
  refreshToken: jest.fn()
};

// Mock getAuthServiceConfig function
const mockGetAuthServiceConfig = jest.fn(() => ({
  baseUrl: 'http://localhost:8081',
  endpoints: {
    login: 'http://localhost:8081/api/auth/login',
    logout: 'http://localhost:8081/api/auth/logout',
    callback: 'http://localhost:8081/api/auth/callback',
    token: 'http://localhost:8081/api/auth/token',
    refresh: 'http://localhost:8081/api/auth/refresh',
    validate_token: 'http://localhost:8081/api/auth/validate',
    config: 'http://localhost:8081/api/auth/config',
    session: 'http://localhost:8081/api/auth/session',
    me: 'http://localhost:8081/api/auth/me'
  },
  oauth: {
    googleClientId: 'mock-google-client-id',
    redirectUri: 'http://localhost:3000/auth/callback',
    javascriptOrigins: ['http://localhost:3000']
  }
}));

jest.mock('@/lib/auth-service-config', () => ({
  authService: mockAuthServiceClient,
  AuthServiceClient: jest.fn().mockImplementation(() => mockAuthServiceClient),
  getAuthServiceConfig: mockGetAuthServiceConfig
}));

// Mock logger
const mockLogger = {
  info: jest.fn(),
  warn: jest.fn(), 
  error: jest.fn(),
  debug: jest.fn()
};

jest.mock('@/lib/logger', () => ({
  logger: mockLogger
}));

// Mock debug logger used in auth-service-config
jest.mock('@/utils/debug-logger', () => ({
  logger: mockLogger
}));

// Mock configuration
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8081'
  }
}));

// Note: We DON'T mock @/auth/service here because we want to test the real auth service
// which will use our mocked authServiceClient from @/lib/auth-service-config

// Offline fallback config - matches the auth service fallback logic
const offlineFallbackConfig = {
  development_mode: false,
  google_client_id: 'mock-google-client-id',
  endpoints: {
    login: 'http://localhost:8081/api/auth/login',
    logout: 'http://localhost:8081/api/auth/logout',
    callback: 'http://localhost:8081/api/auth/callback',
    token: 'http://localhost:8081/api/auth/token',
    user: 'http://localhost:8081/api/auth/me',
    dev_login: 'http://localhost:8081/api/auth/dev/login'
  },
  authorized_javascript_origins: ['http://localhost:3000'],
  authorized_redirect_uris: ['http://localhost:3000/auth/callback']
};

// Export mocks for test access
export { mockUseContext, mockAuthServiceClient, mockLogger, defaultMockAuthConfig, mockGetAuthServiceConfig, offlineFallbackConfig };