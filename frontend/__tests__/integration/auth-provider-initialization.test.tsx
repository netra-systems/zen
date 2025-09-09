/**
 * Integration Tests for AuthProvider Initialization Bug
 * 
 * CRITICAL BUG REPRODUCTION: AuthProvider timing issue
 * Reproduces the exact scenario where:
 * - Token exists in localStorage during initialization
 * - AuthProvider finishes initialization (initialized: true)
 * - But user state is null due to timing issues in fetchAuthConfig
 * - This breaks chat functionality completely
 * 
 * BVJ: All segments - Core authentication system must work
 * 
 * @compliance CLAUDE.md - Real integration tests with actual AuthProvider
 * @compliance type_safety.xml - Strongly typed React testing
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AuthProvider, useAuth } from '@/auth/context';
import { unifiedAuthService } from '@/auth/unified-auth-service';
import { User } from '@/types';
import { logger } from '@/lib/logger';
import { monitorAuthState } from '@/lib/auth-validation';

// Mock dependencies
jest.mock('@/auth/unified-auth-service', () => ({
  unifiedAuthService: {
    getAuthConfig: jest.fn(),
    getToken: jest.fn(),
    removeToken: jest.fn(),
    needsRefresh: jest.fn(),
    refreshToken: jest.fn(),
    handleDevLogin: jest.fn(),
    getDevLogoutFlag: jest.fn(),
    clearDevLogoutFlag: jest.fn(),
    setDevLogoutFlag: jest.fn(),
    handleLogout: jest.fn(),
  }
}));

jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  }
}));

jest.mock('@/lib/auth-validation', () => ({
  monitorAuthState: jest.fn(),
}));

jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: () => ({
    trackLogin: jest.fn(),
    trackLogout: jest.fn(),
    trackOAuthComplete: jest.fn(),
    trackError: jest.fn(),
  })
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    login: jest.fn(),
    logout: jest.fn(),
  })
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: {
    getState: () => ({
      resetStore: jest.fn(),
    })
  }
}));

// Mock JWT decode
jest.mock('jwt-decode', () => ({
  jwtDecode: jest.fn(),
}));

const mockUnifiedAuthService = unifiedAuthService as jest.Mocked<typeof unifiedAuthService>;
const mockLogger = logger as jest.Mocked<typeof logger>;
const mockMonitorAuthState = monitorAuthState as jest.MockedFunction<typeof monitorAuthState>;
const mockJwtDecode = require('jwt-decode').jwtDecode as jest.MockedFunction<any>;

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
});

// Test component to access auth context
const TestComponent: React.FC = () => {
  const auth = useAuth();
  return (
    <div>
      <div data-testid="auth-loading">{auth.loading ? 'loading' : 'not-loading'}</div>
      <div data-testid="auth-initialized">{auth.initialized ? 'initialized' : 'not-initialized'}</div>
      <div data-testid="auth-has-token">{auth.token ? 'has-token' : 'no-token'}</div>
      <div data-testid="auth-has-user">{auth.user ? 'has-user' : 'no-user'}</div>
      <div data-testid="auth-user-email">{auth.user?.email || 'no-email'}</div>
    </div>
  );
};

describe('AuthProvider Initialization - CRITICAL BUG REPRODUCTION', () => {
  const mockUser: User = {
    id: 'test-user-123',
    email: 'test@example.com',
    full_name: 'Test User',
    exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour from now
  };

  const validToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6InRlc3QtdXNlci0xMjMiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJmdWxsX25hbWUiOiJUZXN0IFVzZXIiLCJleHAiOjE5OTk5OTk5OTksInN1YiI6InRlc3QtdXNlci0xMjMifQ.FakeSignature';

  const mockAuthConfig = {
    development_mode: false,
    oauth_enabled: true,
    google_client_id: 'test-client-id',
    endpoints: {
      login: '/auth/login',
      logout: '/auth/logout',
      callback: '/auth/callback',
      token: '/auth/token',
      user: '/auth/me',
    },
    authorized_javascript_origins: ['http://localhost:3000'],
    authorized_redirect_uris: ['http://localhost:3000/auth/callback'],
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset localStorage mock
    mockLocalStorage.getItem.mockClear();
    mockLocalStorage.setItem.mockClear();
    mockLocalStorage.removeItem.mockClear();
    
    // Default mocks
    mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
    mockUnifiedAuthService.getToken.mockReturnValue(null);
    mockUnifiedAuthService.needsRefresh.mockReturnValue(false);
    mockUnifiedAuthService.getDevLogoutFlag.mockReturnValue(false);
    mockJwtDecode.mockReturnValue(mockUser);
  });

  describe('CRITICAL BUG: Token in localStorage but User Not Set', () => {
    test('SHOULD FAIL: AuthProvider initializes with token but fails to set user', async () => {
      // REPRODUCE THE EXACT BUG SCENARIO:
      // 1. Token exists in localStorage (during page refresh)
      mockLocalStorage.getItem.mockImplementation((key) => {
        if (key === 'jwt_token') return validToken;
        return null;
      });

      // 2. unifiedAuthService.getToken() returns the same token
      mockUnifiedAuthService.getToken.mockReturnValue(validToken);

      // 3. JWT decode succeeds (should set user but doesn't due to timing)
      mockJwtDecode.mockReturnValue(mockUser);

      // 4. Auth config fetch succeeds
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);

      // SIMULATE THE BUG: AuthProvider processes token but fails to set user state
      // This could happen due to React state update timing issues
      
      const { container } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Wait for initialization to complete
      await waitFor(() => {
        expect(screen.getByTestId('auth-loading')).toHaveTextContent('not-loading');
        expect(screen.getByTestId('auth-initialized')).toHaveTextContent('initialized');
      }, { timeout: 1000 });

      // CRITICAL BUG STATE: Should have token but no user
      // In the actual bug, this is what happens:
      const authState = {
        hasToken: screen.getByTestId('auth-has-token').textContent === 'has-token',
        hasUser: screen.getByTestId('auth-has-user').textContent === 'has-user',
        initialized: screen.getByTestId('auth-initialized').textContent === 'initialized',
      };

      // Log the detected bug state
      console.log('🐛 DETECTED AUTH STATE:', authState);

      // The bug occurs when we have this exact scenario:
      if (authState.hasToken && !authState.hasUser && authState.initialized) {
        console.error('🚨 CRITICAL BUG REPRODUCED: Token exists but user is null!');
        
        // Verify monitorAuthState was called to detect this
        expect(mockMonitorAuthState).toHaveBeenCalledWith(
          expect.any(String), // token
          expect.any(Object),  // user (should be set but isn't)
          true,               // initialized
          'auth_init_complete'
        );
      }

      // This test will FAIL if the bug is present
      // It should PASS only when the fix ensures user is always set when token exists
      expect(authState.hasToken).toBe(true);
      expect(authState.hasUser).toBe(true); // This will FAIL if bug is present
      expect(screen.getByTestId('auth-user-email')).toHaveTextContent(mockUser.email);
    });

    test('SHOULD FAIL: Monitor auth state detects token without user during init', async () => {
      // Set up the bug scenario
      mockLocalStorage.getItem.mockImplementation((key) => {
        if (key === 'jwt_token') return validToken;
        return null;
      });
      mockUnifiedAuthService.getToken.mockReturnValue(validToken);
      mockJwtDecode.mockReturnValue(mockUser);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-initialized')).toHaveTextContent('initialized');
      });

      // Verify monitorAuthState was called during auth init completion
      expect(mockMonitorAuthState).toHaveBeenCalledWith(
        expect.any(String), // token should exist
        expect.anything(),  // user (may be null due to bug)
        true,              // initialized: true
        'auth_init_complete'
      );
    });

    test('SHOULD FAIL: Auth logging shows token processing but user setting fails', async () => {
      mockLocalStorage.getItem.mockImplementation((key) => {
        if (key === 'jwt_token') return validToken;
        return null;
      });
      mockUnifiedAuthService.getToken.mockReturnValue(validToken);
      mockJwtDecode.mockReturnValue(mockUser);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-initialized')).toHaveTextContent('initialized');
      });

      // Verify comprehensive logging during auth initialization
      expect(mockLogger.debug).toHaveBeenCalledWith(
        'Found token in localStorage during AuthProvider initialization',
        expect.objectContaining({
          component: 'AuthContext',
          action: 'init_token_from_storage'
        })
      );

      expect(mockLogger.info).toHaveBeenCalledWith(
        '[AUTH INIT] Auth context initialization finished',
        expect.objectContaining({
          component: 'AuthContext',
          action: 'init_finished',
          hasUser: expect.any(Boolean),
          hasToken: expect.any(Boolean),
          initialized: true
        })
      );
    });
  });

  describe('Valid Auth Initialization Scenarios', () => {
    test('SHOULD PASS: AuthProvider initializes correctly without token', async () => {
      // No token in localStorage
      mockLocalStorage.getItem.mockReturnValue(null);
      mockUnifiedAuthService.getToken.mockReturnValue(null);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-initialized')).toHaveTextContent('initialized');
      });

      expect(screen.getByTestId('auth-has-token')).toHaveTextContent('no-token');
      expect(screen.getByTestId('auth-has-user')).toHaveTextContent('no-user');
      expect(screen.getByTestId('auth-loading')).toHaveTextContent('not-loading');
    });

    test('SHOULD PASS: AuthProvider handles auth config fetch failure gracefully', async () => {
      mockUnifiedAuthService.getAuthConfig.mockRejectedValue(new Error('Backend offline'));
      mockLocalStorage.getItem.mockReturnValue(null);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-initialized')).toHaveTextContent('initialized');
      });

      expect(mockLogger.error).toHaveBeenCalledWith(
        'Failed to fetch auth config - backend may be offline',
        expect.any(Error),
        expect.objectContaining({
          component: 'AuthContext',
          action: 'fetch_auth_config_failed'
        })
      );
    });
  });
});
