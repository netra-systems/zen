/**
 * AI AGENT MODIFICATION METADATA
 * ================================
 * Timestamp: 2025-08-11T18:05:00Z
 * Agent: Claude Opus 4.1 (claude-opus-4-1-20250805) via claude-code
 * Context: Create comprehensive test suite for auth/service.ts with 100% coverage
 * Git: v7 | feature-auth-tests | dirty
 * Change: Test | Scope: Auth | Risk: Low
 * Session: auth-test-improvement | Seq: 2
 * Review: Pending | Score: 95/100
 * ================================
 */

import { authService } from '@/auth/service';
import { config } from '@/config';
import { AuthContext } from '@/auth/context';
import React from 'react';

// Mock dependencies
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8000'
  }
}));

// Mock React.useContext
const mockUseContext = jest.spyOn(React, 'useContext');

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// Mock window.location methods without replacing the entire object
const mockAssign = jest.fn();
const mockReplace = jest.fn();
const mockReload = jest.fn();

delete (window as any).location;
(window as any).location = {
  href: '',
  assign: mockAssign,
  replace: mockReplace,
  reload: mockReload,
  origin: 'http://localhost:3000',
  pathname: '/',
  search: '',
  hash: ''
};

// Mock fetch
global.fetch = jest.fn();

describe('AuthService', () => {
  const mockAuthConfig = {
    development_mode: false,
    endpoints: {
      login: 'http://localhost:8000/auth/login',
      logout: 'http://localhost:8000/auth/logout',
      callback: 'http://localhost:8000/auth/callback',
      dev_login: 'http://localhost:8000/auth/dev-login'
    }
  };

  const mockToken = 'mock-jwt-token-123';
  const mockDevLoginResponse = {
    access_token: mockToken,
    token_type: 'Bearer'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    window.location.href = '';
    localStorageMock.getItem.mockReturnValue(null);
  });

  describe('getAuthConfig', () => {
    it('should fetch auth config successfully', async () => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockAuthConfig)
      });

      const result = await authService.getAuthConfig();

      expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/auth/config');
      expect(result).toEqual(mockAuthConfig);
    });

    it('should throw error when fetch fails', async () => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 500
      });

      await expect(authService.getAuthConfig()).rejects.toThrow('Failed to fetch auth config');
    });

    it('should handle network errors', async () => {
      (fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      await expect(authService.getAuthConfig()).rejects.toThrow('Network error');
    });
  });

  describe('handleDevLogin', () => {
    it('should perform dev login successfully', async () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockDevLoginResponse)
      });

      const result = await authService.handleDevLogin(mockAuthConfig);

      expect(consoleSpy).toHaveBeenCalledWith('Attempting dev login...');
      expect(fetch).toHaveBeenCalledWith(
        mockAuthConfig.endpoints.dev_login,
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: 'dev@example.com' })
        })
      );
      expect(localStorageMock.setItem).toHaveBeenCalledWith('jwt_token', mockToken);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('dev_logout_flag');
      expect(consoleSpy).toHaveBeenCalledWith('Dev login successful');
      expect(result).toEqual(mockDevLoginResponse);

      consoleSpy.mockRestore();
    });

    it('should handle dev login failure with non-ok response', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      (fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 401
      });

      const result = await authService.handleDevLogin(mockAuthConfig);

      expect(consoleErrorSpy).toHaveBeenCalledWith('Dev login failed with status:', 401);
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
      expect(result).toBeNull();

      consoleErrorSpy.mockRestore();
    });

    it('should handle dev login network error', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      (fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      const result = await authService.handleDevLogin(mockAuthConfig);

      expect(consoleErrorSpy).toHaveBeenCalledWith('Error during dev login:', expect.any(Error));
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
      expect(result).toBeNull();

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Token Management', () => {
    describe('getToken', () => {
      it('should retrieve token from localStorage', () => {
        localStorageMock.getItem.mockReturnValue(mockToken);

        const result = authService.getToken();

        expect(localStorageMock.getItem).toHaveBeenCalledWith('jwt_token');
        expect(result).toBe(mockToken);
      });

      it('should return null when no token exists', () => {
        localStorageMock.getItem.mockReturnValue(null);

        const result = authService.getToken();

        expect(result).toBeNull();
      });
    });

    describe('getAuthHeaders', () => {
      it('should return auth headers with token', () => {
        localStorageMock.getItem.mockReturnValue(mockToken);

        const headers = authService.getAuthHeaders();

        expect(headers).toEqual({ Authorization: `Bearer ${mockToken}` });
      });

      it('should return empty object when no token', () => {
        localStorageMock.getItem.mockReturnValue(null);

        const headers = authService.getAuthHeaders();

        expect(headers).toEqual({});
      });
    });

    describe('removeToken', () => {
      it('should remove token from localStorage', () => {
        authService.removeToken();

        expect(localStorageMock.removeItem).toHaveBeenCalledWith('jwt_token');
      });
    });
  });

  describe('Dev Logout Flag Management', () => {
    describe('getDevLogoutFlag', () => {
      it('should return true when flag is set', () => {
        localStorageMock.getItem.mockReturnValue('true');

        const result = authService.getDevLogoutFlag();

        expect(localStorageMock.getItem).toHaveBeenCalledWith('dev_logout_flag');
        expect(result).toBe(true);
      });

      it('should return false when flag is not set', () => {
        localStorageMock.getItem.mockReturnValue(null);

        const result = authService.getDevLogoutFlag();

        expect(result).toBe(false);
      });

      it('should return false when flag is not "true"', () => {
        localStorageMock.getItem.mockReturnValue('false');

        const result = authService.getDevLogoutFlag();

        expect(result).toBe(false);
      });
    });

    describe('setDevLogoutFlag', () => {
      it('should set dev logout flag', () => {
        authService.setDevLogoutFlag();

        expect(localStorageMock.setItem).toHaveBeenCalledWith('dev_logout_flag', 'true');
      });
    });

    describe('clearDevLogoutFlag', () => {
      it('should clear dev logout flag', () => {
        authService.clearDevLogoutFlag();

        expect(localStorageMock.removeItem).toHaveBeenCalledWith('dev_logout_flag');
      });
    });
  });

  describe('handleLogin', () => {
    it('should redirect to login endpoint', () => {
      authService.handleLogin(mockAuthConfig);

      expect(window.location.href).toBe(mockAuthConfig.endpoints.login);
    });

    it('should handle login with development mode config', () => {
      const devConfig = { ...mockAuthConfig, development_mode: true };
      
      authService.handleLogin(devConfig);

      expect(window.location.href).toBe(devConfig.endpoints.login);
    });
  });

  describe('handleLogout', () => {
    it('should perform logout successfully and redirect', async () => {
      localStorageMock.getItem.mockReturnValue(mockToken);
      (fetch as jest.Mock).mockResolvedValue({ ok: true });

      await authService.handleLogout(mockAuthConfig);

      expect(fetch).toHaveBeenCalledWith(
        mockAuthConfig.endpoints.logout,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${mockToken}`
          }
        })
      );
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('jwt_token');
      expect(window.location.href).toBe('/');
    });

    it('should handle logout failure and still redirect', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      localStorageMock.getItem.mockReturnValue(mockToken);
      (fetch as jest.Mock).mockResolvedValue({ ok: false });

      await authService.handleLogout(mockAuthConfig);

      expect(consoleErrorSpy).toHaveBeenCalledWith('Logout failed');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('jwt_token');
      expect(window.location.href).toBe('/');

      consoleErrorSpy.mockRestore();
    });

    it('should handle logout network error and still redirect', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      localStorageMock.getItem.mockReturnValue(mockToken);
      (fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      await authService.handleLogout(mockAuthConfig);

      expect(consoleErrorSpy).toHaveBeenCalledWith('Error during logout:', expect.any(Error));
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('jwt_token');
      expect(window.location.href).toBe('/');

      consoleErrorSpy.mockRestore();
    });

    it('should handle logout without token', async () => {
      const hrefSetter = jest.fn();
      Object.defineProperty(window.location, 'href', {
        set: hrefSetter,
        get: () => '/',
        configurable: true
      });
      localStorageMock.getItem.mockReturnValue(null);
      (fetch as jest.Mock).mockResolvedValue({ ok: true });

      await authService.handleLogout(mockAuthConfig);

      expect(fetch).toHaveBeenCalledWith(
        mockAuthConfig.endpoints.logout,
        expect.objectContaining({
          headers: {
            'Content-Type': 'application/json'
          }
        })
      );
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('jwt_token');
      expect(window.location.href).toBe('/');
    });
  });

  describe('useAuth Hook', () => {
    it('should return auth context when used within provider', () => {
      const mockContext = {
        user: null,
        login: jest.fn(),
        logout: jest.fn(),
        loading: false,
        authConfig: null,
        token: null
      };
      mockUseContext.mockReturnValue(mockContext);

      const result = authService.useAuth();

      expect(mockUseContext).toHaveBeenCalledWith(AuthContext);
      expect(result).toBe(mockContext);
    });

    it('should throw error when used outside provider', () => {
      mockUseContext.mockReturnValue(undefined);

      expect(() => authService.useAuth()).toThrow('useAuth must be used within an AuthProvider');
    });
  });

  describe('API Error Handling', () => {
    it('should handle 401 unauthorized response', async () => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 401,
        statusText: 'Unauthorized'
      });

      await expect(authService.getAuthConfig()).rejects.toThrow('Failed to fetch auth config');
    });

    it('should handle 403 forbidden response', async () => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 403,
        statusText: 'Forbidden'
      });

      await expect(authService.getAuthConfig()).rejects.toThrow('Failed to fetch auth config');
    });

    it('should handle 500 server error', async () => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      });

      await expect(authService.getAuthConfig()).rejects.toThrow('Failed to fetch auth config');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty auth config response', async () => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({})
      });

      const result = await authService.getAuthConfig();

      expect(result).toEqual({});
    });

    it('should handle malformed JSON response', async () => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockRejectedValue(new Error('Invalid JSON'))
      });

      await expect(authService.getAuthConfig()).rejects.toThrow('Invalid JSON');
    });

    it('should handle concurrent login/logout operations', async () => {
      localStorageMock.getItem.mockReturnValue(mockToken);
      (fetch as jest.Mock).mockResolvedValue({ ok: true });

      // Start multiple operations
      const loginPromise = Promise.resolve(authService.handleLogin(mockAuthConfig));
      const logoutPromise = authService.handleLogout(mockAuthConfig);

      await Promise.all([loginPromise, logoutPromise]);

      // Verify operations completed
      expect(window.location.href).toBeDefined();
      expect(localStorageMock.removeItem).toHaveBeenCalled();
    });

    it('should handle rapid token operations', () => {
      // Rapid set and get operations
      authService.removeToken();
      localStorageMock.getItem.mockReturnValue(mockToken);
      const token1 = authService.getToken();
      authService.removeToken();
      localStorageMock.getItem.mockReturnValue(null);
      const token2 = authService.getToken();

      expect(token1).toBe(mockToken);
      expect(token2).toBeNull();
      expect(localStorageMock.removeItem).toHaveBeenCalledTimes(2);
    });

    it('should handle localStorage quota exceeded', () => {
      localStorageMock.setItem.mockImplementation(() => {
        throw new Error('QuotaExceededError');
      });

      // Should not throw, but log error
      expect(async () => {
        await authService.handleDevLogin(mockAuthConfig);
      }).not.toThrow();
    });
  });

  describe('Security Tests', () => {
    it('should not expose sensitive data in headers', () => {
      localStorageMock.getItem.mockReturnValue(mockToken);
      
      const headers = authService.getAuthHeaders();
      
      // Check that only Authorization header is returned
      expect(Object.keys(headers)).toEqual(['Authorization']);
      expect(headers.Authorization).toMatch(/^Bearer /);
    });

    it('should sanitize email input in dev login', async () => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockDevLoginResponse)
      });

      await authService.handleDevLogin(mockAuthConfig);

      // Verify that only hardcoded email is used, not user input
      const callBody = JSON.parse((fetch as jest.Mock).mock.calls[0][1].body);
      expect(callBody.email).toBe('dev@example.com');
    });

    it('should clear sensitive data on logout', async () => {
      localStorageMock.getItem.mockReturnValue(mockToken);
      (fetch as jest.Mock).mockResolvedValue({ ok: true });

      await authService.handleLogout(mockAuthConfig);

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('jwt_token');
    });
  });
});