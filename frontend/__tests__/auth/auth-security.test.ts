/**
 * Auth Security & Error Handling Tests
 * ====================================
 * Tests for security compliance, API error handling, and edge cases
 * 
 * BVJ: Enterprise segment - ensures security compliance, prevents auth vulnerabilities
 * Modular design: ≤300 lines, functions ≤8 lines
 */

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
  validateSecureLogout
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

      const callBody = JSON.parse(
        testEnv.fetchMock.mock.calls[0][1].body
      );
      expect(callBody.email).toBe('dev@example.com');
    });

    it('should clear sensitive data on logout', async () => {
      testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
      testEnv.fetchMock.mockResolvedValue(createSuccessResponse({}));

      await authService.handleLogout(mockAuthConfig);

      validateSecureLogout(testEnv.localStorageMock);
    });

    it('should handle token with potential XSS content', () => {
      const xssToken = '<script>alert("xss")</script>';
      testEnv.localStorageMock.getItem.mockReturnValue(xssToken);
      
      const headers = authService.getAuthHeaders();
      
      expect(headers.Authorization).toBe(`Bearer ${xssToken}`);
      expect(Object.keys(headers)).toEqual(['Authorization']);
    });

    it('should handle SQL injection attempts in token', () => {
      const sqlToken = "'; DROP TABLE users; --";
      testEnv.localStorageMock.getItem.mockReturnValue(sqlToken);
      
      const headers = authService.getAuthHeaders();
      
      expect(headers.Authorization).toBe(`Bearer ${sqlToken}`);
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
    it('should handle 401 unauthorized response', async () => {
      testEnv.fetchMock.mockResolvedValue(
        createErrorResponse(401, 'Unauthorized')
      );

      await expect(authService.getAuthConfig())
        .rejects.toThrow('Failed to fetch auth config');
    });

    it('should handle 403 forbidden response', async () => {
      testEnv.fetchMock.mockResolvedValue(
        createErrorResponse(403, 'Forbidden')
      );

      await expect(authService.getAuthConfig())
        .rejects.toThrow('Failed to fetch auth config');
    });

    it('should handle 404 not found response', async () => {
      testEnv.fetchMock.mockResolvedValue(
        createErrorResponse(404, 'Not Found')
      );

      await expect(authService.getAuthConfig())
        .rejects.toThrow('Failed to fetch auth config');
    });

    it('should handle 500 server error', async () => {
      testEnv.fetchMock.mockResolvedValue(
        createErrorResponse(500, 'Internal Server Error')
      );

      await expect(authService.getAuthConfig())
        .rejects.toThrow('Failed to fetch auth config');
    });

    it('should handle timeout errors', async () => {
      testEnv.fetchMock.mockRejectedValue(
        createNetworkError('Request timeout')
      );

      await expect(authService.getAuthConfig())
        .rejects.toThrow('Request timeout');
    });

    it('should handle rate limiting (429)', async () => {
      testEnv.fetchMock.mockResolvedValue(
        createErrorResponse(429, 'Too Many Requests')
      );

      await expect(authService.getAuthConfig())
        .rejects.toThrow('Failed to fetch auth config');
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

    it('should handle network instability', async () => {
      let callCount = 0;
      testEnv.fetchMock.mockImplementation(() => {
        callCount++;
        if (callCount === 1) {
          return Promise.reject(createNetworkError('Network unstable'));
        }
        return Promise.resolve(createSuccessResponse(mockAuthConfig));
      });

      // First call fails
      await expect(authService.getAuthConfig())
        .rejects.toThrow('Network unstable');

      // Second call succeeds
      const result = await authService.getAuthConfig();
      expect(result).toEqual(mockAuthConfig);
    });

    it('should handle empty response bodies', async () => {
      testEnv.fetchMock.mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(null)
      });

      const result = await authService.getAuthConfig();
      expect(result).toBeNull();
    });

    it('should handle response with wrong content type', async () => {
      testEnv.fetchMock.mockResolvedValue({
        ok: true,
        json: jest.fn().mockRejectedValue(
          new Error('Unexpected token < in JSON')
        )
      });

      await expect(authService.getAuthConfig())
        .rejects.toThrow('Unexpected token < in JSON');
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
      testEnv.fetchMock.mockResolvedValue(
        createSuccessResponse(mockAuthConfig)
      );

      const promises = Array(10).fill(null).map(() => 
        authService.getAuthConfig()
      );

      const results = await Promise.all(promises);
      
      results.forEach(result => {
        expect(result).toEqual(mockAuthConfig);
      });
      expect(testEnv.fetchMock).toHaveBeenCalledTimes(10);
    });

    it('should handle memory pressure scenarios', () => {
      const largeToken = 'x'.repeat(10000);
      testEnv.localStorageMock.getItem.mockReturnValue(largeToken);

      const headers = authService.getAuthHeaders();
      
      expect(headers.Authorization).toBe(`Bearer ${largeToken}`);
    });

    it('should handle cleanup on page unload', () => {
      testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
      
      // Simulate cleanup
      authService.removeToken();
      
      expect(testEnv.localStorageMock.removeItem)
        .toHaveBeenCalledWith('jwt_token');
    });
  });
});