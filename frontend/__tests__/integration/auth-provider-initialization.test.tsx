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

// Mock localStorage with all methods
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
});

// Mock sessionStorage as well
Object.defineProperty(window, 'sessionStorage', {
  value: {
    getItem: jest.fn(),
    setItem: jest.fn(), 
    removeItem: jest.fn(),
    clear: jest.fn(),
    length: 0,
    key: jest.fn(),
  },
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
    
    // CRITICAL FIX: Clear localStorage mock BEFORE setting up state
    // This ensures clean state for each test and prevents cross-contamination
    mockLocalStorage.clear();
    mockLocalStorage.getItem.mockClear();
    mockLocalStorage.setItem.mockClear();
    mockLocalStorage.removeItem.mockClear();
    mockLocalStorage.clear.mockClear();
    
    // Set localStorage mock to return null by default (clean state)
    mockLocalStorage.getItem.mockReturnValue(null);
    
    // Default mocks
    mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
    mockUnifiedAuthService.getToken.mockReturnValue(null);
    mockUnifiedAuthService.needsRefresh.mockReturnValue(false);
    mockUnifiedAuthService.getDevLogoutFlag.mockReturnValue(false);
    mockJwtDecode.mockReturnValue(mockUser);
  });

  afterEach(() => {
    // CRITICAL: Ensure complete cleanup after each test
    // This prevents cross-contamination between tests
    jest.clearAllMocks();
    
    // Clear mocked localStorage
    mockLocalStorage.clear();
    
    // Reset all mock implementations to default state
    mockLocalStorage.getItem.mockReset();
    mockLocalStorage.setItem.mockReset();
    mockLocalStorage.removeItem.mockReset();
    mockLocalStorage.clear.mockReset();
    
    // Reset service mocks
    mockUnifiedAuthService.getAuthConfig.mockReset();
    mockUnifiedAuthService.getToken.mockReset();
    mockUnifiedAuthService.needsRefresh.mockReset();
    mockUnifiedAuthService.getDevLogoutFlag.mockReset();
    mockJwtDecode.mockReset();
    
    // Reset logger and monitor mocks
    mockLogger.debug.mockReset();
    mockLogger.info.mockReset();
    mockLogger.warn.mockReset();
    mockLogger.error.mockReset();
    mockMonitorAuthState.mockReset();
  });

  describe('CRITICAL BUG: Token in localStorage but User Not Set', () => {
    test('SHOULD PASS: AuthProvider correctly initializes with token and sets user', async () => {
      // CRITICAL FIX: Set up localStorage state BEFORE rendering
      // This simulates a real page refresh scenario where token exists in localStorage
      
      // 1. Set token in localStorage via proper mock setup - this is key!
      mockLocalStorage.setItem('jwt_token', validToken);
      
      // 2. Set up mocks to return token consistently
      mockLocalStorage.getItem.mockImplementation((key) => {
        if (key === 'jwt_token') return validToken;
        return null; // Default for other keys
      });
      
      mockUnifiedAuthService.getToken.mockReturnValue(validToken);
      mockJwtDecode.mockReturnValue(mockUser);
      mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);

      // Now render the AuthProvider - it should find the token and set user
      const { container } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Wait for initialization to complete
      await waitFor(() => {
        expect(screen.getByTestId('auth-loading')).toHaveTextContent('not-loading');
        expect(screen.getByTestId('auth-initialized')).toHaveTextContent('initialized');
      }, { timeout: 2000 });

      // Verify the auth state is consistent
      const authState = {
        hasToken: screen.getByTestId('auth-has-token').textContent === 'has-token',
        hasUser: screen.getByTestId('auth-has-user').textContent === 'has-user',
        initialized: screen.getByTestId('auth-initialized').textContent === 'initialized',
      };

      console.log('🔐 AUTH STATE VERIFICATION:', authState);

      // CRITICAL: When token exists in localStorage, user MUST also be set
      expect(authState.hasToken).toBe(true);
      expect(authState.hasUser).toBe(true);
      expect(authState.initialized).toBe(true);
      expect(screen.getByTestId('auth-user-email')).toHaveTextContent(mockUser.email);

      // Verify monitorAuthState was called with proper parameters
      expect(mockMonitorAuthState).toHaveBeenCalledWith(
        expect.stringContaining('eyJ'), // Should be the actual token
        expect.objectContaining({ // Should be the user object
          id: 'test-user-123',
          email: 'test@example.com'
        }),
        true,               // initialized: true
        'auth_init_complete'
      );
    });

    test('SHOULD PASS: Monitor auth state detects consistent token and user during init', async () => {
      // Set up the successful scenario
      mockLocalStorage.setItem('jwt_token', validToken);
      
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
      }, { timeout: 2000 });

      // Verify monitorAuthState was called during auth init completion
      // This ensures our monitoring system is working correctly
      expect(mockMonitorAuthState).toHaveBeenCalledWith(
        expect.stringContaining('eyJ'), // token should exist and be valid
        expect.objectContaining({       // user should be properly set
          id: 'test-user-123',
          email: 'test@example.com'
        }),
        true,              // initialized: true
        'auth_init_complete'
      );
    });

    test('SHOULD PASS: Auth logging shows proper token processing and user setting', async () => {
      // Set up localStorage with token BEFORE rendering
      mockLocalStorage.setItem('jwt_token', validToken);
      
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
      }, { timeout: 2000 });

      // Verify comprehensive logging during auth initialization
      // This log should appear when token is found during AuthProvider initialization
      expect(mockLogger.debug).toHaveBeenCalledWith(
        'Found token in localStorage during AuthProvider initialization',
        expect.objectContaining({
          component: 'AuthContext',
          action: 'init_token_from_storage'
        })
      );

      // This log should appear when auth initialization finishes successfully  
      expect(mockLogger.info).toHaveBeenCalledWith(
        '[AUTH INIT] Auth context initialization finished',
        expect.objectContaining({
          component: 'AuthContext',
          action: 'init_finished',
          hasUser: true,  // Should be true when token is processed correctly
          hasToken: true, // Should be true when token exists
          initialized: true
        })
      );
    });
  });

  describe('Valid Auth Initialization Scenarios', () => {
    test('SHOULD PASS: AuthProvider initializes correctly without token', async () => {
      // CRITICAL FIX: Ensure localStorage is truly empty (not just mocked)
      mockLocalStorage.clear();
      
      // Set up mocks for no-token scenario  
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
        expect(screen.getByTestId('auth-loading')).toHaveTextContent('not-loading');
      }, { timeout: 2000 });

      // Verify clean initialization state
      expect(screen.getByTestId('auth-has-token')).toHaveTextContent('no-token');
      expect(screen.getByTestId('auth-has-user')).toHaveTextContent('no-user');
      expect(screen.getByTestId('auth-user-email')).toHaveTextContent('no-email');
    });

    test('SHOULD PASS: AuthProvider handles auth config fetch failure gracefully', async () => {
      // Set up scenario where backend is offline
      mockLocalStorage.clear();
      
      mockUnifiedAuthService.getAuthConfig.mockRejectedValue(new Error('Backend offline'));
      mockLocalStorage.getItem.mockReturnValue(null);
      mockUnifiedAuthService.getToken.mockReturnValue(null);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-initialized')).toHaveTextContent('initialized');
        expect(screen.getByTestId('auth-loading')).toHaveTextContent('not-loading');
      }, { timeout: 2000 });

      // Verify error logging for config fetch failure
      expect(mockLogger.error).toHaveBeenCalledWith(
        'Failed to fetch auth config - backend may be offline',
        expect.any(Error),
        expect.objectContaining({
          component: 'AuthContext',
          action: 'fetch_auth_config_failed'
        })
      );

      // Should still initialize even when backend is offline
      expect(screen.getByTestId('auth-initialized')).toHaveTextContent('initialized');
    });
  });
});
