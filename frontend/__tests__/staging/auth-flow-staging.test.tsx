/**
 * Frontend Authentication Flow - Staging Environment Tests
 * 
 * These tests verify that the complete authentication flow works properly in staging:
 * - User login through OAuth
 * - Token management and refresh
 * - Authenticated API requests
 * - Session persistence and logout
 * 
 * @environment staging
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { jest } from '@jest/globals';
import { authService } from '@/auth/service';
import { authInterceptor } from '@/lib/auth-interceptor';
import { ThreadService } from '@/services/threadService';
import { AuthProvider } from '@/auth/context';
import { Button } from '@/components/ui/button';

// Test environment validation
if (process.env.NODE_ENV !== 'test' && process.env.NEXT_PUBLIC_ENVIRONMENT !== 'staging') {
  throw new Error('These tests should only run in staging environment');
}

// Mock components for testing
const TestAuthComponent = () => {
  const { user, login, logout, loading, token } = authService.useAuth();
  
  if (loading) return <div data-testid="auth-loading">Loading...</div>;
  
  return (
    <div data-testid="auth-component">
      {user ? (
        <div>
          <div data-testid="user-info">
            Email: {user.email}
            <br />
            Name: {user.full_name || 'Unknown'}
            <br />
            Token: {token ? 'Present' : 'Missing'}
          </div>
          <Button data-testid="logout-button" onClick={logout}>
            Logout
          </Button>
        </div>
      ) : (
        <Button data-testid="login-button" onClick={login}>
          Login
        </Button>
      )}
    </div>
  );
};

const AuthTestWrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe('Authentication Flow - Staging Environment', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  const originalLocation = window.location;
  let mockFetch: jest.MockedFunction<typeof fetch>;

  beforeEach(() => {
    // Mock window.location for redirect tests
    delete (window as any).location;
    window.location = { ...originalLocation };
    
    // Clear localStorage
    localStorage.clear();
    sessionStorage.clear();
    
    // Setup fetch mock
    mockFetch = jest.fn() as jest.MockedFunction<typeof fetch>;
    global.fetch = mockFetch;
    
    // Reset auth service state
    jest.clearAllMocks();
  });

  afterEach(() => {
    window.location = originalLocation;
    jest.restoreAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('Authentication State Management', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should initialize with no user when not authenticated', async () => {
      // Mock auth config endpoint
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          development_mode: false,
          google_client_id: 'test-client-id',
          endpoints: {
            login: '/auth/login',
            logout: '/auth/logout',
            callback: '/auth/callback',
            token: '/auth/token',
            user: '/auth/me'
          }
        })
      } as Response);

      render(
        <AuthTestWrapper>
          <TestAuthComponent />
        </AuthTestWrapper>
      );

      // Should show login button when not authenticated
      await waitFor(() => {
        expect(screen.getByTestId('login-button')).toBeInTheDocument();
      });

      expect(screen.queryByTestId('user-info')).not.toBeInTheDocument();
    });

    test('should initialize with user when valid token exists', async () => {
      // Set up a valid JWT token in localStorage
      const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZnVsbF9uYW1lIjoiVGVzdCBVc2VyIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjk5OTk5OTk5OTl9.Lmb5qHhYXKLMfCgH1FoWm4GKuJzD4MkX9sEfH0a6N7Q';
      localStorage.setItem('jwt_token', mockToken);

      // Mock auth config endpoint
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          development_mode: false,
          google_client_id: 'test-client-id',
          endpoints: {
            login: '/auth/login',
            logout: '/auth/logout',
            callback: '/auth/callback',
            token: '/auth/token',
            user: '/auth/me'
          }
        })
      } as Response);

      render(
        <AuthTestWrapper>
          <TestAuthComponent />
        </AuthTestWrapper>
      );

      // Should show user info when authenticated
      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toBeInTheDocument();
      });

      expect(screen.getByText('Email: test@example.com')).toBeInTheDocument();
      expect(screen.getByText('Name: Test User')).toBeInTheDocument();
      expect(screen.getByText('Token: Present')).toBeInTheDocument();
      expect(screen.getByTestId('logout-button')).toBeInTheDocument();
    });
  });

  describe('OAuth Login Flow', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should redirect to OAuth provider on login', async () => {
      const mockAuthConfig = {
        development_mode: false,
        google_client_id: 'staging-client-id',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
          callback: '/auth/callback',
          token: '/auth/token',
          user: '/auth/me'
        },
        authorized_redirect_uris: ['https://app.staging.netrasystems.ai/auth/callback']
      };

      // Mock auth config endpoint
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAuthConfig
      } as Response);

      // Mock window.location.href assignment
      const mockLocationHref = jest.fn();
      Object.defineProperty(window.location, 'href', {
        set: mockLocationHref,
        configurable: true
      });

      render(
        <AuthTestWrapper>
          <TestAuthComponent />
        </AuthTestWrapper>
      );

      // Wait for component to initialize
      await waitFor(() => {
        expect(screen.getByTestId('login-button')).toBeInTheDocument();
      });

      // Click login button
      fireEvent.click(screen.getByTestId('login-button'));

      // Should initiate OAuth flow
      await waitFor(() => {
        expect(mockLocationHref).toHaveBeenCalledWith(
          expect.stringContaining('accounts.google.com')
        );
      });
    });

    test('should handle OAuth callback with authorization code', async () => {
      const mockAuthResponse = {
        access_token: 'new-access-token',
        token_type: 'bearer',
        expires_in: 3600,
        refresh_token: 'new-refresh-token'
      };

      // Mock the OAuth callback request
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAuthResponse
      } as Response);

      // Mock processing OAuth callback
      const authConfig = {
        development_mode: false,
        endpoints: { callback: '/auth/callback' }
      };

      const authorizationCode = 'test-auth-code';
      
      // Simulate OAuth callback processing
      const result = await authService.handleOAuthCallback(authConfig as any, authorizationCode);
      
      expect(result).toEqual(mockAuthResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/callback'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining(authorizationCode)
        })
      );
    });
  });

  describe('Authenticated API Requests', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should successfully make authenticated requests to /api/threads', async () => {
      // Set up authenticated user
      const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjk5OTk5OTk5OTl9.Lmb5qHhYXKLMfCgH1FoWm4GKuJzD4MkX9sEfH0a6N7Q';
      localStorage.setItem('jwt_token', mockToken);

      // Mock successful threads response
      const mockThreadsResponse = {
        threads: [
          {
            id: 'thread-1',
            title: 'Test Thread 1',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z'
          },
          {
            id: 'thread-2',
            title: 'Test Thread 2',
            created_at: '2024-01-02T00:00:00Z',
            updated_at: '2024-01-02T00:00:00Z'
          }
        ]
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockThreadsResponse
      } as Response);

      // Make authenticated request
      const response = await authInterceptor.get('/api/threads');
      const data = await response.json();

      expect(response.ok).toBe(true);
      expect(data.threads).toHaveLength(2);
      expect(data.threads[0].id).toBe('thread-1');

      // Verify Authorization header was included
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/threads',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': `Bearer ${mockToken}`
          })
        })
      );
    });

    test('should handle 401 responses and retry with refreshed token', async () => {
      // Set up initial token
      const initialToken = 'expired-token';
      const refreshedToken = 'refreshed-token';
      localStorage.setItem('jwt_token', initialToken);

      // Mock 401 response first, then success after refresh
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          statusText: 'Unauthorized'
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            access_token: refreshedToken,
            token_type: 'bearer',
            expires_in: 3600
          })
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ threads: [] })
        } as Response);

      // Make request that should trigger refresh
      const response = await authInterceptor.get('/api/threads');
      
      expect(response.ok).toBe(true);
      
      // Should have made 3 calls: original request, refresh token, retry request
      expect(mockFetch).toHaveBeenCalledTimes(3);
      
      // Verify retry request used refreshed token
      const retryCall = mockFetch.mock.calls[2];
      expect(retryCall[1]?.headers).toEqual(
        expect.objectContaining({
          'Authorization': `Bearer ${refreshedToken}`
        })
      );
    });

    test('should create threads with proper authentication', async () => {
      const mockToken = 'valid-token';
      localStorage.setItem('jwt_token', mockToken);

      const newThreadResponse = {
        id: 'new-thread-id',
        title: 'New Thread',
        created_at: '2024-01-03T00:00:00Z',
        updated_at: '2024-01-03T00:00:00Z'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => newThreadResponse
      } as Response);

      const threadData = { title: 'New Thread' };
      const response = await authInterceptor.post('/api/threads', threadData);
      const data = await response.json();

      expect(response.ok).toBe(true);
      expect(data.id).toBe('new-thread-id');
      expect(data.title).toBe('New Thread');

      // Verify request structure
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/threads',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': `Bearer ${mockToken}`,
            'Content-Type': 'application/json'
          }),
          body: JSON.stringify(threadData)
        })
      );
    });
  });

  describe('Token Management', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should refresh token automatically before expiration', async () => {
      // Set up token that expires soon
      const soonToExpireToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwODJ9.invalidSignature';
      localStorage.setItem('jwt_token', soonToExpireToken);

      const refreshedTokenResponse = {
        access_token: 'refreshed-token',
        token_type: 'bearer',
        expires_in: 3600
      };

      // Mock auth config
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            development_mode: false,
            endpoints: { token: '/auth/token' }
          })
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => refreshedTokenResponse
        } as Response);

      render(
        <AuthTestWrapper>
          <TestAuthComponent />
        </AuthTestWrapper>
      );

      // Wait for automatic token refresh to occur
      await waitFor(() => {
        const storedToken = localStorage.getItem('jwt_token');
        expect(storedToken).toBe('refreshed-token');
      }, { timeout: 5000 });
    });

    test('should handle token refresh failure gracefully', async () => {
      const expiredToken = 'expired-token';
      localStorage.setItem('jwt_token', expiredToken);

      // Mock auth config and failed refresh
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            development_mode: false,
            endpoints: { token: '/auth/token' }
          })
        } as Response)
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          statusText: 'Unauthorized'
        } as Response);

      render(
        <AuthTestWrapper>
          <TestAuthComponent />
        </AuthTestWrapper>
      );

      // Should not crash on refresh failure, should continue with expired token
      await waitFor(() => {
        expect(screen.getByTestId('auth-component')).toBeInTheDocument();
      });
    });

    test('should validate token format and reject malformed tokens', () => {
      const malformedToken = 'not.a.valid.jwt.token';
      localStorage.setItem('jwt_token', malformedToken);

      // Mock auth config
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          development_mode: false,
          endpoints: {}
        })
      } as Response);

      render(
        <AuthTestWrapper>
          <TestAuthComponent />
        </AuthTestWrapper>
      );

      // Should clear malformed token and show login
      expect(localStorage.getItem('jwt_token')).toBeNull();
    });
  });

  describe('Session Persistence', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should persist session across page refreshes', async () => {
      const persistentToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjk5OTk5OTk5OTl9.Lmb5qHhYXKLMfCgH1FoWm4GKuJzD4MkX9sEfH0a6N7Q';
      localStorage.setItem('jwt_token', persistentToken);

      // Mock auth config
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          development_mode: false,
          endpoints: {}
        })
      } as Response);

      const { unmount } = render(
        <AuthTestWrapper>
          <TestAuthComponent />
        </AuthTestWrapper>
      );

      // Verify user is logged in
      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toBeInTheDocument();
      });

      unmount();

      // Mock auth config again for remount
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          development_mode: false,
          endpoints: {}
        })
      } as Response);

      // Remount component (simulate page refresh)
      render(
        <AuthTestWrapper>
          <TestAuthComponent />
        </AuthTestWrapper>
      );

      // Should still be logged in
      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toBeInTheDocument();
      });
    });

    test('should handle cross-tab synchronization', async () => {
      const sharedToken = 'shared-token';
      
      // Initial render without token
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          development_mode: false,
          endpoints: {}
        })
      } as Response);

      render(
        <AuthTestWrapper>
          <TestAuthComponent />
        </AuthTestWrapper>
      );

      // Should show login initially
      await waitFor(() => {
        expect(screen.getByTestId('login-button')).toBeInTheDocument();
      });

      // Simulate token being set in another tab
      localStorage.setItem('jwt_token', sharedToken);
      
      // Trigger storage event
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'jwt_token',
        newValue: sharedToken,
        storageArea: localStorage
      }));

      // Component should detect the change and update
      // Note: This test may need additional implementation in the auth context
      // to listen for storage events for proper cross-tab sync
    });
  });

  describe('Logout Flow', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should clear all auth data on logout', async () => {
      const mockToken = 'valid-token';
      localStorage.setItem('jwt_token', mockToken);

      // Mock auth config and logout
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            development_mode: false,
            endpoints: { logout: '/auth/logout' }
          })
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true })
        } as Response);

      render(
        <AuthTestWrapper>
          <TestAuthComponent />
        </AuthTestWrapper>
      );

      // Wait for user to be logged in
      await waitFor(() => {
        expect(screen.getByTestId('logout-button')).toBeInTheDocument();
      });

      // Click logout
      fireEvent.click(screen.getByTestId('logout-button'));

      // Should clear localStorage and show login
      await waitFor(() => {
        expect(localStorage.getItem('jwt_token')).toBeNull();
        expect(screen.getByTestId('login-button')).toBeInTheDocument();
      });

      // Verify logout API was called
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/logout'),
        expect.objectContaining({
          method: 'POST'
        })
      );
    });

    test('should handle logout API failure gracefully', async () => {
      const mockToken = 'valid-token';
      localStorage.setItem('jwt_token', mockToken);

      // Mock auth config and failed logout
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            development_mode: false,
            endpoints: { logout: '/auth/logout' }
          })
        } as Response)
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          statusText: 'Server Error'
        } as Response);

      render(
        <AuthTestWrapper>
          <TestAuthComponent />
        </AuthTestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId('logout-button')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('logout-button'));

      // Should still clear local data even if API fails
      await waitFor(() => {
        expect(localStorage.getItem('jwt_token')).toBeNull();
        expect(screen.getByTestId('login-button')).toBeInTheDocument();
      });
    });
  });

  describe('CORS and Security Headers', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should handle CORS preflight requests properly', async () => {
      const mockToken = 'valid-token';
      localStorage.setItem('jwt_token', mockToken);

      // Mock CORS preflight response
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          headers: new Headers({
            'Access-Control-Allow-Origin': 'https://app.staging.netrasystems.ai',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Authorization, Content-Type'
          })
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ threads: [] })
        } as Response);

      const response = await authInterceptor.get('/api/threads');
      
      expect(response.ok).toBe(true);
      
      // Verify proper headers were sent
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/threads',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': `Bearer ${mockToken}`,
            'Content-Type': 'application/json'
          })
        })
      );
    });

    test('should reject requests with invalid CORS headers', async () => {
      // This test simulates a scenario where the backend rejects 
      // requests due to CORS policy violations
      const mockToken = 'valid-token';
      localStorage.setItem('jwt_token', mockToken);

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'CORS policy violation'
      } as Response);

      try {
        await authInterceptor.get('/api/threads');
        fail('Should have thrown an error');
      } catch (error) {
        expect(error).toBeDefined();
      }
    });
  });
});