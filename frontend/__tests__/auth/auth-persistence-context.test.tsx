/**
 * Test Suite: AuthContext Initialization and Token Persistence
 * Tests initialization state tracking and environment-aware refresh scheduling
 */

import React from 'react';
import { render, waitFor, act, renderHook } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/auth/context';
import { unifiedAuthService } from '@/auth/unified-auth-service';
import { jwtDecode } from 'jwt-decode';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock dependencies
jest.mock('@/auth/unified-auth-service');
jest.mock('jwt-decode');
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn()
  }
}));
jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    login: jest.fn(),
    logout: jest.fn()
  })
}));
jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: () => ({
    trackLogin: jest.fn(),
    trackLogout: jest.fn(),
    trackOAuthComplete: jest.fn(),
    trackError: jest.fn()
  })
}));

describe('AuthContext - Persistence and Initialization', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  const mockAuthService = unifiedAuthService as jest.Mocked<typeof unifiedAuthService>;
  const mockDecode = jwtDecode as jest.MockedFunction<typeof jwtDecode>;

  // Helper to create test tokens
  const createToken = (lifetimeSeconds: number, userId: string = 'test-user') => {
    const now = Math.floor(Date.now() / 1000);
    return {
      exp: now + lifetimeSeconds,
      iat: now,
      sub: userId,
      email: `${userId}@example.com`,
      full_name: 'Test User'
    };
  };

  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('Initialization State Tracking', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should start with loading=true and initialized=false', () => {
      mockAuthService.getAuthConfig.mockResolvedValue({
        development_mode: false,
        google_client_id: 'test-client-id',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
          callback: '/auth/callback',
          token: '/auth/token',
          user: '/auth/me'
        },
        authorized_javascript_origins: ['http://localhost:3000'],
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });

      const { result } = renderHook(() => useAuth(), {
        wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>
      });

      // Initial state
      expect(result.current.loading).toBe(true);
      expect(result.current.initialized).toBe(false);
      expect(result.current.user).toBeNull();
    });

    it('should set initialized=true after auth config loads', async () => {
      mockAuthService.getAuthConfig.mockResolvedValue({
        development_mode: false,
        google_client_id: 'test-client-id',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
          callback: '/auth/callback',
          token: '/auth/token',
          user: '/auth/me'
        },
        authorized_javascript_origins: ['http://localhost:3000'],
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
      mockAuthService.getToken.mockReturnValue(null);

      const { result } = renderHook(() => useAuth(), {
        wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
        expect(result.current.initialized).toBe(true);
      });
    });

    it('should restore token from localStorage on mount', async () => {
      const token = 'stored.jwt.token';
      const decodedUser = createToken(900, 'stored-user'); // 15-minute token
      
      // Set token in localStorage before mounting
      localStorage.setItem('jwt_token', token);
      
      mockAuthService.getAuthConfig.mockResolvedValue({
        development_mode: false,
        google_client_id: 'test-client-id',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
          callback: '/auth/callback',
          token: '/auth/token',
          user: '/auth/me'
        },
        authorized_javascript_origins: ['http://localhost:3000'],
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
      
      mockAuthService.getToken.mockReturnValue(token);
      mockDecode.mockReturnValue(decodedUser);

      const { result } = renderHook(() => useAuth(), {
        wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>
      });

      await waitFor(() => {
        expect(result.current.initialized).toBe(true);
        expect(result.current.user).toEqual(decodedUser);
        expect(result.current.token).toBe(token);
      });
    });

    it('should handle expired token on initialization', async () => {
      const expiredToken = 'expired.jwt.token';
      const expiredUser = createToken(-100, 'expired-user'); // Expired 100 seconds ago
      
      localStorage.setItem('jwt_token', expiredToken);
      
      mockAuthService.getAuthConfig.mockResolvedValue({
        development_mode: false,
        google_client_id: 'test-client-id',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
          callback: '/auth/callback',
          token: '/auth/token',
          user: '/auth/me'
        },
        authorized_javascript_origins: ['http://localhost:3000'],
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
      
      mockAuthService.getToken.mockReturnValue(expiredToken);
      mockDecode.mockReturnValue(expiredUser);
      mockAuthService.needsRefresh.mockReturnValue(true);
      mockAuthService.refreshToken.mockRejectedValue(new Error('Token expired'));

      const { result } = renderHook(() => useAuth(), {
        wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>
      });

      await waitFor(() => {
        expect(result.current.initialized).toBe(true);
        expect(result.current.user).toBeNull(); // Expired token should be cleared
        expect(mockAuthService.removeToken).toHaveBeenCalled();
      });
    });
  });

  describe('Environment-Aware Refresh Scheduling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should schedule refresh every 10 seconds for 30-second tokens', async () => {
      const shortToken = 'short.jwt.token';
      const shortUser = createToken(30, 'short-user'); // 30-second token
      
      localStorage.setItem('jwt_token', shortToken);
      
      mockAuthService.getAuthConfig.mockResolvedValue({
        development_mode: false,
        google_client_id: 'test-client-id',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
          callback: '/auth/callback',
          token: '/auth/token',
          user: '/auth/me'
        },
        authorized_javascript_origins: ['http://localhost:3000'],
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
      
      mockAuthService.getToken.mockReturnValue(shortToken);
      mockDecode.mockReturnValue(shortUser);
      mockAuthService.needsRefresh.mockReturnValue(false);

      renderHook(() => useAuth(), {
        wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>
      });

      // Fast-forward 10 seconds
      await act(async () => {
        jest.advanceTimersByTime(10000);
      });

      // Should have checked for refresh
      expect(mockAuthService.needsRefresh).toHaveBeenCalledWith(shortToken);

      // Fast-forward another 10 seconds
      await act(async () => {
        jest.advanceTimersByTime(10000);
      });

      // Should check again
      expect(mockAuthService.needsRefresh).toHaveBeenCalledTimes(2);
    });

    it('should schedule refresh every 2 minutes for 15-minute tokens', async () => {
      const normalToken = 'normal.jwt.token';
      const normalUser = createToken(900, 'normal-user'); // 15-minute token
      
      localStorage.setItem('jwt_token', normalToken);
      
      mockAuthService.getAuthConfig.mockResolvedValue({
        development_mode: false,
        google_client_id: 'test-client-id',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
          callback: '/auth/callback',
          token: '/auth/token',
          user: '/auth/me'
        },
        authorized_javascript_origins: ['http://localhost:3000'],
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
      
      mockAuthService.getToken.mockReturnValue(normalToken);
      mockDecode.mockReturnValue(normalUser);
      mockAuthService.needsRefresh.mockReturnValue(false);

      renderHook(() => useAuth(), {
        wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>
      });

      // Fast-forward 10 seconds - should NOT check yet
      await act(async () => {
        jest.advanceTimersByTime(10000);
      });
      expect(mockAuthService.needsRefresh).not.toHaveBeenCalled();

      // Fast-forward to 2 minutes total
      await act(async () => {
        jest.advanceTimersByTime(110000); // Additional 110 seconds
      });

      // Should have checked for refresh
      expect(mockAuthService.needsRefresh).toHaveBeenCalledWith(normalToken);
    });

    it('should refresh token when needsRefresh returns true', async () => {
      const token = 'needs.refresh.token';
      const user = createToken(30, 'test-user');
      const newToken = 'refreshed.token';
      const newUser = createToken(30, 'test-user');
      
      localStorage.setItem('jwt_token', token);
      
      mockAuthService.getAuthConfig.mockResolvedValue({
        development_mode: false,
        google_client_id: 'test-client-id',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
          callback: '/auth/callback',
          token: '/auth/token',
          user: '/auth/me'
        },
        authorized_javascript_origins: ['http://localhost:3000'],
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
      
      mockAuthService.getToken.mockReturnValue(token);
      mockDecode.mockReturnValueOnce(user).mockReturnValueOnce(newUser);
      mockAuthService.needsRefresh.mockReturnValue(true);
      mockAuthService.refreshToken.mockResolvedValue({
        access_token: newToken,
        token_type: 'Bearer'
      });

      const { result } = renderHook(() => useAuth(), {
        wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>
      });

      await waitFor(() => {
        expect(result.current.initialized).toBe(true);
      });

      // Trigger refresh check
      await act(async () => {
        jest.advanceTimersByTime(10000);
      });

      await waitFor(() => {
        expect(mockAuthService.refreshToken).toHaveBeenCalled();
        expect(result.current.token).toBe(newToken);
      });
    });
  });

  describe('Storage Event Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should update auth state when token changes in another tab', async () => {
      const initialToken = 'initial.token';
      const initialUser = createToken(900, 'initial-user');
      const newToken = 'new.token.from.other.tab';
      const newUser = createToken(900, 'new-user');
      
      mockAuthService.getAuthConfig.mockResolvedValue({
        development_mode: false,
        google_client_id: 'test-client-id',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
          callback: '/auth/callback',
          token: '/auth/token',
          user: '/auth/me'
        },
        authorized_javascript_origins: ['http://localhost:3000'],
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
      
      mockAuthService.getToken.mockReturnValue(initialToken);
      mockDecode.mockReturnValueOnce(initialUser).mockReturnValueOnce(newUser);

      const { result } = renderHook(() => useAuth(), {
        wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>
      });

      await waitFor(() => {
        expect(result.current.initialized).toBe(true);
        expect(result.current.user?.sub).toBe('initial-user');
      });

      // Simulate storage event from another tab
      await act(async () => {
        const storageEvent = new StorageEvent('storage', {
          key: 'jwt_token',
          newValue: newToken,
          oldValue: initialToken,
          storageArea: localStorage
        });
        window.dispatchEvent(storageEvent);
      });

      await waitFor(() => {
        expect(result.current.token).toBe(newToken);
        expect(result.current.user?.sub).toBe('new-user');
      });
    });

    it('should handle token removal from another tab', async () => {
      const token = 'initial.token';
      const user = createToken(900, 'test-user');
      
      localStorage.setItem('jwt_token', token);
      
      mockAuthService.getAuthConfig.mockResolvedValue({
        development_mode: false,
        google_client_id: 'test-client-id',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
          callback: '/auth/callback',
          token: '/auth/token',
          user: '/auth/me'
        },
        authorized_javascript_origins: ['http://localhost:3000'],
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
      
      mockAuthService.getToken.mockReturnValue(token);
      mockDecode.mockReturnValue(user);

      const { result } = renderHook(() => useAuth(), {
        wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>
      });

      await waitFor(() => {
        expect(result.current.user).not.toBeNull();
      });

      // Simulate token removal from another tab
      await act(async () => {
        const storageEvent = new StorageEvent('storage', {
          key: 'jwt_token',
          newValue: null,
          oldValue: token,
          storageArea: localStorage
        });
        window.dispatchEvent(storageEvent);
      });

      // Note: Current implementation only handles new tokens, not removal
      // This test documents the current behavior
      expect(result.current.user).not.toBeNull(); // User remains logged in
    });
  });

  describe('Error Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle malformed tokens gracefully', async () => {
      const malformedToken = 'malformed.token';
      
      localStorage.setItem('jwt_token', malformedToken);
      
      mockAuthService.getAuthConfig.mockResolvedValue({
        development_mode: false,
        google_client_id: 'test-client-id',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
          callback: '/auth/callback',
          token: '/auth/token',
          user: '/auth/me'
        },
        authorized_javascript_origins: ['http://localhost:3000'],
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
      
      mockAuthService.getToken.mockReturnValue(malformedToken);
      mockDecode.mockImplementation(() => {
        throw new Error('Invalid token');
      });

      const { result } = renderHook(() => useAuth(), {
        wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>
      });

      await waitFor(() => {
        expect(result.current.initialized).toBe(true);
        expect(result.current.user).toBeNull();
        expect(mockAuthService.removeToken).toHaveBeenCalled();
      });
    });

    it('should handle auth config fetch failure gracefully', async () => {
      mockAuthService.getAuthConfig.mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useAuth(), {
        wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
        expect(result.current.initialized).toBe(true);
        expect(result.current.authConfig).not.toBeNull(); // Should have offline config
      });
    });

    it('should continue with existing token if refresh fails', async () => {
      const token = 'current.token';
      const user = createToken(30, 'test-user');
      
      localStorage.setItem('jwt_token', token);
      
      mockAuthService.getAuthConfig.mockResolvedValue({
        development_mode: false,
        google_client_id: 'test-client-id',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
          callback: '/auth/callback',
          token: '/auth/token',
          user: '/auth/me'
        },
        authorized_javascript_origins: ['http://localhost:3000'],
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      });
      
      mockAuthService.getToken.mockReturnValue(token);
      mockDecode.mockReturnValue(user);
      mockAuthService.needsRefresh.mockReturnValue(true);
      mockAuthService.refreshToken.mockRejectedValue(new Error('Refresh failed'));

      const { result } = renderHook(() => useAuth(), {
        wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>
      });

      await waitFor(() => {
        expect(result.current.initialized).toBe(true);
      });

      // Trigger refresh
      await act(async () => {
        jest.advanceTimersByTime(10000);
      });

      // User should remain logged in despite refresh failure
      await waitFor(() => {
        expect(result.current.user).not.toBeNull();
        expect(result.current.token).toBe(token);
      });
    });
  });
});