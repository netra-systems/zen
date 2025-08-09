import { authService } from '@/auth/service';
import jwt from 'jsonwebtoken';

// Mock fetch and jwt
global.fetch = jest.fn();
jest.mock('jsonwebtoken');

describe('AuthService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('JWT Token Management', () => {
    it('should store and retrieve access token', () => {
      const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature';
      
      authService.setToken(token);
      expect(authService.getToken()).toBe(token);
      expect(localStorage.getItem('access_token')).toBe(token);
    });

    it('should decode JWT token to get user info', () => {
      const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature';
      const decodedPayload = {
        sub: 'user-123',
        email: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour from now
      };

      (jwt.decode as jest.Mock).mockReturnValue(decodedPayload);

      const userInfo = authService.getUserFromToken(token);
      
      expect(jwt.decode).toHaveBeenCalledWith(token);
      expect(userInfo).toEqual({
        id: 'user-123',
        email: 'test@example.com',
      });
    });

    it('should detect expired tokens', () => {
      const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.expired.signature';
      const expiredPayload = {
        sub: 'user-123',
        email: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) - 3600, // 1 hour ago
      };

      (jwt.decode as jest.Mock).mockReturnValue(expiredPayload);

      expect(authService.isTokenExpired(expiredToken)).toBe(true);
    });

    it('should handle invalid tokens gracefully', () => {
      (jwt.decode as jest.Mock).mockReturnValue(null);

      const userInfo = authService.getUserFromToken('invalid-token');
      expect(userInfo).toBeNull();
    });
  });

  describe('Authentication Flow', () => {
    it('should login with email and password', async () => {
      const mockResponse = {
        access_token: 'new-token',
        refresh_token: 'refresh-token',
        user: {
          id: 'user-123',
          email: 'test@example.com',
        },
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await authService.login('test@example.com', 'password123');

      expect(fetch).toHaveBeenCalledWith('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: 'test@example.com',
          password: 'password123',
        }),
      });

      expect(result).toEqual(mockResponse);
      expect(localStorage.getItem('access_token')).toBe('new-token');
      expect(localStorage.getItem('refresh_token')).toBe('refresh-token');
    });

    it('should handle login errors', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid credentials' }),
      });

      await expect(
        authService.login('test@example.com', 'wrong-password')
      ).rejects.toThrow('Invalid credentials');

      expect(localStorage.getItem('access_token')).toBeNull();
    });

    it('should logout and clear tokens', async () => {
      // Set tokens first
      localStorage.setItem('access_token', 'token-to-remove');
      localStorage.setItem('refresh_token', 'refresh-to-remove');

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

      await authService.logout();

      expect(fetch).toHaveBeenCalledWith('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer token-to-remove',
        },
      });

      expect(localStorage.getItem('access_token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
    });
  });

  describe('Token Refresh', () => {
    it('should refresh access token using refresh token', async () => {
      localStorage.setItem('refresh_token', 'valid-refresh-token');

      const mockResponse = {
        access_token: 'new-access-token',
        user: { id: 'user-123', email: 'test@example.com' },
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await authService.refreshToken();

      expect(fetch).toHaveBeenCalledWith('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: 'valid-refresh-token',
        }),
      });

      expect(result).toEqual(mockResponse);
      expect(localStorage.getItem('access_token')).toBe('new-access-token');
    });

    it('should auto-refresh token before expiry', async () => {
      jest.useFakeTimers();

      const token = 'expiring-token';
      const tokenPayload = {
        sub: 'user-123',
        exp: Math.floor(Date.now() / 1000) + 300, // 5 minutes from now
      };

      (jwt.decode as jest.Mock).mockReturnValue(tokenPayload);
      authService.setToken(token);

      const mockRefreshResponse = {
        access_token: 'refreshed-token',
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockRefreshResponse,
      });

      authService.setupTokenRefresh();

      // Fast forward to just before token expiry
      jest.advanceTimersByTime(4 * 60 * 1000); // 4 minutes

      await Promise.resolve(); // Let promises resolve

      expect(fetch).toHaveBeenCalledWith('/api/auth/refresh', expect.any(Object));

      jest.useRealTimers();
    });
  });

  describe('Auth Headers', () => {
    it('should provide auth headers for API requests', () => {
      authService.setToken('test-token');

      const headers = authService.getAuthHeaders();

      expect(headers).toEqual({
        'Authorization': 'Bearer test-token',
      });
    });

    it('should return empty headers when not authenticated', () => {
      const headers = authService.getAuthHeaders();
      expect(headers).toEqual({});
    });
  });

  describe('Development Mode', () => {
    it('should handle dev mode auto-login', async () => {
      const devAuthData = {
        authenticated: false,
        development_mode: true,
        dev_user: {
          email: 'dev@example.com',
          id: 'dev-user',
        },
      };

      const mockDevLoginResponse = {
        access_token: 'dev-token',
        user: devAuthData.dev_user,
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockDevLoginResponse,
      });

      const result = await authService.handleDevLogin(devAuthData);

      expect(fetch).toHaveBeenCalledWith('/api/auth/dev-login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      expect(result).toEqual(mockDevLoginResponse);
      expect(localStorage.getItem('access_token')).toBe('dev-token');
    });
  });

  describe('Session Management', () => {
    it('should check authentication status', async () => {
      authService.setToken('valid-token');

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          authenticated: true,
          user: { id: 'user-123', email: 'test@example.com' },
        }),
      });

      const status = await authService.checkAuth();

      expect(fetch).toHaveBeenCalledWith('/api/auth/check', {
        headers: {
          'Authorization': 'Bearer valid-token',
        },
      });

      expect(status.authenticated).toBe(true);
      expect(status.user).toEqual({
        id: 'user-123',
        email: 'test@example.com',
      });
    });

    it('should handle session timeout', async () => {
      authService.setToken('expired-token');

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Token expired' }),
      });

      const status = await authService.checkAuth();

      expect(status.authenticated).toBe(false);
      expect(localStorage.getItem('access_token')).toBeNull();
    });
  });

  describe('Security', () => {
    it('should sanitize tokens before storage', () => {
      const maliciousToken = '<script>alert("xss")</script>token';
      authService.setToken(maliciousToken);

      const stored = localStorage.getItem('access_token');
      expect(stored).not.toContain('<script>');
    });

    it('should validate token format', () => {
      const invalidTokens = [
        '',
        'not.a.token',
        'only.two',
        '...',
        null,
        undefined,
      ];

      invalidTokens.forEach(token => {
        expect(authService.isValidTokenFormat(token)).toBe(false);
      });

      const validToken = 'header.payload.signature';
      expect(authService.isValidTokenFormat(validToken)).toBe(true);
    });
  });
});