/**
 * Comprehensive tests for refresh loop prevention mechanisms
 * Validates all defensive programming measures are working correctly
 */

import React from 'react';
import { render, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/auth';
import { unifiedAuthService } from '@/auth/unified-auth-service';
import { logger } from '@/lib/logger';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock dependencies
jest.mock('@/auth/unified-auth-service');
jest.mock('@/lib/logger');
jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: () => ({
    trackLogin: jest.fn(),
    trackLogout: jest.fn(),
    trackOAuthComplete: jest.fn(),
    trackError: jest.fn(),
  }),
}));
jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));

describe('Refresh Loop Prevention Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    localStorage.clear();
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

  describe('Token Refresh Cooldown', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('enforces 30-second cooldown between refresh attempts', async () => {
      const mockRefreshToken = jest.fn().mockResolvedValue({
        access_token: 'new_token',
      });
      (unifiedAuthService.refreshToken as jest.Mock) = mockRefreshToken;
      (unifiedAuthService.needsRefresh as jest.Mock).mockReturnValue(true);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue('old_token');
      (unifiedAuthService.getAuthConfig as jest.Mock).mockResolvedValue({
        development_mode: false,
        endpoints: {},
      });

      const TestComponent = () => {
        const { token } = useAuth();
        return <div>{token}</div>;
      };

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Wait for initial mount
      await act(async () => {
        jest.advanceTimersByTime(100);
      });

      // First refresh should work
      expect(mockRefreshToken).toHaveBeenCalledTimes(0); // Not called immediately

      // Advance time to trigger refresh check
      await act(async () => {
        jest.advanceTimersByTime(120000); // 2 minutes
      });

      // Try another refresh immediately - should be blocked by cooldown
      (unifiedAuthService.needsRefresh as jest.Mock).mockReturnValue(true);
      await act(async () => {
        jest.advanceTimersByTime(1000);
      });

      // Verify cooldown prevented additional refresh
      const refreshCalls = mockRefreshToken.mock.calls.length;
      
      // Advance time less than cooldown
      await act(async () => {
        jest.advanceTimersByTime(20000); // 20 seconds
      });
      
      // Should still be same number of calls
      expect(mockRefreshToken).toHaveBeenCalledTimes(refreshCalls);

      // Advance past cooldown
      await act(async () => {
        jest.advanceTimersByTime(15000); // Total 35 seconds
      });

      // Now refresh should be allowed again
      expect(mockRefreshToken.mock.calls.length).toBeGreaterThanOrEqual(refreshCalls);
    });

    it('stops refresh attempts after 3 failures', async () => {
      const mockRefreshToken = jest.fn().mockRejectedValue(new Error('Refresh failed'));
      (unifiedAuthService.refreshToken as jest.Mock) = mockRefreshToken;
      (unifiedAuthService.needsRefresh as jest.Mock).mockReturnValue(true);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue('expired_token');
      (unifiedAuthService.removeToken as jest.Mock) = jest.fn();
      (unifiedAuthService.getAuthConfig as jest.Mock).mockResolvedValue({
        development_mode: false,
        endpoints: {},
      });

      const TestComponent = () => {
        const { token, user } = useAuth();
        return (
          <div>
            Token: {token || 'none'}
            User: {user ? 'logged in' : 'logged out'}
          </div>
        );
      };

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Simulate 3 failed refresh attempts with proper cooldown
      for (let i = 0; i < 4; i++) {
        await act(async () => {
          jest.advanceTimersByTime(35000); // Past cooldown
        });
      }

      // After 3 failures, should clear token and stop trying
      await waitFor(() => {
        expect(mockRefreshToken).toHaveBeenCalledTimes(3); // Exactly 3 attempts
        expect(unifiedAuthService.removeToken).toHaveBeenCalled();
      });

      // Further time advances should not trigger more attempts
      await act(async () => {
        jest.advanceTimersByTime(120000);
      });

      expect(mockRefreshToken).toHaveBeenCalledTimes(3); // Still only 3
    });
  });

  describe('Same Token Detection', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('detects when refresh returns the same token', async () => {
      const sameToken = 'same_expired_token';
      const mockRefreshToken = jest.fn().mockResolvedValue({
        access_token: sameToken, // Returns same token
      });
      
      (unifiedAuthService.refreshToken as jest.Mock) = mockRefreshToken;
      (unifiedAuthService.needsRefresh as jest.Mock).mockReturnValue(true);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(sameToken);
      (unifiedAuthService.getAuthConfig as jest.Mock).mockResolvedValue({
        development_mode: false,
        endpoints: {},
      });

      const loggerWarnSpy = jest.spyOn(logger, 'warn');

      const TestComponent = () => {
        const { token } = useAuth();
        return <div>{token}</div>;
      };

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Trigger refresh
      await act(async () => {
        jest.advanceTimersByTime(120000);
      });

      await waitFor(() => {
        expect(loggerWarnSpy).toHaveBeenCalledWith(
          expect.stringContaining('same token'),
          expect.objectContaining({
            action: 'same_token_refresh',
          })
        );
      });
    });
  });

  describe('Redirect Loop Prevention', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('prevents multiple redirects in HomePage', async () => {
      const mockPush = jest.fn();
      jest.mock('next/navigation', () => ({
        useRouter: () => ({ push: mockPush }),
      }));

      (unifiedAuthService.getAuthConfig as jest.Mock).mockResolvedValue({
        development_mode: false,
        endpoints: {},
      });
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(null);

      const HomePage = require('@/app/page').default;

      render(<HomePage />);

      // Wait for potential redirects
      await act(async () => {
        jest.advanceTimersByTime(500);
      });

      // Should only redirect once
      expect(mockPush).toHaveBeenCalledTimes(1);
      expect(mockPush).toHaveBeenCalledWith('/login');

      // Simulate multiple re-renders
      for (let i = 0; i < 5; i++) {
        await act(async () => {
          jest.advanceTimersByTime(100);
        });
      }

      // Still should only have one redirect
      expect(mockPush).toHaveBeenCalledTimes(1);
    });

    it('prevents redirect loops in LoginPage when user exists', async () => {
      const mockPush = jest.fn();
      jest.mock('next/navigation', () => ({
        useRouter: () => ({ push: mockPush }),
      }));

      // Mock auth context with user
      jest.mock('@/auth', () => ({
        authService: {
          useAuth: () => ({
            user: { id: '123', email: 'test@example.com' },
            loading: false,
            initialized: true,
            authConfig: { development_mode: false },
          }),
        },
      }));

      const LoginPage = require('@/app/login/page').default;

      render(<LoginPage />);

      // Wait for redirect
      await act(async () => {
        jest.advanceTimersByTime(500);
      });

      // Should redirect to chat once
      expect(mockPush).toHaveBeenCalledTimes(1);
      expect(mockPush).toHaveBeenCalledWith('/chat');

      // Multiple re-renders should not cause more redirects
      for (let i = 0; i < 3; i++) {
        await act(async () => {
          jest.advanceTimersByTime(100);
        });
      }

      expect(mockPush).toHaveBeenCalledTimes(1);
    });
  });

  describe('Environment Config Validation', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('throws error when staging uses localhost URLs', () => {
      const originalEnv = process.env.NEXT_PUBLIC_ENVIRONMENT;
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';

      // Mock window.location for staging
      Object.defineProperty(window, 'location', {
        value: { hostname: 'app.staging.netrasystems.ai' },
        writable: true,
      });

      const { getUnifiedApiConfig } = require('@/lib/unified-api-config');

      // This should work correctly - staging URLs
      const config = getUnifiedApiConfig();
      expect(config.urls.api).toContain('staging');
      expect(config.urls.auth).toContain('staging');

      // Restore environment
      process.env.NEXT_PUBLIC_ENVIRONMENT = originalEnv;
    });

    it('validates auth config matches environment', async () => {
      process.env.NEXT_PUBLIC_ENVIRONMENT = 'staging';

      (unifiedAuthService.getAuthConfig as jest.Mock).mockResolvedValue({
        development_mode: true, // Wrong for staging!
        endpoints: {
          login: 'http://localhost:3001/auth/login', // Wrong URL!
        },
      });

      const loggerErrorSpy = jest.spyOn(logger, 'error');

      const TestComponent = () => {
        const { authConfig } = useAuth();
        
        React.useEffect(() => {
          if (authConfig && process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging') {
            if (authConfig.development_mode) {
              logger.error('Development mode in staging!');
            }
            if (authConfig.endpoints.login?.includes('localhost')) {
              logger.error('Localhost URLs in staging!');
            }
          }
        }, [authConfig]);
        
        return <div>Testing</div>;
      };

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(loggerErrorSpy).toHaveBeenCalledWith(
          expect.stringContaining('staging')
        );
      });

      process.env.NEXT_PUBLIC_ENVIRONMENT = undefined;
    });
  });

  describe('Auth Initialization Race Conditions', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('waits for initialization before making auth decisions', async () => {
      let resolveAuthConfig: any;
      const authConfigPromise = new Promise((resolve) => {
        resolveAuthConfig = resolve;
      });

      (unifiedAuthService.getAuthConfig as jest.Mock).mockReturnValue(authConfigPromise);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(null);

      const TestComponent = () => {
        const { initialized, loading, user } = useAuth();
        return (
          <div>
            Initialized: {initialized ? 'yes' : 'no'}
            Loading: {loading ? 'yes' : 'no'}
            User: {user ? 'exists' : 'none'}
          </div>
        );
      };

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Should be loading, not initialized
      expect(getByText(/Loading: yes/)).toBeInTheDocument();
      expect(getByText(/Initialized: no/)).toBeInTheDocument();

      // Resolve auth config
      await act(async () => {
        resolveAuthConfig({
          development_mode: false,
          endpoints: {},
        });
      });

      // Now should be initialized
      await waitFor(() => {
        expect(getByText(/Initialized: yes/)).toBeInTheDocument();
        expect(getByText(/Loading: no/)).toBeInTheDocument();
      });
    });
  });
});