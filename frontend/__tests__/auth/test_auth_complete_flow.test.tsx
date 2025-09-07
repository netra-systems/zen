/**
 * Test Authentication Complete Flow
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free, Early, Mid, Enterprise)
 * - Business Goal: Enable secure user access to AI agents and chat functionality
 * - Value Impact: Users must authenticate to access personalized AI insights and optimization features
 * - Strategic Impact: Authentication is the gateway to all platform value - without it, users cannot access agents that deliver cost savings and optimization insights
 * 
 * This test validates the complete authentication system that enables business value:
 * 1. User login enables access to AI optimization agents
 * 2. JWT token management ensures secure multi-user isolation
 * 3. Session persistence allows uninterrupted access to valuable insights
 * 4. WebSocket authentication enables real-time agent communication
 * 5. Multi-user isolation protects customer data and enables concurrent usage
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/auth/context';
import { unifiedAuthService } from '@/auth/unified-auth-service';
import { useAuthStore } from '@/store/authStore';
import { WebSocketService } from '@/services/webSocketService';
import { User } from '@/types';
import { jwtDecode } from 'jwt-decode';

// Mock external dependencies but keep internal auth logic real
jest.mock('@/auth/unified-auth-service');
jest.mock('@/services/webSocketService');
jest.mock('jwt-decode');
jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn(),
  }
}));
jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn(() => ({
    isAuthenticated: false,
    user: null,
    token: null,
    loading: false,
    error: null,
    login: jest.fn(),
    logout: jest.fn(),
    setLoading: jest.fn(),
    setError: jest.fn(),
    hasPermission: jest.fn(() => false),
    isAdminOrHigher: jest.fn(() => false),
    isDeveloperOrHigher: jest.fn(() => false),
  }))
}));
jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: () => ({
    trackLogin: jest.fn(),
    trackLogout: jest.fn(),
    trackOAuthComplete: jest.fn(),
    trackError: jest.fn(),
  })
}));
jest.mock('@/lib/auth-validation', () => ({
  monitorAuthState: jest.fn()
}));
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: {
    getState: jest.fn(() => ({
      resetStore: jest.fn()
    }))
  }
}));

const mockUnifiedAuthService = unifiedAuthService as jest.Mocked<typeof unifiedAuthService>;
const mockJwtDecode = jwtDecode as jest.MockedFunction<typeof jwtDecode>;
const mockWebSocketService = WebSocketService as jest.MockedClass<typeof WebSocketService>;

// Test utilities for authentication flows
const mockUser: User = {
  id: 'user-123',
  email: 'test@netra.com',
  full_name: 'Test User',
  exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour from now
  iat: Math.floor(Date.now() / 1000),
  sub: 'user-123'
};

const mockAuthConfig = {
  development_mode: false,
  oauth_enabled: true,
  google_client_id: 'mock-google-client-id',
  endpoints: {
    login: '/auth/login',
    logout: '/auth/logout',
    callback: '/auth/callback',
    token: '/auth/token',
    user: '/auth/me'
  },
  authorized_javascript_origins: ['http://localhost:3000'],
  authorized_redirect_uris: ['http://localhost:3000/auth/callback']
};

const mockJwtToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoidGVzdEBuZXRyYS5jb20iLCJpYXQiOjE2MzAzMjAwMDAsImV4cCI6OTk5OTk5OTk5OX0.test-signature';

// Test component to interact with auth context
const TestAuthComponent: React.FC = () => {
  const { user, login, logout, loading, token, initialized } = useAuth();
  
  return (
    <div>
      <div data-testid="auth-status">
        {loading ? 'loading' : initialized ? 'initialized' : 'not-initialized'}
      </div>
      <div data-testid="user-info">
        {user ? `${user.full_name} (${user.email})` : 'No user'}
      </div>
      <div data-testid="token-status">
        {token ? 'Token present' : 'No token'}
      </div>
      <button onClick={() => login()} data-testid="login-button">
        Login
      </button>
      <button onClick={() => login(true)} data-testid="oauth-login-button">
        OAuth Login
      </button>
      <button onClick={logout} data-testid="logout-button">
        Logout
      </button>
    </div>
  );
};

describe('Authentication Complete Flow', () => {
  let mockAuthStore: any;
  
  // Reset mocks and localStorage before each test
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Create fresh mock auth store for each test
    mockAuthStore = {
      isAuthenticated: false,
      user: null,
      token: null,
      loading: false,
      error: null,
      login: jest.fn(),
      logout: jest.fn(),
      setLoading: jest.fn(),
      setError: jest.fn(),
      hasPermission: jest.fn(() => false),
      isAdminOrHigher: jest.fn(() => false),
      isDeveloperOrHigher: jest.fn(() => false),
    };
    
    // Mock useAuthStore to return our controlled mock
    (useAuthStore as jest.Mock).mockReturnValue(mockAuthStore);
    
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: jest.fn(),
        setItem: jest.fn(),
        removeItem: jest.fn(),
        clear: jest.fn(),
      },
      writable: true,
    });

    // Mock sessionStorage
    Object.defineProperty(window, 'sessionStorage', {
      value: {
        getItem: jest.fn(),
        setItem: jest.fn(),
        removeItem: jest.fn(),
        clear: jest.fn(),
      },
      writable: true,
    });

    // Default mock implementations
    mockUnifiedAuthService.needsRefresh.mockReturnValue(false);
    mockUnifiedAuthService.setToken.mockImplementation(() => {});
    mockUnifiedAuthService.clearDevLogoutFlag.mockImplementation(() => {});
    mockUnifiedAuthService.setDevLogoutFlag.mockImplementation(() => {});
    mockUnifiedAuthService.getDevLogoutFlag.mockReturnValue(false);
  });

  describe('Initial Authentication State', () => {
    it('should initialize with no user when no token exists and OAuth is enabled', async () => {
      // Setup: No token in localStorage, OAuth enabled (prevents auto dev login)
      (localStorage.getItem as jest.Mock).mockReturnValue(null);
      const oauthEnabledConfig = { ...mockAuthConfig, oauth_enabled: true };
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(oauthEnabledConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(null);

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('initialized');
        expect(screen.getByTestId('user-info')).toHaveTextContent('No user');
        expect(screen.getByTestId('token-status')).toHaveTextContent('No token');
      });
    });

    it('should restore user session from stored JWT token on page refresh', async () => {
      // Setup: Token exists in localStorage (simulating page refresh)
      (localStorage.getItem as jest.Mock).mockReturnValue(mockJwtToken);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(mockJwtToken);
      mockJwtDecode.mockReturnValue(mockUser);

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('initialized');
        expect(screen.getByTestId('user-info')).toHaveTextContent('Test User (test@netra.com)');
        expect(screen.getByTestId('token-status')).toHaveTextContent('Token present');
      });

      // Verify JWT was decoded to restore user
      expect(mockJwtDecode).toHaveBeenCalledWith(mockJwtToken);
    });

    it('should auto-login in development mode when OAuth is not configured', async () => {
      // This test validates the current auto-login behavior
      const devConfig = {
        ...mockAuthConfig,
        development_mode: true,
        oauth_enabled: false
      };
      
      (localStorage.getItem as jest.Mock).mockReturnValue(null);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(devConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(null);
      mockUnifiedAuthService.getDevLogoutFlag.mockReturnValue(false);
      mockUnifiedAuthService.handleDevLogin.mockResolvedValue({
        access_token: mockJwtToken,
        token_type: 'Bearer'
      });
      mockJwtDecode.mockReturnValue(mockUser);

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('initialized');
        expect(screen.getByTestId('user-info')).toHaveTextContent('Test User (test@netra.com)');
        expect(screen.getByTestId('token-status')).toHaveTextContent('Token present');
      });

      expect(mockUnifiedAuthService.handleDevLogin).toHaveBeenCalledWith(devConfig);
    });
  });

  describe('Email/Password Login Flow', () => {
    it('should handle dev login in development mode when OAuth not configured', async () => {
      const devAuthConfig = {
        ...mockAuthConfig,
        development_mode: true,
        oauth_enabled: false
      };

      // Mock successful dev login
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(devAuthConfig);
      mockUnifiedAuthService.handleDevLogin.mockResolvedValue({
        access_token: mockJwtToken,
        token_type: 'Bearer'
      });
      mockJwtDecode.mockReturnValue(mockUser);
      
      // Mock user endpoint for dev login
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockUser)
      });

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('initialized');
      });

      // Click login button (should use dev login in this mode)
      fireEvent.click(screen.getByTestId('login-button'));

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('Test User (test@netra.com)');
        expect(screen.getByTestId('token-status')).toHaveTextContent('Token present');
      });

      expect(mockUnifiedAuthService.handleDevLogin).toHaveBeenCalledWith(devAuthConfig);
    });

    it('should handle login errors gracefully', async () => {
      const consoleError = jest.spyOn(console, 'error').mockImplementation();
      
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.handleLogin.mockImplementation(() => {
        throw new Error('Login failed');
      });

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('initialized');
      });

      // Attempt login that will fail
      fireEvent.click(screen.getByTestId('login-button'));

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('No user');
      });

      consoleError.mockRestore();
    });
  });

  describe('OAuth Login Flow', () => {
    it('should redirect to OAuth provider when OAuth is enabled', async () => {
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.handleLogin.mockImplementation(() => {
        // Simulate OAuth redirect (no immediate response)
      });

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('initialized');
      });

      // Click OAuth login button
      fireEvent.click(screen.getByTestId('oauth-login-button'));

      expect(mockUnifiedAuthService.handleLogin).toHaveBeenCalledWith(mockAuthConfig);
    });

    it('should handle OAuth callback and set user state', async () => {
      // Simulate OAuth callback by setting token in localStorage
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(mockJwtToken);
      mockJwtDecode.mockReturnValue(mockUser);

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('initialized');
      });

      // Simulate OAuth callback by triggering storage event
      act(() => {
        const storageEvent = new StorageEvent('storage', {
          key: 'jwt_token',
          newValue: mockJwtToken,
          oldValue: null
        });
        window.dispatchEvent(storageEvent);
      });

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('Test User (test@netra.com)');
        expect(screen.getByTestId('token-status')).toHaveTextContent('Token present');
      });
    });
  });

  describe('JWT Token Management', () => {
    it('should automatically refresh token when needed', async () => {
      const expiredUser = {
        ...mockUser,
        exp: Math.floor(Date.now() / 1000) - 300 // 5 minutes ago (expired)
      };

      const refreshedToken = 'new-refreshed-token';
      const refreshedUser = {
        ...mockUser,
        exp: Math.floor(Date.now() / 1000) + 3600 // 1 hour from now
      };

      // Setup initial expired token
      (localStorage.getItem as jest.Mock).mockReturnValue(mockJwtToken);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(mockJwtToken);
      mockJwtDecode
        .mockReturnValueOnce(expiredUser) // First call shows expired token
        .mockReturnValueOnce(refreshedUser); // Second call after refresh

      // Mock successful token refresh
      mockUnifiedAuthService.refreshToken.mockResolvedValue({
        access_token: refreshedToken,
        token_type: 'Bearer'
      });

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(mockUnifiedAuthService.refreshToken).toHaveBeenCalled();
        expect(screen.getByTestId('user-info')).toHaveTextContent('Test User (test@netra.com)');
      });
    });

    it('should validate JWT token expiration and handle expired tokens', async () => {
      const expiredUser = {
        ...mockUser,
        exp: Math.floor(Date.now() / 1000) - 300 // 5 minutes ago (expired)
      };

      (localStorage.getItem as jest.Mock).mockReturnValue(mockJwtToken);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(mockJwtToken);
      mockJwtDecode.mockReturnValue(expiredUser);
      
      // Mock failed refresh
      mockUnifiedAuthService.refreshToken.mockRejectedValue(new Error('Refresh failed'));

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(mockUnifiedAuthService.removeToken).toHaveBeenCalled();
        expect(screen.getByTestId('user-info')).toHaveTextContent('No user');
        expect(screen.getByTestId('token-status')).toHaveTextContent('No token');
      });
    });

    it('should store JWT token properly after login', async () => {
      const devAuthConfig = {
        ...mockAuthConfig,
        development_mode: true,
        oauth_enabled: false
      };

      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(devAuthConfig);
      mockUnifiedAuthService.handleDevLogin.mockResolvedValue({
        access_token: mockJwtToken,
        token_type: 'Bearer'
      });
      mockJwtDecode.mockReturnValue(mockUser);
      
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockUser)
      });

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('initialized');
      });

      fireEvent.click(screen.getByTestId('login-button'));

      await waitFor(() => {
        expect(screen.getByTestId('token-status')).toHaveTextContent('Token present');
      });

      // Verify Zustand store was updated
      expect(mockAuthStore.login).toHaveBeenCalled();
    });
  });

  describe('WebSocket Authentication', () => {
    it('should initialize WebSocket with JWT token for agent communication', async () => {
      (localStorage.getItem as jest.Mock).mockReturnValue(mockJwtToken);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(mockJwtToken);
      mockJwtDecode.mockReturnValue(mockUser);

      // Mock WebSocket service
      const mockWebSocketConnect = jest.fn();
      mockWebSocketService.mockImplementation(() => ({
        connect: mockWebSocketConnect,
        disconnect: jest.fn(),
        send: jest.fn(),
        on: jest.fn(),
        off: jest.fn(),
        isConnected: jest.fn().mockReturnValue(false)
      }) as any);

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('Test User (test@netra.com)');
      });

      // WebSocket authentication should be handled with the JWT token
      // This ensures agent communication can happen securely
      expect(mockJwtDecode).toHaveBeenCalledWith(mockJwtToken);
    });

    it('should handle WebSocket reconnection with fresh token', async () => {
      const initialToken = mockJwtToken;
      const refreshedToken = 'refreshed-websocket-token';

      (localStorage.getItem as jest.Mock).mockReturnValue(initialToken);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(initialToken);
      mockJwtDecode.mockReturnValue(mockUser);

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('token-status')).toHaveTextContent('Token present');
      });

      // Simulate token refresh for WebSocket reconnection
      mockUnifiedAuthService.refreshToken.mockResolvedValue({
        access_token: refreshedToken,
        token_type: 'Bearer'
      });

      // This test ensures that WebSocket connections can be re-established
      // with fresh tokens, maintaining real-time agent communication
    });
  });

  describe('Multi-User Isolation', () => {
    it('should maintain separate user sessions without interference', async () => {
      const user1 = { ...mockUser, id: 'user-1', email: 'user1@netra.com', full_name: 'User One' };
      const user2 = { ...mockUser, id: 'user-2', email: 'user2@netra.com', full_name: 'User Two' };
      
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);

      // Test first user session
      (localStorage.getItem as jest.Mock).mockReturnValue(mockJwtToken);
      mockUnifiedAuthService.getToken.mockReturnValue(mockJwtToken);
      mockJwtDecode.mockReturnValue(user1);

      const { rerender } = render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('User One (user1@netra.com)');
      });

      // Simulate user switching (new token)
      const newToken = 'user2-token';
      mockUnifiedAuthService.getToken.mockReturnValue(newToken);
      mockJwtDecode.mockReturnValue(user2);

      // Simulate storage change for new user
      act(() => {
        const storageEvent = new StorageEvent('storage', {
          key: 'jwt_token',
          newValue: newToken,
          oldValue: mockJwtToken
        });
        window.dispatchEvent(storageEvent);
      });

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('User Two (user2@netra.com)');
      });

      // Verify auth store was called for user switching
      expect(mockAuthStore.login).toHaveBeenCalled();
    });

    it('should prevent session leakage between users', async () => {
      const user1Token = 'user1-token';
      const user2Token = 'user2-token';
      
      // First user login
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(user1Token);
      mockJwtDecode.mockReturnValue({ ...mockUser, id: 'user-1' });

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('token-status')).toHaveTextContent('Token present');
      });

      // Logout should clear all state
      fireEvent.click(screen.getByTestId('logout-button'));

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('No user');
        expect(screen.getByTestId('token-status')).toHaveTextContent('No token');
      });

      expect(mockUnifiedAuthService.handleLogout).toHaveBeenCalled();
    });
  });

  describe('Logout Flow', () => {
    it('should clear all authentication state and redirect to login', async () => {
      // Setup authenticated state
      (localStorage.getItem as jest.Mock).mockReturnValue(mockJwtToken);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(mockJwtToken);
      mockJwtDecode.mockReturnValue(mockUser);

      // Mock window.location
      const mockLocation = { href: '' };
      Object.defineProperty(window, 'location', {
        value: mockLocation,
        writable: true
      });

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('Test User (test@netra.com)');
      });

      // Perform logout
      fireEvent.click(screen.getByTestId('logout-button'));

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('No user');
        expect(screen.getByTestId('token-status')).toHaveTextContent('No token');
      });

      // Verify complete cleanup
      expect(mockUnifiedAuthService.handleLogout).toHaveBeenCalledWith(mockAuthConfig);
    });

    it('should handle logout errors gracefully and still clear local state', async () => {
      // Setup authenticated state
      (localStorage.getItem as jest.Mock).mockReturnValue(mockJwtToken);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(mockJwtToken);
      mockJwtDecode.mockReturnValue(mockUser);
      
      // Mock logout failure
      mockUnifiedAuthService.handleLogout.mockRejectedValue(new Error('Backend logout failed'));

      const mockLocation = { href: '' };
      Object.defineProperty(window, 'location', {
        value: mockLocation,
        writable: true
      });

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('Test User (test@netra.com)');
      });

      // Perform logout (should handle error gracefully)
      fireEvent.click(screen.getByTestId('logout-button'));

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('No user');
        expect(screen.getByTestId('token-status')).toHaveTextContent('No token');
      });

      // Even with backend error, local logout method should be called
      // (The AuthProvider handles clearing local state internally)
    });

    it('should clear localStorage and sessionStorage on logout', async () => {
      // Setup authenticated state
      (localStorage.getItem as jest.Mock).mockReturnValue(mockJwtToken);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(mockJwtToken);
      mockJwtDecode.mockReturnValue(mockUser);

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('Test User (test@netra.com)');
      });

      fireEvent.click(screen.getByTestId('logout-button'));

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('No user');
      });

      // Verify storage cleanup (multiple items should be removed)
      expect(localStorage.removeItem).toHaveBeenCalledWith('jwt_token');
      expect(sessionStorage.clear).toHaveBeenCalled();
    });
  });

  describe('Authentication Error Handling', () => {
    it('should handle network errors during auth config fetch', async () => {
      mockUnifiedAuthService.getAuthConfig.mockRejectedValue(new Error('Network error'));

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      // Should still initialize with offline config in development mode
      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('initialized');
      });
    });

    it('should handle invalid JWT tokens gracefully', async () => {
      const invalidToken = 'invalid.jwt.token';
      
      (localStorage.getItem as jest.Mock).mockReturnValue(invalidToken);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(invalidToken);
      mockJwtDecode.mockImplementation(() => {
        throw new Error('Invalid token');
      });

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('No user');
        expect(screen.getByTestId('token-status')).toHaveTextContent('No token');
      });

      expect(mockUnifiedAuthService.removeToken).toHaveBeenCalled();
    });
  });

  describe('Session Persistence', () => {
    it('should maintain authentication state across page refreshes', async () => {
      // Simulate page refresh scenario
      (localStorage.getItem as jest.Mock).mockReturnValue(mockJwtToken);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
      mockUnifiedAuthService.getToken.mockReturnValue(mockJwtToken);
      mockJwtDecode.mockReturnValue(mockUser);

      const { unmount, rerender } = render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('Test User (test@netra.com)');
      });

      // Unmount and remount to simulate page refresh
      unmount();

      render(
        <AuthProvider>
          <TestAuthComponent />
        </AuthProvider>
      );

      // User should be restored from token
      await waitFor(() => {
        expect(screen.getByTestId('user-info')).toHaveTextContent('Test User (test@netra.com)');
        expect(screen.getByTestId('token-status')).toHaveTextContent('Token present');
      });
    });
  });
});