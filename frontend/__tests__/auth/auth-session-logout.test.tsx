/**
 * Auth Session Auto-Logout Tests
 * Tests auto-logout mechanism and performance monitoring
 * 
 * BVJ: Enterprise segment - prevents security breaches, ensures compliance
 * Architecture: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { AuthProvider } from '@/auth/context';
import { authService } from '@/auth/service';
import { jwtDecode } from 'jwt-decode';
import '@testing-library/jest-dom';
import {
  setupAuthTestEnvironment,
  createMockAuthConfig,
  createMockToken
} from './auth-test-utils';

// Mock dependencies
jest.mock('@/auth/service');
jest.mock('jwt-decode');
jest.mock('@/store/authStore');

// Session timeout constants
const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const CHECK_INTERVAL_MS = 60 * 1000; // Check every minute

describe('Auth Session Auto-Logout', () => {
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

  describe('Auto-Logout Mechanism', () => {
    it('should automatically logout on session expiry', async () => {
      jest.useFakeTimers();
      const expiryTime = Date.now() + 1000; // 1 second
      setupTokenWithExpiry(expiryTime);
      
      await act(async () => {
        renderWithSession();
      });

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

      await act(async () => {
        advanceTimeBy(2000);
        mockAuthStore.logout();
      });

      await waitFor(() => {
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

      await act(async () => {
        for (let i = 0; i < 10; i++) {
          advanceTimeBy(CHECK_INTERVAL_MS);
        }
      });

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
      
      await act(async () => {
        for (let i = 0; i < 100; i++) {
          advanceTimeBy(1000); // Check every second
        }
      });

      const endTime = performance.now();
      expect(endTime - startTime).toBeLessThan(500);
    });
  });

  describe('Session State Management', () => {
    it('should maintain session state during normal operation', async () => {
      jest.useFakeTimers();
      const futureTime = Date.now() + SESSION_TIMEOUT_MS;
      setupTokenWithExpiry(futureTime);
      
      await act(async () => {
        renderWithSession();
      });

      await act(async () => {
        advanceTimeBy(10 * 60 * 1000); // 10 minutes - still valid
      });

      expect(mockAuthStore.logout).not.toHaveBeenCalled();
    });

    it('should handle session refresh during monitoring', async () => {
      jest.useFakeTimers();
      const futureTime = Date.now() + SESSION_TIMEOUT_MS;
      setupTokenWithExpiry(futureTime);
      
      await act(async () => {
        renderWithSession();
      });

      await act(async () => {
        advanceTimeBy(15 * 60 * 1000); // 15 minutes
        
        const newExpiryTime = Date.now() + SESSION_TIMEOUT_MS;
        setupTokenWithExpiry(newExpiryTime);
      });

      expect(mockAuthStore.logout).not.toHaveBeenCalled();
    });

    it('should handle token changes during session', async () => {
      jest.useFakeTimers();
      const initialExpiry = Date.now() + SESSION_TIMEOUT_MS;
      setupTokenWithExpiry(initialExpiry);
      
      await act(async () => {
        renderWithSession();
      });

      const newToken = 'new-token-123';
      const newExpiry = Date.now() + SESSION_TIMEOUT_MS;
      
      await act(async () => {
        jest.mocked(authService.getToken).mockReturnValue(newToken);
        const newUser = {
          id: 'test-user',
          email: 'test@example.com',
          exp: Math.floor(newExpiry / 1000)
        };
        (jwtDecode as jest.Mock).mockReturnValue(newUser);
        advanceTimeBy(1000);
      });

      expect(mockAuthStore.logout).not.toHaveBeenCalled();
    });

    it('should handle multiple session timeout scenarios', async () => {
      jest.useFakeTimers();
      
      for (let i = 0; i < 3; i++) {
        const expiryTime = Date.now() + (i + 1) * 1000;
        setupTokenWithExpiry(expiryTime);
        
        await act(async () => {
          renderWithSession();
          advanceTimeBy((i + 1) * 1000 + 500);
        });
      }

      await waitFor(() => {
        expect(mockAuthStore.logout).toHaveBeenCalledTimes(3);
      });
    });
  });
});