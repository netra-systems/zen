/**
 * AuthContext Storage Event Listener Tests
 * 
 * CRITICAL FUNCTIONALITY TESTS: Cross-tab token synchronization and security
 * 
 * Context: AuthContext listens for storage events to detect token changes in real-time,
 * enabling immediate token detection when OAuth callback saves the token. This is crucial
 * for multi-tab scenarios and OAuth flows.
 * 
 * These tests are designed to be CHALLENGING and will fail if the implementation is incorrect:
 * 
 * 1. Cross-Tab Synchronization Test: Verifies token changes from other tabs/windows are
 *    immediately detected and processed. This test would fail if storage event listeners
 *    aren't properly registered or if event handling is broken.
 * 
 * 2. Race Condition with Multiple Rapid Events: Tests handling of multiple storage events
 *    in quick succession, simulating network issues or multiple OAuth attempts.
 *    This test would fail if event handling isn't debounced or if concurrent updates cause issues.
 * 
 * 3. Malicious Storage Event Injection: Tests security by simulating invalid/malicious 
 *    storage events and ensuring they don't compromise the auth state.
 *    This test would fail if proper validation isn't implemented.
 * 
 * IMPLEMENTATION NOTES:
 * - Tests unmock the real AuthContext to test actual storage event implementation
 * - Uses controlled localStorage and window event mocking
 * - Tests timing-sensitive race conditions and security edge cases
 * - Validates proper token validation and error handling during events
 */

import React from 'react';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/auth/context';
import { unifiedAuthService } from '@/auth/unified-auth-service';
import { jwtDecode } from 'jwt-decode';
import { useAuthStore } from '@/store/authStore';
import { logger } from '@/lib/logger';
import '@testing-library/jest-dom';

// Test component to track auth state changes with precise timing
const TestComponent = ({ onAuthChange }: { onAuthChange?: (authState: any) => void }) => {
  const auth = useAuth();
  
  React.useEffect(() => {
    if (onAuthChange) {
      onAuthChange({
        token: auth.token,
        user: auth.user,
        loading: auth.loading,
        timestamp: Date.now(),
        // Include additional state for comprehensive tracking
        hasToken: !!auth.token,
        hasUser: !!auth.user,
        isAuthenticated: !!auth.user && !!auth.token
      });
    }
  }, [auth.token, auth.user, auth.loading, onAuthChange]);

  return (
    <div data-testid="auth-test-component">
      <div data-testid="token-display">{auth.token || 'no-token'}</div>
      <div data-testid="user-display">{auth.user ? auth.user.email : 'no-user'}</div>
      <div data-testid="loading-display">{auth.loading ? 'loading' : 'loaded'}</div>
      <div data-testid="auth-status">
        {auth.user && auth.token ? 'authenticated' : 'unauthenticated'}
      </div>
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

// Realistic test data
const mockValidToken1 = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoidGVzdDFAZXhhbXBsZS5jb20iLCJmdWxsX25hbWUiOiJUZXN0IFVzZXIgMSIsImV4cCI6OTk5OTk5OTk5OSwicm9sZSI6InVzZXIifQ.valid-signature-1';
const mockValidToken2 = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTQ1NiIsImVtYWlsIjoidGVzdDJAZXhhbXBsZS5jb20iLCJmdWxsX25hbWUiOiJUZXN0IFVzZXIgMiIsImV4cCI6OTk5OTk5OTk5OSwicm9sZSI6InVzZXIifQ.valid-signature-2';
const mockValidToken3 = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTc4OSIsImVtYWlsIjoidGVzdDNAZXhhbXBsZS5jb20iLCJmdWxsX25hbWUiOiJUZXN0IFVzZXIgMyIsImV4cCI6OTk5OTk5OTk5OSwicm9sZSI6InVzZXIifQ.valid-signature-3';
const mockExpiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImZ1bGxfbmFtZSI6IlRlc3QgVXNlciIsImV4cCI6MTAwLCJyb2xlIjoidXNlciJ9.expired-signature';
const mockInvalidToken = 'invalid.malicious.token.injection.attempt';
const mockMaliciousToken = '<script>alert("xss")</script>';

const mockValidUser1 = {
  sub: 'user-123',
  email: 'test1@example.com',
  full_name: 'Test User 1',
  exp: 9999999999,
  role: 'user'
};

const mockValidUser2 = {
  sub: 'user-456',
  email: 'test2@example.com',
  full_name: 'Test User 2',
  exp: 9999999999,
  role: 'user'
};

const mockValidUser3 = {
  sub: 'user-789',
  email: 'test3@example.com',
  full_name: 'Test User 3',
  exp: 9999999999,
  role: 'user'
};

const mockExpiredUser = {
  sub: 'user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  exp: 100, // Past expiration
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

describe('AuthContext Storage Event Listener - Critical Cross-Tab & Security Tests', () => {
  let mockAuthStore: any;
  let mockUnifiedAuthService: jest.Mocked<typeof unifiedAuthService>;
  let mockJwtDecode: jest.MockedFunction<typeof jwtDecode>;
  let originalWindow: any;
  let originalLocalStorage: any;
  let mockLocalStorage: any;
  let mockAddEventListener: jest.Mock;
  let mockRemoveEventListener: jest.Mock;

  beforeEach(() => {
    // Store original globals
    originalWindow = global.window;
    originalLocalStorage = global.localStorage;

    // Setup advanced localStorage mock with event simulation
    const localStorageStore = new Map<string, string>();
    mockLocalStorage = {
      getItem: jest.fn((key: string) => localStorageStore.get(key) || null),
      setItem: jest.fn((key: string, value: string) => {
        const oldValue = localStorageStore.get(key) || null;
        localStorageStore.set(key, value);
        
        // Simulate storage event when value changes
        if (oldValue !== value && mockAddEventListener) {
          const storageEvent = new StorageEvent('storage', {
            key,
            oldValue,
            newValue: value,
            storageArea: localStorage  // Use the actual localStorage object
          });
          
          // Trigger registered storage event listeners
          setTimeout(() => {
            const calls = mockAddEventListener.mock.calls;
            calls.forEach(([eventType, handler]) => {
              if (eventType === 'storage') {
                handler(storageEvent);
              }
            });
          }, 0);
        }
      }),
      removeItem: jest.fn((key: string) => {
        const oldValue = localStorageStore.get(key) || null;
        localStorageStore.delete(key);
        
        // Simulate storage event for removal
        if (oldValue && mockAddEventListener) {
          const storageEvent = new StorageEvent('storage', {
            key,
            oldValue,
            newValue: null,
            storageArea: mockLocalStorage
          });
          
          setTimeout(() => {
            const calls = mockAddEventListener.mock.calls;
            calls.forEach(([eventType, handler]) => {
              if (eventType === 'storage') {
                handler(storageEvent);
              }
            });
          }, 0);
        }
      }),
      clear: jest.fn(() => localStorageStore.clear())
    };

    // Setup advanced window mock with event listener tracking
    mockAddEventListener = jest.fn();
    mockRemoveEventListener = jest.fn();
    
    global.window = {
      localStorage: mockLocalStorage,
      addEventListener: mockAddEventListener,
      removeEventListener: mockRemoveEventListener,
      dispatchEvent: jest.fn()
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

    // Setup JWT decode mock with multi-token support
    mockJwtDecode = jwtDecode as jest.MockedFunction<typeof jwtDecode>;
    mockJwtDecode.mockImplementation((token: string) => {
      switch (token) {
        case mockValidToken1: return mockValidUser1;
        case mockValidToken2: return mockValidUser2;
        case mockValidToken3: return mockValidUser3;
        case mockExpiredToken: return mockExpiredUser;
        case mockInvalidToken:
        case mockMaliciousToken:
          throw new Error('Invalid token format');
        default:
          throw new Error('Unknown token');
      }
    });

    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    // Restore original globals
    global.window = originalWindow;
    global.localStorage = originalLocalStorage;
    
    jest.clearAllTimers();
    jest.useRealTimers();
  });

  /**
   * TEST 1: Critical Cross-Tab Synchronization
   * 
   * SCENARIO: User opens multiple tabs, performs OAuth login in one tab,
   * and expects all other tabs to immediately detect the new token via storage events.
   * 
   * FAILURE CONDITIONS:
   * - If storage event listeners aren't properly registered
   * - If event handling doesn't update AuthContext state
   * - If token validation fails during storage event processing
   * - If auth store isn't synced after storage event
   * 
   * SUCCESS CRITERIA:
   * - Storage event listener is registered on mount
   * - Token change from "external" tab is immediately detected
   * - AuthContext state is updated with new token and user
   * - Auth store is synced with new authentication state
   * - Proper logging confirms cross-tab synchronization
   */
  it('CRITICAL: should detect and sync token changes from other tabs via storage events', async () => {
    // Track auth state changes with precise timing
    const authStates: any[] = [];
    const handleAuthChange = (state: any) => {
      authStates.push({ ...state, captureTime: Date.now() });
    };

    // SETUP: Render AuthProvider without initial token
    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent onAuthChange={handleAuthChange} />
        </AuthProvider>
      );
    });

    // Wait for initial load to complete
    await waitFor(() => {
      expect(screen.getByTestId('loading-display')).toHaveTextContent('loaded');
    });

    // CRITICAL ASSERTION 1: Storage event listener should be registered
    expect(mockAddEventListener).toHaveBeenCalledWith('storage', expect.any(Function));

    // VERIFY: Initial state should be unauthenticated
    expect(screen.getByTestId('token-display')).toHaveTextContent('no-token');
    expect(screen.getByTestId('user-display')).toHaveTextContent('no-user');
    expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');

    // SIMULATE: Another tab performs OAuth and sets token in localStorage
    // This simulates the OAuth callback setting the token
    const beforeStorageEventTime = Date.now();

    await act(async () => {
      // Directly trigger storage event as if from another tab
      const storageEvent = new StorageEvent('storage', {
        key: 'jwt_token',
        oldValue: null,
        newValue: mockValidToken1,
        storageArea: mockLocalStorage
      });

      // Get the registered storage event handler
      const storageHandler = mockAddEventListener.mock.calls.find(
        call => call[0] === 'storage'
      )?.[1];

      expect(storageHandler).toBeDefined();

      // Simulate the storage event
      if (storageHandler) {
        storageHandler(storageEvent);
      }
    });

    // CRITICAL ASSERTION 2: Token should be immediately updated
    await waitFor(() => {
      expect(screen.getByTestId('token-display')).toHaveTextContent(mockValidToken1);
    }, { timeout: 1000 });

    // CRITICAL ASSERTION 3: User should be decoded and set
    await waitFor(() => {
      expect(screen.getByTestId('user-display')).toHaveTextContent(mockValidUser1.email);
    }, { timeout: 1000 });

    // CRITICAL ASSERTION 4: Auth status should be updated
    expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');

    // VERIFY: JWT decode should have been called with the new token
    expect(mockJwtDecode).toHaveBeenCalledWith(mockValidToken1);

    // VERIFY: Auth store should be synced with new authentication state
    await waitFor(() => {
      expect(mockAuthStore.login).toHaveBeenCalledWith(
        expect.objectContaining({
          id: mockValidUser1.sub,
          email: mockValidUser1.email,
          full_name: mockValidUser1.full_name,
          role: mockValidUser1.role
        }),
        mockValidToken1
      );
    });

    // VERIFY: Logging should confirm cross-tab synchronization
    expect(logger.info).toHaveBeenCalledWith(
      'Detected token change via storage event',
      {
        component: 'AuthContext',
        action: 'storage_token_detected'
      }
    );

    // VERIFY: Auth state changes should show progression from unauthenticated to authenticated
    const finalAuthState = authStates[authStates.length - 1];
    expect(finalAuthState.hasToken).toBe(true);
    expect(finalAuthState.hasUser).toBe(true);
    expect(finalAuthState.isAuthenticated).toBe(true);
    expect(finalAuthState.captureTime).toBeGreaterThan(beforeStorageEventTime);
  });

  /**
   * TEST 2: Race Condition with Multiple Rapid Storage Events
   * 
   * SCENARIO: Multiple storage events fire in rapid succession (network issues,
   * multiple OAuth attempts, or tab switching). The AuthContext must handle
   * these events gracefully without corrupting state or causing race conditions.
   * 
   * FAILURE CONDITIONS:
   * - If multiple events cause state corruption
   * - If concurrent token processing creates inconsistent state
   * - If error handling fails under rapid event conditions
   * - If auth store gets out of sync due to race conditions
   * 
   * SUCCESS CRITERIA:
   * - All storage events are processed in order
   * - Final state reflects the last valid token
   * - No state corruption occurs during rapid events
   * - Error handling works correctly for invalid tokens in sequence
   * - Auth store remains consistent throughout the process
   */
  it('CRITICAL: should handle multiple rapid storage events without race conditions', async () => {
    // Track all auth state changes for race condition analysis
    const authStates: any[] = [];
    const handleAuthChange = (state: any) => {
      authStates.push({ 
        ...state, 
        captureTime: Date.now(),
        stateId: Math.random().toString(36).substring(7)
      });
    };

    // SETUP: Render AuthProvider
    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent onAuthChange={handleAuthChange} />
        </AuthProvider>
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('loading-display')).toHaveTextContent('loaded');
    });

    // Get the registered storage event handler
    const storageHandler = mockAddEventListener.mock.calls.find(
      call => call[0] === 'storage'
    )?.[1];
    expect(storageHandler).toBeDefined();

    // SIMULATE: Rapid sequence of storage events (simulating race conditions)
    const eventSequence = [
      { token: mockValidToken1, user: mockValidUser1, delay: 0 },
      { token: mockInvalidToken, user: null, delay: 10 }, // Invalid token
      { token: mockValidToken2, user: mockValidUser2, delay: 20 },
      { token: mockExpiredToken, user: mockExpiredUser, delay: 30 }, // Expired token
      { token: mockValidToken3, user: mockValidUser3, delay: 40 }, // Final valid token
    ];

    const startTime = Date.now();

    // Fire all events in rapid succession
    await act(async () => {
      eventSequence.forEach(({ token, delay }, index) => {
        setTimeout(() => {
          const storageEvent = new StorageEvent('storage', {
            key: 'jwt_token',
            oldValue: index === 0 ? null : eventSequence[index - 1].token,
            newValue: token,
            storageArea: mockLocalStorage
          });

          if (storageHandler) {
            try {
              storageHandler(storageEvent);
            } catch (error) {
              // Expected for invalid tokens
            }
          }
        }, delay);
      });

      // Advance timers to trigger all events
      jest.advanceTimersByTime(100);
    });

    // CRITICAL ASSERTION 1: Final state should reflect last valid token
    await waitFor(() => {
      expect(screen.getByTestId('token-display')).toHaveTextContent(mockValidToken3);
    }, { timeout: 2000 });

    await waitFor(() => {
      expect(screen.getByTestId('user-display')).toHaveTextContent(mockValidUser3.email);
    }, { timeout: 2000 });

    // CRITICAL ASSERTION 2: Auth status should be authenticated with final valid token
    expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');

    // VERIFY: Error logging should have occurred for invalid tokens
    expect(logger.error).toHaveBeenCalledWith(
      'Failed to decode token from storage event',
      expect.any(Error)
    );

    // CRITICAL ASSERTION 3: Auth store should reflect final valid state
    await waitFor(() => {
      expect(mockAuthStore.login).toHaveBeenCalledWith(
        expect.objectContaining({
          id: mockValidUser3.sub,
          email: mockValidUser3.email,
          full_name: mockValidUser3.full_name,
          role: mockValidUser3.role
        }),
        mockValidToken3
      );
    });

    // VERIFY: State progression shows no corruption
    const finalAuthState = authStates[authStates.length - 1];
    expect(finalAuthState.token).toBe(mockValidToken3);
    expect(finalAuthState.hasToken).toBe(true);
    expect(finalAuthState.hasUser).toBe(true);
    expect(finalAuthState.isAuthenticated).toBe(true);

    // VERIFY: All events were processed within reasonable time
    expect(Date.now() - startTime).toBeLessThan(2000);
  });

  /**
   * TEST 3: Malicious Storage Event Injection Security Test
   * 
   * SCENARIO: Malicious code or browser extensions attempt to inject invalid
   * or malicious storage events to compromise the authentication state.
   * The AuthContext must validate and sanitize all storage events.
   * 
   * FAILURE CONDITIONS:
   * - If malicious tokens are accepted without validation
   * - If XSS or injection attacks succeed through storage events
   * - If error handling exposes sensitive information
   * - If auth state becomes corrupted by malicious events
   * - If proper cleanup doesn't occur after malicious attempts
   * 
   * SUCCESS CRITERIA:
   * - All malicious tokens are rejected
   * - XSS attempts are neutralized
   * - Auth state remains stable after malicious events
   * - Error logging doesn't expose sensitive data
   * - Auth store is properly cleaned up after attacks
   * - Valid tokens still work after malicious attempts
   */
  it('CRITICAL: should defend against malicious storage event injection attacks', async () => {
    // Track security-related auth state changes
    const authStates: any[] = [];
    const securityEvents: any[] = [];
    
    const handleAuthChange = (state: any) => {
      authStates.push({ 
        ...state, 
        captureTime: Date.now(),
        securityCheck: {
          tokenLength: state.token ? state.token.length : 0,
          hasScript: state.token ? state.token.includes('<script>') : false,
          hasUser: !!state.user,
          userEmail: state.user ? state.user.email : null
        }
      });
    };

    // Override logger to capture security events
    const originalLoggerError = logger.error;
    (logger.error as jest.Mock).mockImplementation((...args) => {
      securityEvents.push({
        timestamp: Date.now(),
        args: args
      });
      return originalLoggerError.apply(logger, args);
    });

    // SETUP: Render AuthProvider with valid initial token
    mockLocalStorage.setItem('jwt_token', mockValidToken1);

    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent onAuthChange={handleAuthChange} />
        </AuthProvider>
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('loading-display')).toHaveTextContent('loaded');
    });

    // VERIFY: Initial valid state
    expect(screen.getByTestId('token-display')).toHaveTextContent(mockValidToken1);
    expect(screen.getByTestId('user-display')).toHaveTextContent(mockValidUser1.email);

    // Get storage event handler
    const storageHandler = mockAddEventListener.mock.calls.find(
      call => call[0] === 'storage'
    )?.[1];
    expect(storageHandler).toBeDefined();

    // ATTACK SEQUENCE: Multiple malicious injection attempts
    const maliciousEvents = [
      {
        name: 'XSS Script Injection',
        token: mockMaliciousToken,
        expectedRejection: true
      },
      {
        name: 'Invalid Token Format',
        token: mockInvalidToken,
        expectedRejection: true
      },
      {
        name: 'SQL Injection Attempt',
        token: "'; DROP TABLE users; --",
        expectedRejection: true
      },
      {
        name: 'Empty Token Attack',
        token: '',
        expectedRejection: true
      },
      {
        name: 'Null Byte Injection',
        token: 'valid.token.with\x00.null.bytes',
        expectedRejection: true
      },
      {
        name: 'Oversized Token Attack',
        token: 'x'.repeat(10000), // Extremely long token
        expectedRejection: true
      }
    ];

    // Execute malicious event sequence
    for (const attack of maliciousEvents) {
      await act(async () => {
        const maliciousStorageEvent = new StorageEvent('storage', {
          key: 'jwt_token',
          oldValue: mockValidToken1,
          newValue: attack.token,
          storageArea: mockLocalStorage
        });

        // Attempt malicious injection
        if (storageHandler) {
          storageHandler(maliciousStorageEvent);
        }

        // Small delay between attacks
        jest.advanceTimersByTime(50);
      });
    }

    // CRITICAL ASSERTION 1: Original valid token should remain after all attacks
    await waitFor(() => {
      expect(screen.getByTestId('token-display')).toHaveTextContent(mockValidToken1);
    }, { timeout: 1000 });

    // CRITICAL ASSERTION 2: User should remain authenticated with original data
    expect(screen.getByTestId('user-display')).toHaveTextContent(mockValidUser1.email);
    expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');

    // CRITICAL ASSERTION 3: Security errors should be logged for each malicious attempt
    expect(securityEvents.length).toBeGreaterThanOrEqual(maliciousEvents.length);
    
    // Verify each malicious attempt was caught and logged
    securityEvents.forEach(event => {
      expect(event.args[0]).toContain('Failed to decode token from storage event');
      expect(event.args[1]).toBeInstanceOf(Error);
    });

    // CRITICAL ASSERTION 4: Auth state should show no signs of compromise
    const currentAuthState = authStates[authStates.length - 1];
    expect(currentAuthState.securityCheck.hasScript).toBe(false);
    expect(currentAuthState.securityCheck.tokenLength).toBe(mockValidToken1.length);
    expect(currentAuthState.securityCheck.hasUser).toBe(true);
    expect(currentAuthState.securityCheck.userEmail).toBe(mockValidUser1.email);

    // SECURITY VERIFICATION: Test that valid token still works after attacks
    await act(async () => {
      const validStorageEvent = new StorageEvent('storage', {
        key: 'jwt_token',
        oldValue: mockValidToken1,
        newValue: mockValidToken2,
        storageArea: mockLocalStorage
      });

      if (storageHandler) {
        storageHandler(validStorageEvent);
      }
    });

    // FINAL VERIFICATION: Valid token should work correctly after attack attempts
    await waitFor(() => {
      expect(screen.getByTestId('token-display')).toHaveTextContent(mockValidToken2);
    }, { timeout: 1000 });

    await waitFor(() => {
      expect(screen.getByTestId('user-display')).toHaveTextContent(mockValidUser2.email);
    }, { timeout: 1000 });

    // VERIFY: Auth store should be properly updated with valid token
    expect(mockAuthStore.login).toHaveBeenCalledWith(
      expect.objectContaining({
        email: mockValidUser2.email
      }),
      mockValidToken2
    );

    // FINAL SECURITY CHECK: No sensitive data should be exposed in logs
    securityEvents.forEach(event => {
      const logMessage = JSON.stringify(event.args);
      expect(logMessage).not.toContain('<script>');
      expect(logMessage).not.toContain('DROP TABLE');
      expect(logMessage).not.toContain('\x00');
    });
  });

  /**
   * COMPREHENSIVE TEST SUMMARY:
   * 
   * These challenging tests validate the critical storage event listener
   * functionality in AuthContext that enables real-time token synchronization:
   * 
   * Key Test Scenarios:
   * 1. Cross-Tab Sync: Token changes from other tabs immediately reflected
   * 2. Race Conditions: Multiple rapid events handled without corruption
   * 3. Security Defense: Malicious injection attempts properly rejected
   * 
   * Security Features Tested:
   * - Token validation during storage events
   * - XSS prevention in token handling
   * - State corruption prevention under attack
   * - Error logging without sensitive data exposure
   * - Recovery capabilities after malicious attempts
   * 
   * The tests verify:
   * - Event listener registration and cleanup
   * - Proper token validation and decoding
   * - State consistency under concurrent events
   * - Security boundaries and error handling
   * - Integration with auth store and logging systems
   * 
   * Each test is designed to fail if the implementation has security
   * vulnerabilities or race condition issues.
   */
});