/**
 * Auth Configuration Loop Prevention Tests
 * 
 * These tests verify that the auth context does not create infinite loops
 * when fetching configuration, especially in staging where the auth service
 * might be unavailable or return errors.
 * 
 * ISSUE FIXED: Frontend was continuously calling config endpoint in a loop on staging
 */

import React from 'react';
import { render, waitFor, act } from '@testing-library/react';
import { unifiedAuthService } from '@/auth/unified-auth-service';

// Mock dependencies (store and logger are already mocked globally)
jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));
jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
    debug: jest.fn(),
  },
}));

describe('Auth Configuration Loop Prevention', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let getAuthConfigSpy: jest.SpyInstance;
  let getTokenSpy: jest.SpyInstance;
  let AuthProvider: any;

  beforeEach(async () => {
    jest.clearAllMocks();
    
    // Reset React component state by unmounting and clearing render cache
    jest.clearAllTimers();
    
    // CRITICAL: Dynamic import to get fresh AuthProvider instance for each test
    // This ensures hasMountedRef.current is reset between tests
    delete require.cache[require.resolve('@/auth/context')];
    const contextModule = await import('@/auth/context');
    AuthProvider = contextModule.AuthProvider;
    
    // Work with the globally mocked unifiedAuthService - reset and configure
    (unifiedAuthService.getAuthConfig as jest.Mock).mockResolvedValue({
      development_mode: false,
      google_client_id: 'test-client-id',
      endpoints: {
        login: '/auth/login',
        logout: '/auth/logout',
        callback: '/auth/callback',
        token: '/auth/token',
        user: '/auth/me',
      },
      authorized_javascript_origins: ['https://app.staging.netrasystems.ai'],
      authorized_redirect_uris: ['https://app.staging.netrasystems.ai/auth/callback'],
    });
    
    // Mock other methods on the globally mocked service
    (unifiedAuthService.getToken as jest.Mock).mockReturnValue(null);
    (unifiedAuthService.removeToken as jest.Mock).mockImplementation(() => {});
    (unifiedAuthService.getDevLogoutFlag as jest.Mock).mockReturnValue(false);
    (unifiedAuthService.handleDevLogin as jest.Mock).mockResolvedValue(null);
    
    // Store reference for easy access in tests
    getAuthConfigSpy = unifiedAuthService.getAuthConfig as jest.Mock;
    getTokenSpy = unifiedAuthService.getToken as jest.Mock;
  });

  afterEach(() => {
    jest.restoreAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  test('should prevent config fetch loops during component re-renders', async () => {
    // Record initial state - the loop prevention mechanism may mean config is never fetched
    // if the AuthProvider has already been initialized in previous tests
    const initialCallCount = getAuthConfigSpy.mock.calls.length;

    const TestComponent = () => {
      const [counter, setCounter] = React.useState(0);
      
      // Force multiple re-renders to test loop prevention
      React.useEffect(() => {
        const timer = setInterval(() => {
          act(() => {
            setCounter(c => {
              // Stop after a few renders to avoid infinite loop
              return c < 5 ? c + 1 : c;
            });
          });
        }, 50);
        
        return () => clearInterval(timer);
      }, []);
      
      return (
        <AuthProvider>
          <div data-testid="child">Render {counter}</div>
        </AuthProvider>
      );
    };

    const { getByTestId, unmount } = render(<TestComponent />);

    // Wait for initial mount
    await waitFor(() => {
      expect(getByTestId('child')).toBeInTheDocument();
    });

    // Wait for multiple re-renders to occur
    await waitFor(() => {
      expect(getByTestId('child').textContent).toMatch(/Render [0-9]+/);
    }, { timeout: 1000 });

    // Wait a bit more to ensure re-renders have completed
    await new Promise(resolve => setTimeout(resolve, 500));
    
    unmount();

    // CRITICAL: Loop prevention should ensure config is never fetched more than once
    // Even if component re-renders multiple times or has multiple AuthProvider instances
    const finalCallCount = getAuthConfigSpy.mock.calls.length;
    const additionalCalls = finalCallCount - initialCallCount;
    
    // Due to loop prevention guard, should be 0 or 1 additional calls at most
    expect(additionalCalls).toBeLessThanOrEqual(1);
    
    // The important thing is that it doesn't call getAuthConfig for every re-render
    // If it was broken, we'd see many calls (5+ based on our render count)
    expect(additionalCalls).toBeLessThan(3);
  });

  test('should not create infinite loop when auth config fetch fails', async () => {
    // Setup: Mock getAuthConfig to fail (simulating staging auth service down)
    (unifiedAuthService.getAuthConfig as jest.Mock).mockRejectedValue(new Error('Auth service unavailable'));
    const initialCallCount = getAuthConfigSpy.mock.calls.length;

    const { container } = render(
      <AuthProvider>
        <div data-testid="child">Test Content</div>
      </AuthProvider>
    );

    // Wait for error handling
    await waitFor(() => {
      expect(container.querySelector('[data-testid="child"]')).toBeInTheDocument();
    }, { timeout: 2000 });

    // CRITICAL: Loop prevention should ensure no infinite loops even on failures
    const finalCallCount = getAuthConfigSpy.mock.calls.length;
    const additionalCalls = finalCallCount - initialCallCount;
    expect(additionalCalls).toBeLessThanOrEqual(1);
    
    // Wait a bit more to ensure no additional calls
    await new Promise(resolve => setTimeout(resolve, 500));
    const endCallCount = getAuthConfigSpy.mock.calls.length;
    
    // Should not increase after the initial attempt
    expect(endCallCount).toBe(finalCallCount);
  });

  test('should not retry config fetch when dependencies change', async () => {
    // Track call count to verify loop prevention during state changes
    const initialCallCount = getAuthConfigSpy.mock.calls.length;

    const TestComponent = () => {
      const [state, setState] = React.useState(0);
      
      return (
        <AuthProvider>
          <button onClick={() => setState(s => s + 1)} data-testid="trigger">
            Trigger State Change {state}
          </button>
        </AuthProvider>
      );
    };

    const { getByTestId } = render(<TestComponent />);

    // Wait for initial mount
    await waitFor(() => {
      expect(getByTestId('trigger')).toBeInTheDocument();
    });

    // Trigger state changes that might cause re-renders
    const button = getByTestId('trigger');
    
    act(() => {
      button.click();
    });
    await waitFor(() => expect(button.textContent).toContain('1'));
    
    act(() => {
      button.click();
    });
    await waitFor(() => expect(button.textContent).toContain('2'));

    // CRITICAL: Loop prevention should ensure stable call count despite state changes
    const finalCallCount = getAuthConfigSpy.mock.calls.length;
    const additionalCalls = finalCallCount - initialCallCount;
    expect(additionalCalls).toBeLessThanOrEqual(1);
  });

  test('should handle rapid mount/unmount cycles without creating loops', async () => {
    // Track initial call count before rapid mount/unmount test
    const initialCallCount = getAuthConfigSpy.mock.calls.length;
    
    // Setup custom mock for this test - simulate slow network response
    (unifiedAuthService.getAuthConfig as jest.Mock).mockImplementation(() => {
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            development_mode: false,
            google_client_id: 'test-client-id',
            endpoints: {
              login: '/auth/login',
              logout: '/auth/logout',
              callback: '/auth/callback',
              token: '/auth/token',
              user: '/auth/me',
            },
            authorized_javascript_origins: ['https://app.staging.netrasystems.ai'],
            authorized_redirect_uris: ['https://app.staging.netrasystems.ai/auth/callback'],
          });
        }, 500);
      });
    });

    // Mount and unmount rapidly
    const { unmount: unmount1 } = render(
      <AuthProvider>
        <div>Test 1</div>
      </AuthProvider>
    );
    
    // Unmount quickly before config fetch completes
    setTimeout(() => unmount1(), 100);
    
    // Mount again
    const { unmount: unmount2 } = render(
      <AuthProvider>
        <div>Test 2</div>
      </AuthProvider>
    );
    
    // Wait for any pending operations
    await waitFor(() => {}, { timeout: 1000 });
    
    unmount2();

    // CRITICAL: Loop prevention should limit calls even during rapid mount/unmount
    // Due to the hasMountedRef guard, we should see at most 1-2 additional calls
    const finalCallCount = getAuthConfigSpy.mock.calls.length;
    const additionalCalls = finalCallCount - initialCallCount;
    expect(additionalCalls).toBeLessThanOrEqual(2);
  });

  test('should prevent config fetch loop even with token refresh attempts', async () => {
    // Track initial call count before complex auth flow test
    const initialCallCount = getAuthConfigSpy.mock.calls.length;
    
    // Setup: Simulate expired token scenario
    const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMSIsImVtYWlsIjoidGVzdEB0ZXN0LmNvbSIsImV4cCI6MTYwMDAwMDAwMH0.test';
    (unifiedAuthService.getToken as jest.Mock).mockReturnValue(expiredToken);
    (unifiedAuthService.refreshToken as jest.Mock).mockRejectedValue(new Error('Token refresh failed'));

    render(
      <AuthProvider>
        <div data-testid="child">Test</div>
      </AuthProvider>
    );

    // Wait for auth flow to complete
    await waitFor(() => {}, { timeout: 2000 });

    // CRITICAL: Loop prevention should ensure stable call count despite token refresh failures
    const finalCallCount = getAuthConfigSpy.mock.calls.length;
    const additionalCalls = finalCallCount - initialCallCount;
    expect(additionalCalls).toBeLessThanOrEqual(1);
  });
});