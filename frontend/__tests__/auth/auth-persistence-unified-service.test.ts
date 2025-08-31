/**
 * Test Suite: UnifiedAuthService Token Refresh Logic
 * Tests environment-aware token refresh thresholds and dynamic scheduling
 */

import { UnifiedAuthService } from '@/auth/unified-auth-service';
import { jwtDecode } from 'jwt-decode';

// Mock dependencies
jest.mock('jwt-decode');
jest.mock('@/lib/auth-service-client');
jest.mock('@/lib/unified-api-config', () => ({
  unifiedApiConfig: {
    environment: 'test',
    urls: {
      auth: 'http://localhost:8001',
      frontend: 'http://localhost:3000'
    },
    endpoints: {
      authLogin: '/auth/login',
      authLogout: '/auth/logout',
      authCallback: '/auth/callback',
      authToken: '/auth/token',
      authMe: '/auth/me'
    }
  }
}));

describe('UnifiedAuthService - Auth Persistence', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let service: UnifiedAuthService;
  const mockDecode = jwtDecode as jest.MockedFunction<typeof jwtDecode>;

  beforeEach(() => {
    service = new UnifiedAuthService();
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('needsRefresh - Environment-Aware Thresholds', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should refresh 30-second tokens at 25% lifetime remaining', () => {
      const now = Math.floor(Date.now() / 1000);
      const shortToken = 'short.token.here';
      
      // Mock 30-second token with 10 seconds remaining (66% elapsed, needs refresh)
      mockDecode.mockReturnValue({
        exp: now + 10,
        iat: now - 20,
        sub: 'test-user'
      });

      const needsRefresh = service.needsRefresh(shortToken);
      expect(needsRefresh).toBe(true);
    });

    it('should NOT refresh 30-second tokens at 50% lifetime remaining', () => {
      const now = Math.floor(Date.now() / 1000);
      const shortToken = 'short.token.here';
      
      // Mock 30-second token with 15 seconds remaining (50% elapsed, no refresh yet)
      mockDecode.mockReturnValue({
        exp: now + 15,
        iat: now - 15,
        sub: 'test-user'
      });

      const needsRefresh = service.needsRefresh(shortToken);
      expect(needsRefresh).toBe(false);
    });

    it('should refresh 15-minute tokens 5 minutes before expiry', () => {
      const now = Math.floor(Date.now() / 1000);
      const normalToken = 'normal.token.here';
      
      // Mock 15-minute token with 4 minutes remaining (needs refresh)
      mockDecode.mockReturnValue({
        exp: now + (4 * 60),
        iat: now - (11 * 60),
        sub: 'test-user'
      });

      const needsRefresh = service.needsRefresh(normalToken);
      expect(needsRefresh).toBe(true);
    });

    it('should NOT refresh 15-minute tokens with 10 minutes remaining', () => {
      const now = Math.floor(Date.now() / 1000);
      const normalToken = 'normal.token.here';
      
      // Mock 15-minute token with 10 minutes remaining (no refresh yet)
      mockDecode.mockReturnValue({
        exp: now + (10 * 60),
        iat: now - (5 * 60),
        sub: 'test-user'
      });

      const needsRefresh = service.needsRefresh(normalToken);
      expect(needsRefresh).toBe(false);
    });

    it('should handle tokens without iat field gracefully', () => {
      const now = Math.floor(Date.now() / 1000);
      const tokenNoIat = 'no.iat.token';
      
      // Mock token without iat field, expires in 4 minutes
      mockDecode.mockReturnValue({
        exp: now + (4 * 60),
        sub: 'test-user'
      });

      // Should assume 15-minute lifetime and refresh 5 minutes before expiry
      const needsRefresh = service.needsRefresh(tokenNoIat);
      expect(needsRefresh).toBe(true);
    });

    it('should handle malformed tokens safely', () => {
      const malformedToken = 'malformed.token';
      
      // Mock decode throwing error
      mockDecode.mockImplementation(() => {
        throw new Error('Invalid token');
      });

      // Should return true (err on side of caution)
      const needsRefresh = service.needsRefresh(malformedToken);
      expect(needsRefresh).toBe(true);
    });

    it('should handle tokens without exp field', () => {
      const tokenNoExp = 'no.exp.token';
      
      mockDecode.mockReturnValue({
        iat: Math.floor(Date.now() / 1000),
        sub: 'test-user'
      });

      // Should return false (can't determine expiry)
      const needsRefresh = service.needsRefresh(tokenNoExp);
      expect(needsRefresh).toBe(false);
    });
  });

  describe('Token Storage - SSOT', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should store token in localStorage', () => {
      const token = 'test.jwt.token';
      service.setToken(token);
      
      expect(localStorage.getItem('jwt_token')).toBe(token);
    });

    it('should retrieve token from localStorage', () => {
      const token = 'test.jwt.token';
      localStorage.setItem('jwt_token', token);
      
      const retrieved = service.getToken();
      expect(retrieved).toBe(token);
    });

    it('should remove token from localStorage', () => {
      localStorage.setItem('jwt_token', 'test.token');
      service.removeToken();
      
      expect(localStorage.getItem('jwt_token')).toBeNull();
    });

    it('should return null when no token exists', () => {
      const token = service.getToken();
      expect(token).toBeNull();
    });

    it('should handle localStorage unavailable gracefully', () => {
      // Mock localStorage being undefined (SSR scenario)
      const originalLocalStorage = global.localStorage;
      Object.defineProperty(global, 'localStorage', {
        value: undefined,
        writable: true
      });

      expect(() => service.getToken()).not.toThrow();
      expect(service.getToken()).toBeNull();

      // Restore
      Object.defineProperty(global, 'localStorage', {
        value: originalLocalStorage,
        writable: true
      });
    });
  });

  describe('Auth Headers', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should return Authorization header when token exists', () => {
      const token = 'test.jwt.token';
      service.setToken(token);
      
      const headers = service.getAuthHeaders();
      expect(headers).toEqual({
        Authorization: `Bearer ${token}`
      });
    });

    it('should return empty object when no token', () => {
      const headers = service.getAuthHeaders();
      expect(headers).toEqual({});
    });
  });

  describe('Development Mode Flags', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should set dev logout flag in development mode', () => {
      // Mock development environment
      Object.defineProperty(service, 'environment', {
        value: 'development',
        writable: true
      });

      service.setDevLogoutFlag();
      expect(localStorage.getItem('dev_logout_flag')).toBe('true');
    });

    it('should NOT set dev logout flag in production', () => {
      // Mock production environment
      Object.defineProperty(service, 'environment', {
        value: 'production',
        writable: true
      });

      service.setDevLogoutFlag();
      expect(localStorage.getItem('dev_logout_flag')).toBeNull();
    });

    it('should clear dev logout flag', () => {
      localStorage.setItem('dev_logout_flag', 'true');
      service.clearDevLogoutFlag();
      
      expect(localStorage.getItem('dev_logout_flag')).toBeNull();
    });

    it('should check dev logout flag status', () => {
      localStorage.setItem('dev_logout_flag', 'true');
      expect(service.getDevLogoutFlag()).toBe(true);
      
      service.clearDevLogoutFlag();
      expect(service.getDevLogoutFlag()).toBe(false);
    });
  });

  describe('Edge Cases', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle very short tokens (10 seconds)', () => {
      const now = Math.floor(Date.now() / 1000);
      const veryShortToken = 'very.short.token';
      
      // Mock 10-second token with 5 seconds remaining
      mockDecode.mockReturnValue({
        exp: now + 5,
        iat: now - 5,
        sub: 'test-user'
      });

      // Should need refresh at 50% elapsed
      const needsRefresh = service.needsRefresh(veryShortToken);
      expect(needsRefresh).toBe(false); // 50% elapsed, not yet 75%
    });

    it('should handle very long tokens (1 hour)', () => {
      const now = Math.floor(Date.now() / 1000);
      const longToken = 'long.token.here';
      
      // Mock 1-hour token with 4 minutes remaining
      mockDecode.mockReturnValue({
        exp: now + (4 * 60),
        iat: now - (56 * 60),
        sub: 'test-user'
      });

      // Should need refresh (less than 5 minutes remaining)
      const needsRefresh = service.needsRefresh(longToken);
      expect(needsRefresh).toBe(true);
    });

    it('should handle clock skew gracefully', () => {
      const now = Math.floor(Date.now() / 1000);
      const skewedToken = 'skewed.token';
      
      // Mock token with iat in the future (clock skew)
      mockDecode.mockReturnValue({
        exp: now + 300,
        iat: now + 10, // iat in future indicates clock skew
        sub: 'test-user'
      });

      // Should handle negative lifetime gracefully
      const needsRefresh = service.needsRefresh(skewedToken);
      expect(needsRefresh).toBe(false); // Can't determine lifetime, don't refresh
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});