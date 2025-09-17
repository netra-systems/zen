/**
 * BULLETPROOF: Auth Context Edge Cases Test Suite
 * 
 * Comprehensive edge case testing to ensure auth initialization
 * NEVER fails again. These tests cover every possible scenario
 * that could break chat initialization.
 * 
 * CHAT IS KING - We cannot afford auth failures.
 * 
 * @compliance type_safety.xml - Strongly typed test suite
 * @compliance CLAUDE.md - Chat is 90% of value delivery
 */

import React from 'react';
import { render, screen, waitFor, act, renderHook } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/auth/context';
import { AuthGuard } from '@/components/AuthGuard';
import { unifiedAuthService } from '@/auth/unified-auth-service';
// jwt-decode removed - using auth service for token handling
import { User } from '@/types';

// Mock dependencies
jest.mock('@/auth/unified-auth-service');
// jwt-decode mock removed - auth service handles token parsing
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
  }),
}));
jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));
jest.mock('@/lib/logger');
jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: () => ({
    trackLogin: jest.fn(),
    trackLogout: jest.fn(),
    trackOAuthComplete: jest.fn(),
    trackError: jest.fn(),
    trackPageView: jest.fn(),
  }),
}));

const generateMockUser = (overrides?: Partial<User>): User => ({
  id: 'user_123',
  email: 'test@example.com',
  full_name: 'Test User',
  exp: Math.floor(Date.now() / 1000) + 3600,
  ...overrides,
});

const generateMockToken = (user?: Partial<User>): string => {
  const payload = generateMockUser(user);
  return `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${btoa(JSON.stringify(payload))}.signature`;
};

describe('BULLETPROOF: Auth Initialization Edge Cases', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    document.cookie = '';
  });

  describe('Critical Race Conditions', () => {
    test('handles simultaneous token updates from multiple sources', async () => {
      const token1 = generateMockToken({ email: 'user1@example.com' });
      const token2 = generateMockToken({ email: 'user2@example.com' });
      const token3 = generateMockToken({ email: 'user3@example.com' });
      
      // Mock auth service to return user info for different tokens
      (unifiedAuthService.getCurrentUser as jest.Mock).mockImplementation(() => {
        const token = (unifiedAuthService.getToken as jest.Mock)();
        if (token === token1) return generateMockUser({ email: 'user1@example.com' });
        if (token === token2) return generateMockUser({ email: 'user2@example.com' });
        if (token === token3) return generateMockUser({ email: 'user3@example.com' });
        return null;
      });
      
      const { rerender } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      // Simulate rapid token updates from different sources
      await act(async () => {
        // WebSocket update
        localStorage.setItem('jwt_token', token1);
        (unifiedAuthService.getToken as jest.Mock).mockReturnValue(token1);
        
        // OAuth callback
        await new Promise(resolve => setTimeout(resolve, 10));
        localStorage.setItem('jwt_token', token2);
        (unifiedAuthService.getToken as jest.Mock).mockReturnValue(token2);
        
        // Manual refresh
        await new Promise(resolve => setTimeout(resolve, 10));
        localStorage.setItem('jwt_token', token3);
        (unifiedAuthService.getToken as jest.Mock).mockReturnValue(token3);
      });
      
      // Final state should be consistent with last token
      await waitFor(() => {
        const userState = screen.getByTestId('user-state').textContent;
        expect(userState).toBe('user3@example.com');
      });
    });

    test('handles token update during component unmount/remount', async () => {
      const token1 = generateMockToken();
      localStorage.setItem('jwt_token', token1);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(token1);
      (jwtDecode as jest.Mock).mockReturnValue(generateMockUser());
      
      const { unmount, rerender } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('test@example.com');
      });
      
      // Unmount during token update
      const token2 = generateMockToken({ email: 'updated@example.com' });
      localStorage.setItem('jwt_token', token2);
      unmount();
      
      // Remount with new token
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(token2);
      (jwtDecode as jest.Mock).mockReturnValue(generateMockUser({ email: 'updated@example.com' }));
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('updated@example.com');
      });
    });
  });

  describe('Storage Corruption Scenarios', () => {
    test('handles malformed token in localStorage', async () => {
      // Set corrupted token
      localStorage.setItem('jwt_token', 'corrupted.token.here');
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue('corrupted.token.here');
      (jwtDecode as jest.Mock).mockImplementation(() => {
        throw new Error('Invalid token');
      });
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('null');
        expect(screen.getByTestId('initialized-state')).toHaveTextContent('true');
      });
      
      // Verify token was cleaned up
      expect(unifiedAuthService.removeToken).toHaveBeenCalled();
    });

    test('handles localStorage quota exceeded during token save', async () => {
      const mockToken = generateMockToken();
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(null);
      
      // Mock localStorage.setItem to throw quota exceeded
      const originalSetItem = Storage.prototype.setItem;
      Storage.prototype.setItem = jest.fn().mockImplementation(() => {
        throw new DOMException('QuotaExceededError');
      });
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      // Try to set token (should handle error gracefully)
      await act(async () => {
        try {
          localStorage.setItem('jwt_token', mockToken);
        } catch (e) {
          // Should be caught and handled
        }
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('null');
      });
      
      Storage.prototype.setItem = originalSetItem;
    });

    test('handles localStorage disabled/blocked by browser', async () => {
      // Simulate localStorage being blocked
      const originalLocalStorage = global.localStorage;
      Object.defineProperty(global, 'localStorage', {
        get: () => {
          throw new Error('localStorage is not available');
        },
        configurable: true,
      });
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('initialized-state')).toHaveTextContent('true');
        expect(screen.getByTestId('user-state')).toHaveTextContent('null');
      });
      
      Object.defineProperty(global, 'localStorage', {
        value: originalLocalStorage,
        configurable: true,
      });
    });
  });

  describe('Network and Timing Issues', () => {
    test('handles auth config fetch timeout', async () => {
      const mockToken = generateMockToken();
      localStorage.setItem('jwt_token', mockToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(mockToken);
      (jwtDecode as jest.Mock).mockReturnValue(generateMockUser());
      
      // Mock auth config to never resolve
      (unifiedAuthService.getAuthConfig as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      // Should still initialize with token from localStorage
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('test@example.com');
      }, { timeout: 3000 });
    });

    test('handles token refresh during network failure', async () => {
      const expiredToken = generateMockToken({ 
        exp: Math.floor(Date.now() / 1000) - 3600 
      });
      
      localStorage.setItem('jwt_token', expiredToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(expiredToken);
      (jwtDecode as jest.Mock).mockReturnValue(generateMockUser({ 
        exp: Math.floor(Date.now() / 1000) - 3600 
      }));
      
      // Mock refresh to fail with network error
      (unifiedAuthService.refreshToken as jest.Mock).mockRejectedValue(
        new Error('Network error')
      );
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      await waitFor(() => {
        // Should handle gracefully without crashing
        expect(screen.getByTestId('initialized-state')).toHaveTextContent('true');
      });
    });
  });

  describe('Browser-Specific Scenarios', () => {
    test('handles Safari private browsing mode', async () => {
      // Simulate Safari private browsing (localStorage throws on setItem)
      const originalSetItem = Storage.prototype.setItem;
      Storage.prototype.setItem = jest.fn().mockImplementation(() => {
        throw new Error('localStorage not available in private browsing');
      });
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('initialized-state')).toHaveTextContent('true');
        expect(screen.getByTestId('user-state')).toHaveTextContent('null');
      });
      
      Storage.prototype.setItem = originalSetItem;
    });

    test('handles Firefox strict mode cookie blocking', async () => {
      // Simulate blocked third-party cookies
      const mockToken = generateMockToken();
      
      // localStorage works but cookies don't
      localStorage.setItem('jwt_token', mockToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(mockToken);
      (jwtDecode as jest.Mock).mockReturnValue(generateMockUser());
      
      Object.defineProperty(document, 'cookie', {
        set: jest.fn().mockImplementation(() => {
          throw new Error('Cookies blocked');
        }),
        configurable: true,
      });
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      // Should still work with localStorage
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('test@example.com');
      });
    });
  });

  describe('Multiple Tab Synchronization', () => {
    test('handles storage events from other tabs', async () => {
      const initialToken = generateMockToken();
      localStorage.setItem('jwt_token', initialToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(initialToken);
      (jwtDecode as jest.Mock).mockReturnValue(generateMockUser());
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('test@example.com');
      });
      
      // Simulate storage event from another tab
      const newToken = generateMockToken({ email: 'newtab@example.com' });
      const storageEvent = new StorageEvent('storage', {
        key: 'jwt_token',
        oldValue: initialToken,
        newValue: newToken,
        storageArea: localStorage,
      });
      
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(newToken);
      (jwtDecode as jest.Mock).mockReturnValue(generateMockUser({ email: 'newtab@example.com' }));
      
      act(() => {
        window.dispatchEvent(storageEvent);
      });
      
      // Should update to new token
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('newtab@example.com');
      });
    });

    test('handles logout in another tab', async () => {
      const mockToken = generateMockToken();
      localStorage.setItem('jwt_token', mockToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(mockToken);
      (jwtDecode as jest.Mock).mockReturnValue(generateMockUser());
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('test@example.com');
      });
      
      // Simulate logout in another tab
      const storageEvent = new StorageEvent('storage', {
        key: 'jwt_token',
        oldValue: mockToken,
        newValue: null,
        storageArea: localStorage,
      });
      
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(null);
      
      act(() => {
        window.dispatchEvent(storageEvent);
      });
      
      // Should clear user
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('null');
      });
    });
  });

  describe('Token Validation Edge Cases', () => {
    test('handles token with missing required fields', async () => {
      const incompleteToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature';
      localStorage.setItem('jwt_token', incompleteToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(incompleteToken);
      (jwtDecode as jest.Mock).mockReturnValue({ sub: '1234567890' }); // Missing email, exp, etc.
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      await waitFor(() => {
        // Should handle incomplete token gracefully
        expect(screen.getByTestId('initialized-state')).toHaveTextContent('true');
      });
    });

    test('handles token with future iat (issued at time)', async () => {
      const futureToken = generateMockToken({
        iat: Math.floor(Date.now() / 1000) + 3600, // Issued 1 hour in future
        exp: Math.floor(Date.now() / 1000) + 7200, // Expires 2 hours in future
      });
      
      localStorage.setItem('jwt_token', futureToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(futureToken);
      (jwtDecode as jest.Mock).mockReturnValue(generateMockUser({
        iat: Math.floor(Date.now() / 1000) + 3600,
        exp: Math.floor(Date.now() / 1000) + 7200,
      }));
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      await waitFor(() => {
        // Should reject future-issued tokens
        expect(screen.getByTestId('user-state')).toHaveTextContent('null');
      });
    });

    test('handles extremely long tokens', async () => {
      // Create a token with very large payload
      const largePayload = {
        ...generateMockUser(),
        data: 'x'.repeat(10000), // 10KB of data
      };
      const largeToken = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${btoa(JSON.stringify(largePayload))}.signature`;
      
      localStorage.setItem('jwt_token', largeToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(largeToken);
      (jwtDecode as jest.Mock).mockReturnValue(largePayload);
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('test@example.com');
      });
    });
  });

  describe('Component Lifecycle Edge Cases', () => {
    test('handles rapid mount/unmount cycles', async () => {
      const mockToken = generateMockToken();
      localStorage.setItem('jwt_token', mockToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(mockToken);
      (jwtDecode as jest.Mock).mockReturnValue(generateMockUser());
      
      // Rapidly mount and unmount
      for (let i = 0; i < 5; i++) {
        const { unmount } = render(
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        );
        
        await waitFor(() => {
          expect(screen.getByTestId('user-state')).toHaveTextContent('test@example.com');
        });
        
        unmount();
      }
      
      // Final mount should still work
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('test@example.com');
      });
    });

    test('handles StrictMode double rendering', async () => {
      const mockToken = generateMockToken();
      localStorage.setItem('jwt_token', mockToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(mockToken);
      (jwtDecode as jest.Mock).mockReturnValue(generateMockUser());
      
      let renderCount = 0;
      const CountingComponent = () => {
        renderCount++;
        return <TestComponent />;
      };
      
      render(
        <React.StrictMode>
          <AuthProvider>
            <CountingComponent />
          </AuthProvider>
        </React.StrictMode>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('test@example.com');
      });
      
      // StrictMode causes double rendering in development
      expect(renderCount).toBeGreaterThanOrEqual(2);
    });
  });

  describe('AuthGuard Integration Edge Cases', () => {
    test('handles AuthGuard with changing authentication state', async () => {
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(null);
      
      const { rerender } = render(
        <AuthProvider>
          <AuthGuard>
            <div data-testid="protected-content">Protected</div>
          </AuthGuard>
        </AuthProvider>
      );
      
      // Initially not authenticated
      await waitFor(() => {
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      });
      
      // Simulate login
      const mockToken = generateMockToken();
      act(() => {
        localStorage.setItem('jwt_token', mockToken);
        (unifiedAuthService.getToken as jest.Mock).mockReturnValue(mockToken);
        (jwtDecode as jest.Mock).mockReturnValue(generateMockUser());
      });
      
      rerender(
        <AuthProvider>
          <AuthGuard>
            <div data-testid="protected-content">Protected</div>
          </AuthGuard>
        </AuthProvider>
      );
      
      // Should now show protected content
      await waitFor(() => {
        expect(screen.getByTestId('protected-content')).toBeInTheDocument();
      });
    });

    test('handles nested AuthGuards', async () => {
      const mockToken = generateMockToken();
      localStorage.setItem('jwt_token', mockToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(mockToken);
      (jwtDecode as jest.Mock).mockReturnValue(generateMockUser());
      
      render(
        <AuthProvider>
          <AuthGuard>
            <div data-testid="outer-content">
              Outer
              <AuthGuard>
                <div data-testid="inner-content">Inner</div>
              </AuthGuard>
            </div>
          </AuthGuard>
        </AuthProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('outer-content')).toBeInTheDocument();
        expect(screen.getByTestId('inner-content')).toBeInTheDocument();
      });
    });
  });
});

// Test helper component
const TestComponent: React.FC = () => {
  const { user, token, initialized, loading } = useAuth();
  return (
    <div>
      <div data-testid="user-state">{user ? user.email : 'null'}</div>
      <div data-testid="token-state">{token ? 'present' : 'null'}</div>
      <div data-testid="initialized-state">{initialized ? 'true' : 'false'}</div>
      <div data-testid="loading-state">{loading ? 'true' : 'false'}</div>
    </div>
  );
};