/**
 * Auth Session Timeout Tests - Elite Edge Case Coverage
 * ====================================================
 * Tests session timeout handling, auto-logout, and cleanup mechanisms
 * 
 * BVJ: Enterprise segment - prevents security breaches, ensures compliance
 * Architecture: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, AuthContext } from '@/auth/context';
import { authService } from '@/auth/service';
import { jwtDecode } from 'jwt-decode';
import { logger } from '@/lib/logger';
import '@testing-library/jest-dom';
import {
  setupAuthTestEnvironment,
  createMockAuthConfig,
  createMockToken,
  mockAuthServiceClient
} from './auth-test-utils';

// Mock dependencies
jest.mock('@/auth/service');
jest.mock('jwt-decode');
jest.mock('@/lib/logger');
jest.mock('@/store/authStore');

// Session timeout constants
const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const WARNING_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes before timeout
const CHECK_INTERVAL_MS = 60 * 1000; // Check every minute

describe('Auth Session Timeout Handling', () => {
  let mocks: ReturnType<typeof setupAuthTestEnvironment>;
  let mockAuthStore: any;
  let realDateNow: typeof Date.now;

  beforeEach(() => {
    mocks = setupAuthTestEnvironment();
    mockAuthStore = {
      user: null,
      token: null,
      login: jest.fn(),
      logout: jest.fn(),
      reset: jest.fn()
    };
    
    require('@/store/authStore').useAuthStore.mockReturnValue(mockAuthStore);
    
    // Mock Date.now for time-based tests
    realDateNow = Date.now;
    Date.now = jest.fn();
    
    // Setup basic auth config
    const mockConfig = createMockAuthConfig();
    (authService.getAuthConfig as jest.Mock).mockResolvedValue(mockConfig);
  });

  afterEach(() => {
    Date.now = realDateNow;
    jest.clearAllMocks();
    jest.clearAllTimers();
  });

  const setupTokenWithExpiry = (expiryTimeMs: number) => {
    const mockToken = createMockToken();
    const mockUser = {
      id: 'test-user',
      email: 'test@example.com',
      exp: Math.floor(expiryTimeMs / 1000)
    };
    
    (authService.getToken as jest.Mock).mockReturnValue(mockToken);
    (jwtDecode as jest.Mock).mockReturnValue(mockUser);
    return { mockToken, mockUser };
  };

  const renderWithSession = () => {
    return render(
      <AuthProvider>
        <div data-testid="app-content">Test App</div>
      </AuthProvider>
    );
  };

  const advanceTimeBy = (milliseconds: number) => {
    const currentTime = (Date.now as jest.Mock).getMockReturnValue() || 0;
    (Date.now as jest.Mock).mockReturnValue(currentTime + milliseconds);
    jest.advanceTimersByTime(milliseconds);
  };

  describe('Session Expiry Detection', () => {
    it('should detect expired token on initialization', async () => {
      const pastTime = Date.now() - (60 * 60 * 1000); // 1 hour ago
      setupTokenWithExpiry(pastTime);
      
      await act(async () => {
        renderWithSession();
      });

      await waitFor(() => {
        expect(authService.removeToken).toHaveBeenCalled();
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });

    it('should handle invalid expiry dates gracefully', async () => {
      const mockToken = createMockToken();
      const invalidUser = { id: 'test-user', exp: 'invalid' };
      
      (authService.getToken as jest.Mock).mockReturnValue(mockToken);
      (jwtDecode as jest.Mock).mockReturnValue(invalidUser);

      await act(async () => {
        renderWithSession();
      });

      await waitFor(() => {
        expect(logger.error).toHaveBeenCalledWith(
          'Invalid token detected',
          expect.any(Error),
          expect.objectContaining({
            component: 'AuthContext'
          })
        );
      });
    });

    it('should validate token expiry on every check', async () => {
      jest.useFakeTimers();
      const futureTime = Date.now() + SESSION_TIMEOUT_MS;
      setupTokenWithExpiry(futureTime);
      
      await act(async () => {
        renderWithSession();
      });

      // Advance time past expiry
      await act(async () => {
        advanceTimeBy(SESSION_TIMEOUT_MS + 1000);
      });

      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });

    it('should start session timeout monitoring after login', async () => {
      const futureTime = Date.now() + SESSION_TIMEOUT_MS;
      setupTokenWithExpiry(futureTime);
      
      await act(async () => {
        renderWithSession();
      });

      await waitFor(() => {
        expect(screen.getByTestId('app-content')).toBeInTheDocument();
        expect(mockAuthStore.login).toHaveBeenCalled();
      });
    });
  });

  describe('Session Warning System', () => {
    it('should warn user before session expires', async () => {
      jest.useFakeTimers();
      const warningTime = Date.now() + WARNING_THRESHOLD_MS - 1000;
      setupTokenWithExpiry(warningTime + SESSION_TIMEOUT_MS);
      
      await act(async () => {
        renderWithSession();
      });

      // Advance to warning threshold
      await act(async () => {
        advanceTimeBy(WARNING_THRESHOLD_MS - 1000);
      });

      // Should warn about upcoming expiry
      await waitFor(() => {
        expect(logger.warn).toHaveBeenCalledWith(
          expect.stringMatching(/session.*expir/i),
          expect.any(Object)
        );
      });
    });

    it('should provide session extension option', async () => {
      jest.useFakeTimers();
      const futureTime = Date.now() + WARNING_THRESHOLD_MS;
      setupTokenWithExpiry(futureTime);
      
      const mockExtendSession = jest.fn().mockResolvedValue(true);
      (authService as any).extendSession = mockExtendSession;

      await act(async () => {
        renderWithSession();
      });

      // Simulate user activity during warning period
      await act(async () => {
        advanceTimeBy(WARNING_THRESHOLD_MS - 2000);
        // User activity should trigger extension
        const appContent = screen.getByTestId('app-content');
        await userEvent.click(appContent);
      });

      await waitFor(() => {
        expect(mockExtendSession).toHaveBeenCalled();
      });
    });

    it('should handle session extension failures', async () => {
      jest.useFakeTimers();
      const futureTime = Date.now() + WARNING_THRESHOLD_MS;
      setupTokenWithExpiry(futureTime);
      
      const mockExtendSession = jest.fn().mockRejectedValue(new Error('Extension failed'));
      (authService as any).extendSession = mockExtendSession;

      await act(async () => {
        renderWithSession();
      });

      await act(async () => {
        advanceTimeBy(WARNING_THRESHOLD_MS + 1000);
      });

      await waitFor(() => {
        expect(logger.error).toHaveBeenCalledWith(
          expect.stringMatching(/session.*extension.*failed/i),
          expect.any(Error)
        );
      });
    });

    it('should count down remaining session time', async () => {
      jest.useFakeTimers();
      const expiryTime = Date.now() + (10 * 60 * 1000); // 10 minutes
      setupTokenWithExpiry(expiryTime);
      
      await act(async () => {
        renderWithSession();
      });

      // Advance time and check countdown
      await act(async () => {
        advanceTimeBy(5 * 60 * 1000); // 5 minutes
      });

      await waitFor(() => {
        // Should log remaining time
        expect(logger.debug).toHaveBeenCalledWith(
          expect.stringMatching(/session.*remaining/i),
          expect.any(Object)
        );
      });
    });
  });

  describe('Auto-Logout Mechanism', () => {
    it('should automatically logout on session expiry', async () => {
      jest.useFakeTimers();
      const expiryTime = Date.now() + 1000; // 1 second
      setupTokenWithExpiry(expiryTime);
      
      await act(async () => {
        renderWithSession();
      });

      // Advance past expiry
      await act(async () => {
        advanceTimeBy(2000);
      });

      await waitFor(() => {
        expect(authService.removeToken).toHaveBeenCalled();
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });

    it('should clear all session data on auto-logout', async () => {
      jest.useFakeTimers();
      const expiryTime = Date.now() + 1000;
      setupTokenWithExpiry(expiryTime);
      
      await act(async () => {
        renderWithSession();
      });

      await act(async () => {
        advanceTimeBy(2000);
      });

      await waitFor(() => {
        expect(mocks.localStorageMock.removeItem).toHaveBeenCalledWith('jwt_token');
        expect(mockAuthStore.reset).toHaveBeenCalled();
      });
    });

    it('should redirect to login after auto-logout', async () => {
      jest.useFakeTimers();
      const expiryTime = Date.now() + 1000;
      setupTokenWithExpiry(expiryTime);
      
      await act(async () => {
        renderWithSession();
      });

      await act(async () => {
        advanceTimeBy(2000);
      });

      await waitFor(() => {
        expect(mocks.locationUtils.mockLocationAssign).toHaveBeenCalledWith('/');
      });
    });

    it('should handle concurrent logout attempts gracefully', async () => {
      jest.useFakeTimers();
      const expiryTime = Date.now() + 1000;
      setupTokenWithExpiry(expiryTime);
      
      await act(async () => {
        renderWithSession();
      });

      // Simulate multiple logout triggers
      await act(async () => {
        advanceTimeBy(2000);
        // Manual logout during auto-logout
        mockAuthStore.logout();
      });

      await waitFor(() => {
        // Should only logout once
        expect(authService.removeToken).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Session Monitoring Performance', () => {
    it('should monitor session efficiently', async () => {
      jest.useFakeTimers();
      const futureTime = Date.now() + SESSION_TIMEOUT_MS;
      setupTokenWithExpiry(futureTime);
      
      const startTime = performance.now();
      
      await act(async () => {
        renderWithSession();
        advanceTimeBy(CHECK_INTERVAL_MS * 5); // 5 minutes
      });

      const endTime = performance.now();
      const totalTime = endTime - startTime;
      
      expect(totalTime).toBeLessThan(100); // Should be very fast
    });

    it('should not cause memory leaks during monitoring', async () => {
      jest.useFakeTimers();
      const futureTime = Date.now() + SESSION_TIMEOUT_MS;
      setupTokenWithExpiry(futureTime);
      
      await act(async () => {
        renderWithSession();
      });

      // Simulate long session monitoring
      await act(async () => {
        for (let i = 0; i < 10; i++) {
          advanceTimeBy(CHECK_INTERVAL_MS);
        }
      });

      // Should not accumulate timers or listeners
      expect(jest.getTimerCount()).toBeLessThan(5);
    });

    it('should cleanup timers on unmount', async () => {
      jest.useFakeTimers();
      const futureTime = Date.now() + SESSION_TIMEOUT_MS;
      setupTokenWithExpiry(futureTime);
      
      const { unmount } = await act(async () => {
        return renderWithSession();
      });

      await act(async () => {
        unmount();
      });

      // All timers should be cleared
      expect(jest.getTimerCount()).toBe(0);
    });

    it('should handle rapid session checks without performance impact', async () => {
      jest.useFakeTimers();
      const futureTime = Date.now() + SESSION_TIMEOUT_MS;
      setupTokenWithExpiry(futureTime);
      
      await act(async () => {
        renderWithSession();
      });

      const startTime = performance.now();
      
      // Rapid session checks
      await act(async () => {
        for (let i = 0; i < 100; i++) {
          advanceTimeBy(1000); // Check every second
        }
      });

      const endTime = performance.now();
      expect(endTime - startTime).toBeLessThan(500);
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle system clock changes gracefully', async () => {
      jest.useFakeTimers();
      const futureTime = Date.now() + SESSION_TIMEOUT_MS;
      setupTokenWithExpiry(futureTime);
      
      await act(async () => {
        renderWithSession();
      });

      // Simulate system clock jump backwards
      await act(async () => {
        (Date.now as jest.Mock).mockReturnValue(Date.now() - (24 * 60 * 60 * 1000));
        advanceTimeBy(1000);
      });

      // Should handle gracefully without immediate logout
      await waitFor(() => {
        expect(logger.warn).toHaveBeenCalledWith(
          expect.stringMatching(/clock.*change/i),
          expect.any(Object)
        );
      });
    });

    it('should handle network failures during session validation', async () => {
      jest.useFakeTimers();
      const futureTime = Date.now() + SESSION_TIMEOUT_MS;
      setupTokenWithExpiry(futureTime);
      
      // Mock network failure
      (authService as any).validateSession = jest.fn().mockRejectedValue(
        new Error('Network error')
      );

      await act(async () => {
        renderWithSession();
        advanceTimeBy(CHECK_INTERVAL_MS);
      });

      await waitFor(() => {
        expect(logger.error).toHaveBeenCalledWith(
          expect.stringMatching(/session.*validation.*failed/i),
          expect.any(Error)
        );
      });
    });

    it('should handle missing token expiry gracefully', async () => {
      const mockToken = createMockToken();
      const userWithoutExp = { id: 'test-user', email: 'test@example.com' };
      
      (authService.getToken as jest.Mock).mockReturnValue(mockToken);
      (jwtDecode as jest.Mock).mockReturnValue(userWithoutExp);

      await act(async () => {
        renderWithSession();
      });

      // Should not crash, should use default timeout
      await waitFor(() => {
        expect(logger.warn).toHaveBeenCalledWith(
          expect.stringMatching(/missing.*expiry/i),
          expect.any(Object)
        );
      });
    });

    it('should handle browser tab visibility changes', async () => {
      jest.useFakeTimers();
      const futureTime = Date.now() + SESSION_TIMEOUT_MS;
      setupTokenWithExpiry(futureTime);
      
      await act(async () => {
        renderWithSession();
      });

      // Simulate tab becoming hidden
      Object.defineProperty(document, 'hidden', { value: true, writable: true });
      document.dispatchEvent(new Event('visibilitychange'));

      await act(async () => {
        advanceTimeBy(SESSION_TIMEOUT_MS + 1000);
      });

      // Should still logout when tab is hidden
      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });
  });
});