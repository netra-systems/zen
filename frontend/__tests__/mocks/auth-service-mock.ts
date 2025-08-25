/**
 * Auth Service Mock Configuration
 * Mocks the independent auth service for frontend tests
 * Ensures tests work with auth as a separate microservice
 */

import { AuthServiceClient } from '@/lib/auth-service-config';

// Mock auth service responses
export const mockAuthServiceResponses = {
  config: {
    development_mode: false,
    google_client_id: 'mock-google-client-id',
    oauth_enabled: true,
    offline_mode: false,
    endpoints: {
      login: 'http://localhost:8081/api/auth/login',
      logout: 'http://localhost:8081/api/auth/logout', 
      callback: 'http://localhost:8081/api/auth/callback',
      token: 'http://localhost:8081/api/auth/token',
      user: 'http://localhost:8081/api/auth/me',
      dev_login: 'http://localhost:8081/api/auth/dev/login'
    }
  },
  session: {
    user: {
      id: 'user-123',
      email: 'test@example.com',
      name: 'Test User',
      role: 'admin'
    },
    token: 'mock-jwt-token',
    expires_at: new Date(Date.now() + 3600000).toISOString()
  },
  user: {
    id: 'user-123',
    email: 'test@example.com',
    full_name: 'Test User',
    role: 'admin',
    created_at: '2024-01-01T00:00:00Z'
  },
  token: {
    access_token: 'mock-jwt-token',
    token_type: 'Bearer',
    expires_in: 3600
  },
  devLogin: {
    access_token: 'dev-jwt-token',
    token_type: 'Bearer'
  }
};

/**
 * Mock the auth service client
 */
export function mockAuthServiceClient() {
  const mockClient = {
    getConfig: jest.fn().mockResolvedValue(mockAuthServiceResponses.config),
    initiateLogin: jest.fn(),
    logout: jest.fn().mockResolvedValue({ success: true }),
    getSession: jest.fn().mockResolvedValue(mockAuthServiceResponses.session),
    getCurrentUser: jest.fn().mockResolvedValue(mockAuthServiceResponses.user),
    validateToken: jest.fn().mockResolvedValue(true),
    refreshToken: jest.fn().mockResolvedValue(mockAuthServiceResponses.token),
    config: {
      baseUrl: 'http://localhost:8081',
      endpoints: mockAuthServiceResponses.config.endpoints,
      oauth: {
        googleClientId: 'mock-google-client-id',
        redirectUri: 'http://localhost:3000/auth/callback',
        javascriptOrigins: ['http://localhost:3000']
      }
    }
  };
  
  return mockClient;
}

/**
 * Setup auth service mocks for tests
 */
export function setupAuthServiceMocks() {
  // Mock the auth-service-config module
  jest.mock('@/lib/auth-service-config', () => ({
    authService: mockAuthServiceClient(),
    AuthServiceClient: jest.fn().mockImplementation(() => mockAuthServiceClient()),
    getAuthServiceConfig: jest.fn().mockReturnValue({
      baseUrl: 'http://localhost:8081',
      endpoints: mockAuthServiceResponses.config.endpoints,
      oauth: {
        googleClientId: 'mock-google-client-id',
        redirectUri: 'http://localhost:3000/auth/callback',
        javascriptOrigins: ['http://localhost:3000']
      }
    })
  }));
}

/**
 * Mock fetch responses for auth service API calls
 */
export function mockAuthServiceFetch() {
  global.fetch = jest.fn().mockImplementation((url: string) => {
    const urlStr = url.toString();
    
    // Mock different auth service endpoints
    if (urlStr.includes('/api/auth/config')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAuthServiceResponses.config)
      });
    }
    
    if (urlStr.includes('/api/auth/session')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAuthServiceResponses.session)
      });
    }
    
    if (urlStr.includes('/api/auth/me')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAuthServiceResponses.user)
      });
    }
    
    if (urlStr.includes('/api/auth/dev/login')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAuthServiceResponses.devLogin)
      });
    }
    
    if (urlStr.includes('/api/auth/refresh')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAuthServiceResponses.token)
      });
    }
    
    if (urlStr.includes('/api/auth/validate')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ valid: true })
      });
    }
    
    if (urlStr.includes('/api/auth/logout')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true })
      });
    }
    
    // Default response
    return Promise.resolve({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ error: 'Not found' })
    });
  }) as jest.Mock;
}

/**
 * Reset all auth service mocks
 */
export function resetAuthServiceMocks() {
  jest.clearAllMocks();
  if (global.fetch && jest.isMockFunction(global.fetch)) {
    (global.fetch as jest.Mock).mockClear();
  }
}

/**
 * Setup auth service error responses
 */
export function setupAuthServiceErrors() {
  global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));
}

/**
 * Setup unauthorized responses
 */
export function setupAuthServiceUnauthorized() {
  global.fetch = jest.fn().mockResolvedValue({
    ok: false,
    status: 401,
    json: () => Promise.resolve({ error: 'Unauthorized' })
  });
}