/**
 * Auth Token Refresh Failure Handling Tests
 * Tests failure handling, persistence, and performance scenarios
 * 
 * BVJ: Enterprise segment - ensures robust error handling and optimal performance
 * Architecture: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { AuthProvider } from '@/auth/context';
import { authService } from '@/auth/service';
import { jwtDecode } from 'jwt-decode';
import { logger } from '@/lib/logger';
import '@testing-library/jest-dom';
import {
  setupAuthTestEnvironment,
  createMockAuthConfig,
  createMockToken
} from './auth-test-utils';

// Mock dependencies
jest.mock('@/auth/service');
jest.mock('jwt-decode');
jest.mock('@/lib/logger');
jest.mock('@/store/authStore');
jest.mock('@/lib/auth-service-config');

// Token refresh constants
const REFRESH_RETRY_DELAY_MS = 1000; // 1 second retry delay
const MAX_REFRESH_RETRIES = 3;

describe('Auth Token Refresh Failure Handling', () => {
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
      updateToken: jest.fn(),
      reset: jest.fn()
    };
    
    require('@/store/authStore').useAuthStore.mockReturnValue(mockAuthStore);
    
    realDateNow = Date.now;
    Date.now = jest.fn().mockReturnValue(Date.now());
    
    const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
    mockAuthServiceClient.refreshToken = jest.fn();
    
    const mockConfig = createMockAuthConfig();
    (authService.getAuthConfig as jest.Mock).mockResolvedValue(mockConfig);
  });

  afterEach(() => {
    Date.now = realDateNow;
    jest.clearAllMocks();
    jest.clearAllTimers();
  });

  const createExpiringToken = (minutesUntilExpiry: number) => {
    const expiryTime = Date.now() + (minutesUntilExpiry * 60 * 1000);
    const mockUser = {
      id: 'test-user',
      email: 'test@example.com',
      exp: Math.floor(expiryTime / 1000)
    };
    
    const mockToken = createMockToken();
    (authService.getToken as jest.Mock).mockReturnValue(mockToken);
    (jwtDecode as jest.Mock).mockReturnValue(mockUser);
    
    return { mockToken, mockUser, expiryTime };
  };

  const renderWithTokenRefresh = () => {
    return render(
      <AuthProvider>
        <div data-testid="app-content">Test App</div>
      </AuthProvider>
    );
  };

  const advanceTimeBy = (milliseconds: number) => {
    const currentTime = (Date.now as jest.Mock).getMockReturnValue();
    (Date.now as jest.Mock).mockReturnValue(currentTime + milliseconds);
    jest.advanceTimersByTime(milliseconds);
  };

  describe('Token Refresh Failure Handling', () => {
    it('should logout user on refresh failure', async () => {
      createExpiringToken(3); // 3 minutes until expiry
      
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockRejectedValue(
        new Error('Refresh failed')
      );

      await act(async () => {
        renderWithTokenRefresh();
        advanceTimeBy(1000);
      });

      await waitFor(() => {
        expect(logger.error).toHaveBeenCalledWith(
          expect.stringMatching(/token.*refresh.*failed/i),
          expect.any(Error)
        );
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });

    it('should retry refresh with exponential backoff', async () => {
      jest.useFakeTimers();
      createExpiringToken(3); // 3 minutes until expiry
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Server error'))
        .mockResolvedValueOnce({
          access_token: 'new-token',
          expires_in: 1800
        });

      await act(async () => {
        renderWithTokenRefresh();
        for (let i = 0; i < MAX_REFRESH_RETRIES; i++) {
          advanceTimeBy(REFRESH_RETRY_DELAY_MS * Math.pow(2, i));
        }
      });

      await waitFor(() => {
        expect(mockAuthServiceClient.refreshToken).toHaveBeenCalledTimes(3);
      });
    });

    it('should handle network failures during refresh gracefully', async () => {
      createExpiringToken(2); // 2 minutes until expiry
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockRejectedValue(
        new Error('Network unreachable')
      );

      await act(async () => {
        renderWithTokenRefresh();
        advanceTimeBy(1000);
      });

      await waitFor(() => {
        expect(logger.error).toHaveBeenCalledWith(
          expect.stringMatching(/network.*error/i),
          expect.any(Error)
        );
      });
    });

    it('should clear invalid refresh tokens', async () => {
      createExpiringToken(3); // 3 minutes until expiry
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockRejectedValue({
        status: 400,
        message: 'Invalid refresh token'
      });

      await act(async () => {
        renderWithTokenRefresh();
        advanceTimeBy(1000);
      });

      await waitFor(() => {
        expect(authService.removeToken).toHaveBeenCalled();
        expect(mocks.localStorageMock.removeItem).toHaveBeenCalledWith('jwt_token');
      });
    });
  });

  describe('Refresh Token Persistence', () => {
    it('should store and use refresh tokens securely', async () => {
      createExpiringToken(4); // 4 minutes until expiry
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockResolvedValue({
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        expires_in: 1800
      });

      await act(async () => {
        renderWithTokenRefresh();
        advanceTimeBy(1000);
      });

      await waitFor(() => {
        expect(mocks.localStorageMock.setItem).toHaveBeenCalledWith(
          'refresh_token',
          'new-refresh-token'
        );
      });
    });

    it('should remove expired refresh tokens', async () => {
      createExpiringToken(2); // 2 minutes until expiry
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockRejectedValue({
        status: 401,
        message: 'Refresh token expired'
      });

      await act(async () => {
        renderWithTokenRefresh();
        advanceTimeBy(1000);
      });

      await waitFor(() => {
        expect(mocks.localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
        expect(mockAuthStore.logout).toHaveBeenCalled();
      });
    });
  });

  describe('Token Refresh Performance', () => {
    it('should refresh tokens efficiently without blocking UI', async () => {
      createExpiringToken(4); // 4 minutes until expiry
      
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockImplementation(() =>
        new Promise(resolve => setTimeout(() => resolve({
          access_token: 'fast-token',
          expires_in: 1800
        }), 10))
      );

      const startTime = performance.now();
      
      await act(async () => {
        renderWithTokenRefresh();
        advanceTimeBy(1000);
      });

      const endTime = performance.now();
      expect(endTime - startTime).toBeLessThan(100);
    });

    it('should cache refresh attempts to avoid duplicates', async () => {
      createExpiringToken(3); // 3 minutes until expiry
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      let refreshCount = 0;
      mockAuthServiceClient.refreshToken.mockImplementation(() => {
        refreshCount++;
        return Promise.resolve({
          access_token: `token-${refreshCount}`,
          expires_in: 1800
        });
      });

      await act(async () => {
        renderWithTokenRefresh();
        for (let i = 0; i < 5; i++) {
          advanceTimeBy(100);
        }
      });

      await waitFor(() => {
        expect(refreshCount).toBeLessThanOrEqual(2);
      });
    });

    it('should handle high-frequency token validation efficiently', async () => {
      createExpiringToken(10); // 10 minutes - no refresh needed
      const startTime = performance.now();
      
      await act(async () => {
        renderWithTokenRefresh();
        for (let i = 0; i < 50; i++) {
          authService.getAuthHeaders();
        }
      });

      const endTime = performance.now();
      expect(endTime - startTime).toBeLessThan(50);
    });
  });
});