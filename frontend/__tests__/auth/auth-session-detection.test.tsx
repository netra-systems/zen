/**
 * Auth Session Detection Tests
 * Tests session expiry detection and warning system
 * 
 * BVJ: Enterprise segment - prevents security breaches, ensures compliance
 * Architecture: ≤300 lines, functions ≤8 lines
 */

import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, AuthContext } from '@/auth/context';
import { authService } from '@/auth/unified-auth-service';
import { jwtDecode } from 'jwt-decode';
import { logger } from '@/lib/logger';
import '@testing-library/jest-dom';
import { setupAuthTestEnvironment,
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

describe('Auth Session Detection', () => {
  setupAntiHang();
    jest.setTimeout(10000);
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
    
    realDateNow = Date.now;
    Date.now = jest.fn();
    
    const mockConfig = createMockAuthConfig();
    jest.mocked(authService.getAuthConfig).mockResolvedValue(mockConfig);
  });

  afterEach(() => {
    Date.now = realDateNow;
    jest.clearAllMocks();
    jest.clearAllTimers();
      cleanupAntiHang();
  });

  const setupTokenWithExpiry = (expiryTimeMs: number) => {
    const mockToken = createMockToken();
    const mockUser = {
      id: 'test-user',
      email: 'test@example.com',
      exp: Math.floor(expiryTimeMs / 1000)
    };
    
    jest.mocked(authService.getToken).mockReturnValue(mockToken);
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
        setupAntiHang();
      jest.setTimeout(10000);
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
      
      jest.mocked(authService.getToken).mockReturnValue(mockToken);
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
        setupAntiHang();
      jest.setTimeout(10000);
    it('should warn user before session expires', async () => {
      jest.useFakeTimers();
      const warningTime = Date.now() + WARNING_THRESHOLD_MS - 1000;
      setupTokenWithExpiry(warningTime + SESSION_TIMEOUT_MS);
      
      await act(async () => {
        renderWithSession();
      });

      await act(async () => {
        advanceTimeBy(WARNING_THRESHOLD_MS - 1000);
      });

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
        advanceTimeBy(WARNING_THRESHOLD_MS - 2000);
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
        advanceTimeBy(5 * 60 * 1000); // 5 minutes
      });

      await waitFor(() => {
        expect(logger.debug).toHaveBeenCalledWith(
          expect.stringMatching(/session.*remaining/i),
          expect.any(Object)
        );
      });
    });
  });

  describe('Edge Cases and Error Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle system clock changes gracefully', async () => {
      jest.useFakeTimers();
      const futureTime = Date.now() + SESSION_TIMEOUT_MS;
      setupTokenWithExpiry(futureTime);
      
      await act(async () => {
        renderWithSession();
        (Date.now as jest.Mock).mockReturnValue(Date.now() - (24 * 60 * 60 * 1000));
        advanceTimeBy(1000);
      });

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
      
      (authService as any).validateSession = jest.fn().mockRejectedValue(
        new Error('Network error')
      );

      await act(async () => {
        renderWithSession();
        advanceTimeBy(60 * 1000); // 1 minute
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
      
      jest.mocked(authService.getToken).mockReturnValue(mockToken);
      (jwtDecode as jest.Mock).mockReturnValue(userWithoutExp);

      await act(async () => {
        renderWithSession();
      });

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

      Object.defineProperty(document, 'hidden', { value: true, writable: true });
      document.dispatchEvent(new Event('visibilitychange'));

      await act(async () => {
        advanceTimeBy(SESSION_TIMEOUT_MS + 1000);
      });

      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });
  });
});