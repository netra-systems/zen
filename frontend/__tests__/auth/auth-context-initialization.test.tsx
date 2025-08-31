/**
 * AuthContext Token Initialization Tests
 * 
 * CRITICAL FUNCTIONALITY TESTS: Token initialization race conditions and edge cases
 * 
 * Context: AuthContext now initializes token from localStorage during state creation 
 * instead of waiting for useEffect. This prevents race conditions on OAuth first login 
 * where the callback sets a token in localStorage but AuthContext useEffect hasn't run yet.
 * 
 * These tests are designed to be CHALLENGING and will fail if the implementation is incorrect:
 * 
 * 1. Race Condition Test: Verifies token is available immediately during component render,
 *    not after useEffect runs. This test would fail if token initialization was moved back
 *    to useEffect.
 * 
 * 2. SSR Compatibility Test: Ensures no window access during server-side rendering.
 *    This test would fail if window checking is missing or incorrect.
 * 
 * 3. Token Validation Test: Tests what happens when localStorage contains invalid/expired
 *    tokens during initialization. This test would fail if proper error handling isn't
 *    implemented during the initialization phase.
 * 
 * IMPLEMENTATION NOTES:
 * - Tests unmock the real AuthContext to test actual implementation
 * - Uses controlled localStorage mocking to simulate OAuth callback scenarios
 * - Tests timing-sensitive race conditions and async edge cases
 * - Validates proper cleanup and error handling during initialization
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/auth/context';
import { unifiedAuthService } from '@/auth/unified-auth-service';
import { jwtDecode } from 'jwt-decode';
import { useAuthStore } from '@/store/authStore';
import { logger } from '@/lib/logger';
import '@testing-library/jest-dom';

// Test component to access auth context with comprehensive state tracking
const TestComponent = ({ onAuthChange }: { onAuthChange?: (authState: any) => void }) => {
  const auth = useAuth();
  
  React.useEffect(() => {
    if (onAuthChange) {
      onAuthChange({
        token: auth.token,
        user: auth.user,
        loading: auth.loading,
        timestamp: Date.now()
      });
    }
  }, [auth.token, auth.user, auth.loading, onAuthChange]);

  return (
    <div data-testid="auth-test-component">
      <div data-testid="token-display">{auth.token || 'no-token'}</div>
      <div data-testid="user-display">{auth.user ? auth.user.email : 'no-user'}</div>
      <div data-testid="loading-display">{auth.loading ? 'loading' : 'loaded'}</div>
    </div>
  );
};

// Unmock the AuthContext to test real implementation
jest.unmock('@/auth/context');

// Mock dependencies
jest.mock('@/auth/unified-auth-service');
jest.mock('jwt-decode');
jest.mock('@/store/authStore');
jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
    debug: jest.fn()
  }
}));

// Test data - realistic JWT tokens for different scenarios
const mockValidToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImZ1bGxfbmFtZSI6IlRlc3QgVXNlciIsImV4cCI6OTk5OTk5OTk5OSwicm9sZSI6InVzZXIifQ.valid-signature';
const mockExpiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImZ1bGxfbmFtZSI6IlRlc3QgVXNlciIsImV4cCI6MTAwLCJyb2xlIjoidXNlciJ9.expired-signature';
const mockInvalidToken = 'invalid.token.format.without.proper.structure';

const mockValidUser = {
  sub: 'user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  exp: 9999999999, // Far future expiration
  role: 'user'
};

const mockExpiredUser = {
  sub: 'user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  exp: 100, // Past expiration (January 1970)
  role: 'user'
};

const mockAuthConfig = {
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
};

describe('AuthContext Token Initialization - Critical Race Condition Tests', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let mockAuthStore: any;
  let mockUnifiedAuthService: jest.Mocked<typeof unifiedAuthService>;
  let mockJwtDecode: jest.MockedFunction<typeof jwtDecode>;
  let originalWindow: any;
  let originalLocalStorage: any;

  beforeEach(() => {
    // Store original globals
    originalWindow = global.window;
    originalLocalStorage = global.localStorage;

    // Setup clean localStorage mock
    const localStorageStore = new Map<string, string>();
    const mockLocalStorage = {
      getItem: jest.fn((key: string) => localStorageStore.get(key) || null),
      setItem: jest.fn((key: string, value: string) => {
        localStorageStore.set(key, value);
      }),
      removeItem: jest.fn((key: string) => {
        localStorageStore.delete(key);
      }),
      clear: jest.fn(() => {
        localStorageStore.clear();
      })
    };

    // Setup window with clean localStorage
    global.window = {
      localStorage: mockLocalStorage,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn()
    } as any;
    global.localStorage = mockLocalStorage;

    // Setup auth store mock
    mockAuthStore = {
      login: jest.fn(),
      logout: jest.fn(),
      user: null,
      token: null,
      isAuthenticated: false
    };
    (useAuthStore as jest.Mock).mockReturnValue(mockAuthStore);

    // Setup unified auth service mock
    mockUnifiedAuthService = unifiedAuthService as jest.Mocked<typeof unifiedAuthService>;
    mockUnifiedAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
    mockUnifiedAuthService.getToken.mockReturnValue(null);
    mockUnifiedAuthService.removeToken.mockImplementation(() => {});
    mockUnifiedAuthService.needsRefresh.mockReturnValue(false);
    mockUnifiedAuthService.refreshToken.mockResolvedValue({
      access_token: mockValidToken,
      token_type: 'Bearer',
      expires_in: 3600
    });

    // Setup JWT decode mock
    mockJwtDecode = jwtDecode as jest.MockedFunction<typeof jwtDecode>;
    mockJwtDecode.mockReturnValue(mockValidUser);

    jest.clearAllMocks();
  });

  afterEach(() => {
    // Restore original globals
    global.window = originalWindow;
    global.localStorage = originalLocalStorage;
    
    jest.clearAllTimers();
    jest.useRealTimers();
      cleanupAntiHang();
  });

  /**
   * TEST 1: Critical Race Condition Scenario
   * 
   * SCENARIO: OAuth callback has just set a token in localStorage, and AuthContext
   * is being rendered for the first time. The token MUST be available immediately
   * during the initial render phase, not after useEffect runs.
   * 
   * FAILURE CONDITIONS:
   * - If token initialization was moved back to useEffect, this test would fail
   * - If window checking prevents localStorage access during initialization
   * - If the token state isn't properly initialized from localStorage
   * 
   * SUCCESS CRITERIA:
   * - Token is available in the first render cycle
   * - Debug logging confirms localStorage access during initialization
   * - Auth store is eventually synced when auth config loads
   */
  it('CRITICAL: should immediately access token from localStorage during state initialization', async () => {
    // SETUP: Simulate OAuth callback setting token BEFORE AuthProvider renders
    const mockStorage = global.localStorage as any;
    mockStorage.setItem('jwt_token', mockValidToken);
    
    // Mock delayed auth config to ensure token is available before async operations complete
    let resolveAuthConfig: (value: any) => void;
    const authConfigPromise = new Promise(resolve => {
      resolveAuthConfig = resolve;
    });
    mockUnifiedAuthService.getAuthConfig.mockReturnValue(authConfigPromise as any);

    // Track authentication state changes
    const authStates: any[] = [];
    const handleAuthChange = (state: any) => {
      authStates.push(state);
    };

    // RENDER: AuthProvider should initialize token from localStorage immediately
    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent onAuthChange={handleAuthChange} />
        </AuthProvider>
      );
    });

    // CRITICAL ASSERTION 1: Token should be available in the first render
    // This proves token was initialized during useState() callback, not in useEffect
    expect(screen.getByTestId('token-display')).toHaveTextContent(mockValidToken);
    
    // CRITICAL ASSERTION 2: Should be in loading state while auth config loads
    expect(screen.getByTestId('loading-display')).toHaveTextContent('loading');

    // VERIFY: localStorage.getItem was called during initialization
    expect(mockStorage.getItem).toHaveBeenCalledWith('jwt_token');

    // VERIFY: Debug logging confirms token found during initialization
    expect(logger.debug).toHaveBeenCalledWith(
      'Found token in localStorage during AuthProvider initialization',
      {
        component: 'AuthContext',
        action: 'init_token_from_storage'
      }
    );

    // Complete auth config loading
    await act(async () => {
      resolveAuthConfig!(mockAuthConfig);
    });

    // Wait for auth config to complete
    await waitFor(() => {
      expect(screen.getByTestId('loading-display')).toHaveTextContent('loaded');
    });

    // FINAL VERIFICATION: Auth store should be synced after config loads
    await waitFor(() => {
      expect(mockAuthStore.login).toHaveBeenCalledWith(
        expect.objectContaining({
          id: mockValidUser.sub,
          email: mockValidUser.email,
          full_name: mockValidUser.full_name,
          role: mockValidUser.role
        }),
        mockValidToken
      );
    });

    // VERIFY: Token was available throughout the entire lifecycle
    expect(authStates[0].token).toBe(mockValidToken);
    expect(authStates[0].loading).toBe(true); // Still loading config initially
  });

  /**
   * TEST 2: Server-Side Rendering Compatibility
   * 
   * SCENARIO: AuthProvider is rendered in an SSR environment where window
   * and localStorage are not available.
   * 
   * FAILURE CONDITIONS:
   * - If AuthContext tries to access window or localStorage without checking
   * - If the component throws an error during SSR
   * - If the fallback behavior isn't properly implemented
   * 
   * SUCCESS CRITERIA:
   * - No errors thrown during render
   * - Token initializes as null in SSR environment
   * - No localStorage access attempts
   */
  it('CRITICAL: should handle SSR environment without window access', async () => {
    // SETUP: Remove window and localStorage to simulate SSR
    delete (global as any).window;
    delete (global as any).localStorage;

    let renderError: Error | null = null;

    try {
      // RENDER: Should not throw in SSR environment
      await act(async () => {
        render(
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        );
      });

      // Wait for initial render to stabilize
      await waitFor(() => {
        expect(screen.getByTestId('auth-test-component')).toBeInTheDocument();
      });

      // CRITICAL ASSERTION: Should initialize with no token in SSR
      expect(screen.getByTestId('token-display')).toHaveTextContent('no-token');

    } catch (error) {
      renderError = error as Error;
    }

    // CRITICAL ASSERTION: Should not throw any errors
    expect(renderError).toBeNull();

    // VERIFY: No localStorage access attempts occurred
    // (Can't verify since localStorage doesn't exist, but no errors is proof)
  });

  /**
   * TEST 3: Invalid Token Handling During Initialization
   * 
   * SCENARIO: localStorage contains an invalid token during AuthProvider initialization.
   * This tests the error handling path during the critical initialization phase.
   * 
   * FAILURE CONDITIONS:
   * - If invalid token causes initialization to fail
   * - If error handling doesn't properly clean up invalid tokens
   * - If auth store isn't properly cleared on invalid token
   * 
   * SUCCESS CRITERIA:
   * - Invalid token is initially present
   * - Error handling cleans up invalid token
   * - Auth store is logged out
   * - Component ends in clean state
   */
  it('CRITICAL: should detect and clean up invalid tokens during initialization', async () => {
    // SETUP: Place invalid token in localStorage
    const mockStorage = global.localStorage as any;
    mockStorage.setItem('jwt_token', mockInvalidToken);

    // Mock jwtDecode to throw for invalid token
    mockJwtDecode.mockImplementation((token: string) => {
      if (token === mockInvalidToken) {
        throw new Error('Invalid token format');
      }
      return mockValidUser;
    });

    mockUnifiedAuthService.getToken.mockReturnValue(mockInvalidToken);

    // Track component state changes
    const authStates: any[] = [];
    const handleAuthChange = (state: any) => {
      authStates.push(state);
    };

    // RENDER: AuthProvider should handle invalid token gracefully
    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent onAuthChange={handleAuthChange} />
        </AuthProvider>
      );
    });

    // CRITICAL ASSERTION 1: Should initially show invalid token from localStorage
    expect(screen.getByTestId('token-display')).toHaveTextContent(mockInvalidToken);

    // Wait for error handling to complete
    await waitFor(() => {
      expect(logger.error).toHaveBeenCalledWith(
        'Invalid token detected',
        expect.any(Error),
        {
          component: 'AuthContext',
          action: 'token_validation_failed'
        }
      );
    });

    // CRITICAL ASSERTION 2: Should clean up invalid token
    expect(mockUnifiedAuthService.removeToken).toHaveBeenCalled();

    // CRITICAL ASSERTION 3: Should logout auth store
    expect(mockAuthStore.logout).toHaveBeenCalled();

    // Wait for component to reach stable state
    await waitFor(() => {
      expect(screen.getByTestId('loading-display')).toHaveTextContent('loaded');
    }, { timeout: 5000 });

    // FINAL VERIFICATION: Should end in clean state
    expect(screen.getByTestId('token-display')).toHaveTextContent('no-token');
    expect(screen.getByTestId('user-display')).toHaveTextContent('no-user');
  });

  /**
   * COMPREHENSIVE TEST SUMMARY:
   * 
   * These tests validate the critical change where AuthContext initializes 
   * token from localStorage during state creation rather than in useEffect.
   * 
   * Key Test Scenarios:
   * 1. OAuth Race Condition: Token available immediately on first render
   * 2. SSR Compatibility: No window access during server rendering  
   * 3. Invalid Token Handling: Proper cleanup during initialization
   * 
   * Each test is designed to fail if the implementation regresses or 
   * if the critical initialization behavior is changed.
   * 
   * The tests verify:
   * - Timing-sensitive race conditions
   * - Error handling during initialization
   * - Cross-environment compatibility (SSR)
   * - Proper cleanup and state management
   * - Integration with auth store and services
   */
});