/**
 * Auth Service Test Setup
 * Ensures all tests properly mock the independent auth service
 */

import { mockAuthServiceResponses } from '../mocks/auth-service-mock';

// Mock the auth service config module globally
jest.mock('@/lib/auth-service-config', () => {
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

  return {
    authService: mockClient,
    AuthServiceClient: jest.fn().mockImplementation(() => mockClient),
    getAuthServiceConfig: jest.fn().mockReturnValue({
      baseUrl: 'http://localhost:8081',
      endpoints: {
        login: 'http://localhost:8081/api/v1/auth/login',
        logout: 'http://localhost:8081/api/v1/auth/logout',
        callback: 'http://localhost:8081/api/v1/auth/callback',
        token: 'http://localhost:8081/api/v1/auth/token',
        refresh: 'http://localhost:8081/api/v1/auth/refresh',
        validate_token: 'http://localhost:8081/api/v1/auth/validate',
        config: 'http://localhost:8081/api/v1/auth/config',
        session: 'http://localhost:8081/api/v1/auth/session',
        me: 'http://localhost:8081/api/v1/auth/me'
      },
      oauth: {
        googleClientId: 'mock-google-client-id',
        redirectUri: 'http://localhost:3000/auth/callback',
        javascriptOrigins: ['http://localhost:3000']
      }
    })
  };
});

// Mock fetch for auth service API calls
global.fetch = jest.fn().mockImplementation((url: string, options?: any) => {
  const urlStr = url.toString();
  
  // Auth service config endpoint
  if (urlStr.includes('/api/v1/auth/config')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockAuthServiceResponses.config)
    });
  }
  
  // Auth service session endpoint
  if (urlStr.includes('/api/v1/auth/session')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockAuthServiceResponses.session)
    });
  }
  
  // Auth service user endpoint
  if (urlStr.includes('/api/v1/auth/me')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockAuthServiceResponses.user)
    });
  }
  
  // Dev login endpoint
  if (urlStr.includes('/api/v1/auth/dev/login')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockAuthServiceResponses.devLogin)
    });
  }
  
  // Token refresh endpoint
  if (urlStr.includes('/api/v1/auth/refresh')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockAuthServiceResponses.token)
    });
  }
  
  // Token validation endpoint
  if (urlStr.includes('/api/v1/auth/validate')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ valid: true })
    });
  }
  
  // Logout endpoint
  if (urlStr.includes('/api/v1/auth/logout')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ success: true })
    });
  }
  
  // Default: return 404 for unknown endpoints
  return Promise.resolve({
    ok: false,
    status: 404,
    json: () => Promise.resolve({ error: 'Not found' })
  });
});

export {};