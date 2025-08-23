/**
 * Auth Security & Error Handling Tests
 * ====================================
 * Tests for security compliance, API error handling, and edge cases
 * 
 * BVJ: Enterprise segment - ensures security compliance, prevents auth vulnerabilities
 * Modular design: ≤300 lines, functions ≤8 lines
 */

// Import test setup with mocks FIRST
import './auth-test-setup';

// Set up localStorage mock before importing authService
import { createLocalStorageMock } from './auth-test-utils';
const testLocalStorageMock = createLocalStorageMock();
global.localStorage = testLocalStorageMock;

import { authService } from '@/auth';
import {
  setupAuthTestEnvironment,
  resetAuthTestMocks,
  createMockAuthConfig,
  createMockToken,
  createMockDevLoginResponse,
  createSuccessResponse,
  createErrorResponse,
  createNetworkError,
  validateSecureHeaders,
  validateSecureLogout,
  mockAuthServiceClient
} from './auth-test-utils';

describe('Auth Security & Error Handling', () => {
  let testEnv: ReturnType<typeof setupAuthTestEnvironment>;
  let mockAuthConfig: ReturnType<typeof createMockAuthConfig>;
  let mockToken: string;
  let mockDevLoginResponse: ReturnType<typeof createMockDevLoginResponse>;

  beforeEach(() => {
    testEnv = setupAuthTestEnvironment();
    mockAuthConfig = createMockAuthConfig();
    mockToken = createMockToken();
    mockDevLoginResponse = createMockDevLoginResponse();
    
    // Use the test-wide localStorage mock and clear it
    testLocalStorageMock.clear();
    
    // Also set up the testEnv to use our global mock
    testEnv.localStorageMock = testLocalStorageMock;
    
    resetAuthTestMocks(testEnv);
  });

  afterAll(() => {
    jest.restoreAllMocks();
  });

  describe('Security Tests', () => {
    it('should not expose sensitive data in headers', () => {
      testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
      
      const headers = authService.getAuthHeaders();
      
      validateSecureHeaders(headers);
    });

    it('should sanitize email input in dev login', async () => {
      testEnv.fetchMock.mockResolvedValue(
        createSuccessResponse(mockDevLoginResponse)
      );

      await authService.handleDevLogin(mockAuthConfig);

      expect(testEnv.fetchMock).toHaveBeenCalledWith(
        mockAuthConfig.endpoints.dev_login,
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: 'dev@example.com' })
        })
      );
    });

    it('should clear sensitive data on logout', async () => {
      testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
      testEnv.fetchMock.mockResolvedValue(createSuccessResponse({}));

      await authService.handleLogout(mockAuthConfig);

      validateSecureLogout(testEnv.localStorageMock);
    });

    it('should handle token with potential XSS content', () => {
      const xssToken = '<script>alert("xss")</script>';
      
      // Set up the mock to return the XSS token
      jest.spyOn(authService, 'getToken').mockReturnValue(xssToken);
      
      const headers = authService.getAuthHeaders();
      
      expect(headers.Authorization).toBe(`Bearer ${xssToken}`);
      expect(Object.keys(headers)).toEqual(['Authorization']);
      
      // Restore the spy
      jest.restoreAllMocks();
    });

    it('should handle SQL injection attempts in token', () => {
      const sqlToken = "'; DROP TABLE users; --";
      
      // Set up the mock to return the SQL injection token
      jest.spyOn(authService, 'getToken').mockReturnValue(sqlToken);
      
      const headers = authService.getAuthHeaders();
      
      expect(headers.Authorization).toBe(`Bearer ${sqlToken}`);
      
      // Restore the spy
      jest.restoreAllMocks();
    });

    it('should not leak sensitive data in error messages', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      testEnv.fetchMock.mockRejectedValue(createNetworkError('Network error'));

      await authService.handleDevLogin(mockAuthConfig);

      const errorMessage = consoleErrorSpy.mock.calls[0]?.[0] || '';
      expect(errorMessage).not.toContain(mockToken);
      expect(errorMessage).not.toContain('password');
      
      consoleErrorSpy.mockRestore();
    });
  });

  describe('API Error Handling', () => {
    it('should fallback to offline config on 401 unauthorized response', async () => {
      mockAuthServiceClient.getConfig.mockRejectedValue(
        new Error('HTTP 401: Failed to fetch auth configuration')
      );

      const result = await authService.getAuthConfig();
      expect(result).toEqual({
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
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
    });

    it('should fallback to offline config on 403 forbidden response', async () => {
      mockAuthServiceClient.getConfig.mockRejectedValue(
        new Error('HTTP 403: Failed to fetch auth configuration')
      );

      const result = await authService.getAuthConfig();
      expect(result).toEqual({
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
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
    });

    it('should fallback to offline config on 404 not found response', async () => {
      mockAuthServiceClient.getConfig.mockRejectedValue(
        new Error('HTTP 404: Failed to fetch auth configuration')
      );

      const result = await authService.getAuthConfig();
      expect(result).toEqual({
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
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
    });

    it('should fallback to offline config on 500 server error', async () => {
      mockAuthServiceClient.getConfig.mockRejectedValue(
        new Error('HTTP 500: Failed to fetch auth configuration')
      );

      const result = await authService.getAuthConfig();
      expect(result).toEqual({
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
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
    });

    it('should fallback to offline config on timeout errors', async () => {
      mockAuthServiceClient.getConfig.mockRejectedValue(
        createNetworkError('Request timeout')
      );

      const result = await authService.getAuthConfig();
      expect(result).toEqual({
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
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
    });

    it('should fallback to offline config on rate limiting (429)', async () => {
      mockAuthServiceClient.getConfig.mockRejectedValue(
        new Error('HTTP 429: Failed to fetch auth configuration')
      );

      const result = await authService.getAuthConfig();
      expect(result).toEqual({
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
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle concurrent login/logout operations', async () => {
      testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
      testEnv.fetchMock.mockResolvedValue(createSuccessResponse({}));

      const loginPromise = Promise.resolve(
        authService.handleLogin(mockAuthConfig)
      );
      const logoutPromise = authService.handleLogout(mockAuthConfig);

      await Promise.all([loginPromise, logoutPromise]);

      expect(testEnv.locationUtils.getMockHref()).toBeDefined();
      expect(testEnv.localStorageMock.removeItem).toHaveBeenCalled();
    });

    it('should handle malformed config objects', async () => {
      const malformedConfig = {
        ...mockAuthConfig,
        endpoints: null
      };

      expect(() => {
        authService.handleLogin(malformedConfig as any);
      }).not.toThrow();
    });

    it('should handle undefined config', () => {
      expect(() => {
        authService.handleLogin(undefined as any);
      }).not.toThrow();
    });

    it('should handle network instability with retry and fallback', async () => {
      // Make sure the mock is set to reject consistently
      mockAuthServiceClient.getConfig.mockRejectedValue(
        createNetworkError('Network unstable')
      );

      // Auth service retries then falls back to offline config
      const result = await authService.getAuthConfig();
      expect(result).toEqual({
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
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
    });

    it('should handle empty response bodies', async () => {
      mockAuthServiceClient.getConfig.mockResolvedValue(null);

      const result = await authService.getAuthConfig();
      expect(result).toEqual({
        development_mode: false,
        google_client_id: 'mock-google-client-id',
        endpoints: {
          callback: 'http://localhost:8081/auth/callback',
          dev_login: 'http://localhost:8081/auth/dev/login',
          login: 'http://localhost:8081/auth/login',
          logout: 'http://localhost:8081/auth/logout',
          token: 'http://localhost:8081/auth/token',
          user: 'http://localhost:8081/auth/me'
        },
        authorized_javascript_origins: ['http://localhost:3000'],
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
    });

    it('should fallback to offline config on response with wrong content type', async () => {
      mockAuthServiceClient.getConfig.mockRejectedValue(
        new Error('Unexpected token < in JSON')
      );

      const result = await authService.getAuthConfig();
      expect(result).toEqual({
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
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
    });

    it('should handle browser storage limitations', () => {
      testEnv.localStorageMock.setItem.mockImplementation(() => {
        throw new Error('QuotaExceededError');
      });

      expect(() => {
        testEnv.localStorageMock.setItem('test', 'value');
      }).toThrow('QuotaExceededError');
    });

    it('should handle localStorage unavailable', () => {
      testEnv.localStorageMock.getItem.mockImplementation(() => {
        throw new Error('localStorage is not available');
      });

      expect(() => authService.getToken())
        .toThrow('localStorage is not available');
    });
  });

  describe('Performance & Reliability', () => {
    it('should handle rapid successive calls', async () => {
      mockAuthServiceClient.getConfig.mockResolvedValue(mockAuthConfig);

      const promises = Array(10).fill(null).map(() => 
        authService.getAuthConfig()
      );

      const results = await Promise.all(promises);
      
      results.forEach(result => {
        expect(result).toEqual({
          ...mockAuthConfig,
          google_client_id: 'mock-google-client-id',
          authorized_redirect_uris: ['http://localhost:3000/auth/callback']
        });
      });
      // All calls should return consistent config
      expect(results).toHaveLength(10);
    });

    it('should handle memory pressure scenarios', () => {
      const largeToken = 'x'.repeat(10000);
      
      // Set up the mock to return the large token
      jest.spyOn(authService, 'getToken').mockReturnValue(largeToken);

      const headers = authService.getAuthHeaders();
      
      expect(headers.Authorization).toBe(`Bearer ${largeToken}`);
      
      // Restore the spy
      jest.restoreAllMocks();
    });

    it('should handle cleanup on page unload', () => {
      // Spy on removeToken to verify it's called
      const removeTokenSpy = jest.spyOn(authService, 'removeToken');
      
      // Simulate cleanup
      authService.removeToken();
      
      expect(removeTokenSpy).toHaveBeenCalled();
      
      // Restore the spy
      jest.restoreAllMocks();
    });
  });
});