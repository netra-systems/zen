import { render, screen, fireEvent, waitFor, renderHook, act } from '@testing-library/react';
import { useAuth } from '../../auth/context';
import { AuthProvider } from '../../auth/AuthProvider';
import LoginPage from '../../app/login/page';
import { useRouter } from 'next/navigation';
import jwt from 'jwt-decode';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  usePathname: jest.fn(),
}));

// Mock jwt-decode
jest.mock('jwt-decode');

describe('Authentication Flow Tests', () => {
  const mockRouter = {
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  };

  beforeEach(() => {
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('Login Flow', () => {
    it('should handle successful login with JWT token', async () => {
      const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature';
      const mockDecodedToken = {
        sub: 'user123',
        email: 'test@netra.ai',
        exp: Math.floor(Date.now() / 1000) + 3600,
        roles: ['user', 'admin'],
      };

      (jwt as jest.Mock).mockReturnValue(mockDecodedToken);

      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: mockToken,
          user: {
            id: 'user123',
            email: 'test@netra.ai',
            name: 'Test User',
          },
        }),
      });

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await act(async () => {
        await result.current.login('test@netra.ai', 'password123');
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual({
        id: 'user123',
        email: 'test@netra.ai',
        name: 'Test User',
      });
      expect(localStorage.getItem('auth_token')).toBe(mockToken);
      expect(mockRouter.push).toHaveBeenCalledWith('/dashboard');
    });

    it('should handle failed login with proper error messages', async () => {
      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({
          detail: 'Invalid credentials',
        }),
      });

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await act(async () => {
        try {
          await result.current.login('test@netra.ai', 'wrongpassword');
        } catch (error) {
          expect(error.message).toBe('Invalid credentials');
        }
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(localStorage.getItem('auth_token')).toBeNull();
    });

    it('should handle OAuth login flow', async () => {
      const mockOAuthToken = 'oauth_token_123';
      const mockOAuthUser = {
        id: 'oauth_user_123',
        email: 'oauth@netra.ai',
        name: 'OAuth User',
        provider: 'google',
      };

      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: mockOAuthToken,
          user: mockOAuthUser,
        }),
      });

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await act(async () => {
        await result.current.loginWithOAuth('google', 'oauth_code_123');
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(mockOAuthUser);
      expect(result.current.authProvider).toBe('google');
    });
  });

  describe('Token Management', () => {
    it('should refresh token before expiration', async () => {
      const initialToken = 'initial_token';
      const refreshedToken = 'refreshed_token';
      
      const mockDecodedToken = {
        exp: Math.floor(Date.now() / 1000) + 300, // Expires in 5 minutes
      };

      (jwt as jest.Mock).mockReturnValue(mockDecodedToken);

      global.fetch = jest.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ access_token: initialToken }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ access_token: refreshedToken }),
        });

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      // Initial login
      await act(async () => {
        await result.current.login('test@netra.ai', 'password');
      });

      // Wait for auto-refresh (should happen 1 minute before expiry)
      await waitFor(() => {
        expect(localStorage.getItem('auth_token')).toBe(refreshedToken);
      }, { timeout: 5000 });
    });

    it('should handle token expiration and redirect to login', async () => {
      const expiredToken = 'expired_token';
      const mockDecodedToken = {
        exp: Math.floor(Date.now() / 1000) - 3600, // Expired 1 hour ago
      };

      (jwt as jest.Mock).mockReturnValue(mockDecodedToken);
      localStorage.setItem('auth_token', expiredToken);

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(false);
        expect(mockRouter.replace).toHaveBeenCalledWith('/login');
      });
    });

    it('should validate token structure and signature', async () => {
      const malformedTokens = [
        'not.a.token',
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9', // Missing parts
        '...', // All empty parts
        null,
        undefined,
        '',
      ];

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      for (const token of malformedTokens) {
        act(() => {
          const isValid = result.current.validateToken(token);
          expect(isValid).toBe(false);
        });
      }
    });
  });

  describe('Session Persistence', () => {
    it('should persist session across page refreshes', async () => {
      const mockToken = 'persistent_token';
      const mockUser = {
        id: 'user123',
        email: 'test@netra.ai',
        name: 'Test User',
      };

      localStorage.setItem('auth_token', mockToken);
      localStorage.setItem('auth_user', JSON.stringify(mockUser));

      const { result, rerender } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true);
        expect(result.current.user).toEqual(mockUser);
      });

      // Simulate page refresh
      rerender();

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(mockUser);
    });

    it('should handle multi-tab synchronization', async () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      // Simulate login in another tab
      const storageEvent = new StorageEvent('storage', {
        key: 'auth_token',
        newValue: 'new_token_from_other_tab',
        oldValue: null,
        storageArea: localStorage,
      });

      act(() => {
        window.dispatchEvent(storageEvent);
      });

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true);
      });
    });
  });

  describe('Logout Flow', () => {
    it('should clear all auth data on logout', async () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      // Setup authenticated state
      await act(async () => {
        await result.current.login('test@netra.ai', 'password');
      });

      expect(result.current.isAuthenticated).toBe(true);

      // Logout
      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(localStorage.getItem('auth_token')).toBeNull();
      expect(sessionStorage.getItem('auth_session')).toBeNull();
      expect(mockRouter.replace).toHaveBeenCalledWith('/login');
    });

    it('should revoke tokens on server during logout', async () => {
      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Logged out successfully' }),
      });

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      });

      await act(async () => {
        await result.current.logout();
      });

      expect(global.fetch).toHaveBeenCalledWith('/api/auth/logout', {
        method: 'POST',
        headers: expect.objectContaining({
          'Authorization': expect.stringContaining('Bearer'),
        }),
      });
    });
  });
});