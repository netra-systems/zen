/**
 * Auth Token Refresh Automatic Tests
 * Tests automatic token refresh and API call refresh scenarios
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

describe('Auth Token Refresh Automatic', () => {
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
    mockAuthServiceClient.validateToken = jest.fn();
    
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

      mocks.fetchMock.mockResolvedValue(createSuccessResponse({ data: 'test' }));
      
      await act(async () => {
        renderWithTokenRefresh();
      });

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

      mocks.fetchMock
        .mockResolvedValueOnce(createErrorResponse(401, 'Unauthorized'))
        .mockResolvedValueOnce(createSuccessResponse({ data: 'success' }));

      await act(async () => {
        renderWithTokenRefresh();
      });

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
        Promise.all([
          fetch('/api/test1'),
          fetch('/api/test2'),
          fetch('/api/test3')
        ]);
      });

      await waitFor(() => {
        expect(mockAuthServiceClient.refreshToken).toHaveBeenCalledTimes(1);
      });
    });
  });
});