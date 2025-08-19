/**
 * Auth Token Refresh Tests - Elite Edge Case Coverage
 * ==================================================
 * Tests token refresh during active sessions, automatic refresh, and failure handling
 * 
 * BVJ: Enterprise segment - ensures seamless user experience, prevents auth interruptions
 * Architecture: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '@/auth/context';
import { authService } from '@/auth/service';
import { jwtDecode } from 'jwt-decode';
import { logger } from '@/lib/logger';
import '@testing-library/jest-dom';
import {
  setupAuthTestEnvironment,
  createMockAuthConfig,
  createMockToken,
  createSuccessResponse,
  createErrorResponse
} from './auth-test-utils';

// Mock dependencies
jest.mock('@/auth/service');
jest.mock('jwt-decode');
jest.mock('@/lib/logger');
jest.mock('@/store/authStore');
jest.mock('@/lib/auth-service-config');

// Token refresh constants
const REFRESH_THRESHOLD_MS = 5 * 60 * 1000; // Refresh 5 minutes before expiry
const REFRESH_RETRY_DELAY_MS = 1000; // 1 second retry delay
const MAX_REFRESH_RETRIES = 3;

describe('Auth Token Refresh During Activity', () => {
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
    
    // Mock Date.now for time-based tests
    realDateNow = Date.now;
    Date.now = jest.fn().mockReturnValue(Date.now());
    
    // Setup auth service client mocks
    const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
    mockAuthServiceClient.refreshToken = jest.fn();
    mockAuthServiceClient.validateToken = jest.fn();
    
    // Setup basic auth config
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

  const createRefreshedToken = () => {
    const newExpiryTime = Date.now() + (30 * 60 * 1000); // 30 minutes
    const refreshedUser = {
      id: 'test-user',
      email: 'test@example.com',
      exp: Math.floor(newExpiryTime / 1000)
    };
    
    return {
      token: 'new-jwt-token-123',
      user: refreshedUser,
      expiryTime: newExpiryTime
    };
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

  describe('Automatic Token Refresh', () => {
    it('should refresh token before expiry threshold', async () => {
      jest.useFakeTimers();
      createExpiringToken(6); // 6 minutes until expiry
      
      const refreshedData = createRefreshedToken();
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockResolvedValue({
        access_token: refreshedData.token,
        expires_in: 1800
      });

      await act(async () => {
        renderWithTokenRefresh();
      });

      // Advance to refresh threshold
      await act(async () => {
        advanceTimeBy(2 * 60 * 1000); // 2 minutes - should trigger refresh
      });

      await waitFor(() => {
        expect(mockAuthServiceClient.refreshToken).toHaveBeenCalled();
        expect(mocks.localStorageMock.setItem).toHaveBeenCalledWith(
          'jwt_token',
          refreshedData.token
        );
      });
    });

    it('should update auth store with refreshed token', async () => {
      jest.useFakeTimers();
      createExpiringToken(4); // 4 minutes until expiry
      
      const refreshedData = createRefreshedToken();
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockResolvedValue({
        access_token: refreshedData.token,
        expires_in: 1800
      });

      await act(async () => {
        renderWithTokenRefresh();
        advanceTimeBy(1000); // Trigger refresh check
      });

      await waitFor(() => {
        expect(mockAuthStore.updateToken).toHaveBeenCalledWith(refreshedData.token);
      });
    });

    it('should refresh token on user activity near expiry', async () => {
      jest.useFakeTimers();
      createExpiringToken(3); // 3 minutes until expiry
      
      const refreshedData = createRefreshedToken();
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockResolvedValue({
        access_token: refreshedData.token,
        expires_in: 1800
      });

      await act(async () => {
        renderWithTokenRefresh();
      });

      // User activity should trigger refresh
      await act(async () => {
        const appContent = screen.getByTestId('app-content');
        await userEvent.click(appContent);
      });

      await waitFor(() => {
        expect(mockAuthServiceClient.refreshToken).toHaveBeenCalled();
      });
    });

    it('should not refresh if token has sufficient time remaining', async () => {
      jest.useFakeTimers();
      createExpiringToken(10); // 10 minutes until expiry - no refresh needed
      
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;

      await act(async () => {
        renderWithTokenRefresh();
        advanceTimeBy(1000);
      });

      await waitFor(() => {
        expect(mockAuthServiceClient.refreshToken).not.toHaveBeenCalled();
      });
    });
  });

  describe('Token Refresh on API Calls', () => {
    it('should refresh token before making authenticated API calls', async () => {
      createExpiringToken(4); // 4 minutes until expiry
      
      const refreshedData = createRefreshedToken();
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockResolvedValue({
        access_token: refreshedData.token,
        expires_in: 1800
      });

      // Mock API call that requires auth
      mocks.fetchMock.mockResolvedValue(createSuccessResponse({ data: 'test' }));
      
      await act(async () => {
        renderWithTokenRefresh();
      });

      // Simulate authenticated API call
      await act(async () => {
        await fetch('/api/protected', {
          headers: authService.getAuthHeaders()
        });
      });

      await waitFor(() => {
        expect(mockAuthServiceClient.refreshToken).toHaveBeenCalled();
      });
    });

    it('should retry API call with refreshed token', async () => {
      createExpiringToken(2); // 2 minutes until expiry
      
      const refreshedData = createRefreshedToken();
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockResolvedValue({
        access_token: refreshedData.token,
        expires_in: 1800
      });

      // First call fails with 401, second succeeds
      mocks.fetchMock
        .mockResolvedValueOnce(createErrorResponse(401, 'Unauthorized'))
        .mockResolvedValueOnce(createSuccessResponse({ data: 'success' }));

      await act(async () => {
        renderWithTokenRefresh();
      });

      // Should retry with new token
      await waitFor(() => {
        expect(mocks.fetchMock).toHaveBeenCalledTimes(2);
        expect(mockAuthServiceClient.refreshToken).toHaveBeenCalled();
      });
    });

    it('should handle 401 responses by triggering token refresh', async () => {
      createExpiringToken(10); // Valid token but server rejects
      
      const refreshedData = createRefreshedToken();
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockResolvedValue({
        access_token: refreshedData.token,
        expires_in: 1800
      });

      mocks.fetchMock.mockResolvedValue(createErrorResponse(401, 'Token expired'));

      await act(async () => {
        renderWithTokenRefresh();
        // Simulate API call that returns 401
        await fetch('/api/test');
      });

      await waitFor(() => {
        expect(mockAuthServiceClient.refreshToken).toHaveBeenCalled();
      });
    });

    it('should prevent multiple concurrent refresh attempts', async () => {
      createExpiringToken(3); // 3 minutes until expiry
      
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockImplementation(() => 
        new Promise(resolve => setTimeout(resolve, 1000))
      );

      await act(async () => {
        renderWithTokenRefresh();
      });

      // Trigger multiple refresh attempts
      await act(async () => {
        Promise.all([
          fetch('/api/test1'),
          fetch('/api/test2'),
          fetch('/api/test3')
        ]);
      });

      await waitFor(() => {
        // Should only call refresh once despite multiple triggers
        expect(mockAuthServiceClient.refreshToken).toHaveBeenCalledTimes(1);
      });
    });
  });

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
      });

      // Should retry with backoff
      await act(async () => {
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
    it('should store refresh token securely', async () => {
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

    it('should use stored refresh token for renewal', async () => {
      createExpiringToken(3); // 3 minutes until expiry
      mocks.localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'refresh_token') return 'stored-refresh-token';
        if (key === 'jwt_token') return createMockToken();
        return null;
      });
      
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockResolvedValue({
        access_token: 'renewed-token',
        expires_in: 1800
      });

      await act(async () => {
        renderWithTokenRefresh();
        advanceTimeBy(1000);
      });

      await waitFor(() => {
        expect(mockAuthServiceClient.refreshToken).toHaveBeenCalledWith(
          'stored-refresh-token'
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

    it('should validate refresh token on app startup', async () => {
      mocks.localStorageMock.getItem.mockImplementation((key) => {
        if (key === 'refresh_token') return 'startup-refresh-token';
        if (key === 'jwt_token') return null; // No access token
        return null;
      });
      
      const mockAuthServiceClient = require('@/lib/auth-service-config').authService;
      mockAuthServiceClient.refreshToken.mockResolvedValue({
        access_token: 'startup-access-token',
        expires_in: 1800
      });

      await act(async () => {
        renderWithTokenRefresh();
      });

      await waitFor(() => {
        expect(mockAuthServiceClient.refreshToken).toHaveBeenCalledWith(
          'startup-refresh-token'
        );
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
        // Multiple rapid refresh triggers
        for (let i = 0; i < 5; i++) {
          advanceTimeBy(100);
        }
      });

      await waitFor(() => {
        // Should deduplicate refresh attempts
        expect(refreshCount).toBeLessThanOrEqual(2);
      });
    });

    it('should handle high-frequency token validation efficiently', async () => {
      createExpiringToken(10); // 10 minutes - no refresh needed
      
      const startTime = performance.now();
      
      await act(async () => {
        renderWithTokenRefresh();
        // Simulate frequent validation checks
        for (let i = 0; i < 50; i++) {
          authService.getAuthHeaders();
        }
      });

      const endTime = performance.now();
      expect(endTime - startTime).toBeLessThan(50);
    });
  });
});