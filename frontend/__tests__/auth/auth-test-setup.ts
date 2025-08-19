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

// Mock auth service client to prevent real navigation
const mockAuthServiceClient = {
  getConfig: jest.fn(),
  initiateLogin: jest.fn(),
  logout: jest.fn(),
  getSession: jest.fn(),
  getCurrentUser: jest.fn(),
  validateToken: jest.fn(),
  refreshToken: jest.fn()
};

jest.mock('@/lib/auth-service-config', () => ({
  authService: mockAuthServiceClient,
  getAuthServiceConfig: jest.fn(() => ({
    baseUrl: 'http://localhost:8081',
    endpoints: {
      login: 'http://localhost:8081/auth/login',
      logout: 'http://localhost:8081/auth/logout',
      callback: 'http://localhost:8081/auth/callback',
      token: 'http://localhost:8081/auth/token',
      refresh: 'http://localhost:8081/auth/refresh',
      validate_token: 'http://localhost:8081/auth/validate',
      config: 'http://localhost:8081/auth/config',
      session: 'http://localhost:8081/auth/session',
      me: 'http://localhost:8081/auth/me'
    },
    oauth: {
      googleClientId: 'mock-google-client-id',
      redirectUri: 'http://localhost:3000/auth/callback',
      javascriptOrigins: ['http://localhost:3000']
    }
  }))
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

// Mock configuration
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8081'
  }
}));

// Export mocks for test access
export { mockUseContext, mockAuthServiceClient, mockLogger };