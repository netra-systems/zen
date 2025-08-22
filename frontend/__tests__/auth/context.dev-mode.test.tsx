/**
 * AuthContext Development Mode Tests
 * Tests development-specific authentication features
 * All functions ≤8 lines per architecture requirements
 */

import React from 'react';
import { render, waitFor } from '@testing-library/react';
import { jwtDecode } from 'jwt-decode';
import { logger } from '@/lib/logger';
import '@testing-library/jest-dom';
import {
  setupBasicMocks,
  setupAuthStore,
  setupDevModeMocks,
  expectAuthStoreLogin,
  mockToken,
  mockUser
} from './helpers/test-helpers';

// Unmock the real AuthProvider and authService for dev mode tests
jest.unmock('@/auth/context');
jest.unmock('@/auth/service');

// Import real components after unmocking
const { AuthProvider } = require('@/auth/context');
const { authService } = require('@/auth/service');

// Mock dependencies but keep AuthProvider real
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

// Mock the auth service config to work with real authService
jest.mock('@/lib/auth-service-config', () => ({
  authService: {
    getConfig: jest.fn(),
    initiateLogin: jest.fn(),
    logout: jest.fn()
  },
  getAuthServiceConfig: jest.fn()
}));

describe('AuthContext - Development Mode', () => {
  let mockAuthStore: any;
  const mockAuthServiceClient = {
    getConfig: jest.fn(),
    initiateLogin: jest.fn(),
    logout: jest.fn()
  };

  beforeEach(() => {
    // Set NODE_ENV to development for these tests
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';
    
    // Clear all existing mocks
    jest.clearAllMocks();
    
    // Setup auth store
    mockAuthStore = setupAuthStore();
    
    // Setup auth service client mock
    const authServiceConfig = require('@/lib/auth-service-config');
    authServiceConfig.authService.getConfig.mockResolvedValue({
      development_mode: true,
      google_client_id: 'mock-google-client-id',
      endpoints: {
        login: 'http://localhost:8081/auth/login',
        logout: 'http://localhost:8081/auth/logout',
        callback: 'http://localhost:8081/auth/callback',
        token: 'http://localhost:8081/auth/token',
        user: 'http://localhost:8081/auth/me',
        dev_login: 'http://localhost:8081/auth/dev/login'
      }
    });
    
    authServiceConfig.getAuthServiceConfig.mockReturnValue({
      endpoints: {
        login: 'http://localhost:8081/auth/login',
        logout: 'http://localhost:8081/auth/logout',
        callback: 'http://localhost:8081/auth/callback',
        token: 'http://localhost:8081/auth/token',
        me: 'http://localhost:8081/auth/me'
      },
      oauth: {
        javascriptOrigins: ['http://localhost:3000'],
        redirectUri: 'http://localhost:3000/auth/callback'
      }
    });
    
    // Setup jwtDecode mock
    (jwtDecode as jest.Mock).mockReturnValue(mockUser);
    
    // Spy on the real authService methods
    jest.spyOn(authService, 'getToken').mockReturnValue(null);
    jest.spyOn(authService, 'getDevLogoutFlag').mockReturnValue(false);
    jest.spyOn(authService, 'handleDevLogin').mockResolvedValue({
      access_token: mockToken,
      token_type: 'Bearer'
    });
    jest.spyOn(authService, 'removeToken').mockImplementation(() => {});
    jest.spyOn(authService, 'setDevLogoutFlag').mockImplementation(() => {});
    jest.spyOn(authService, 'clearDevLogoutFlag').mockImplementation(() => {});
    
    // Mock fetch for dev login endpoint
    global.fetch = jest.fn().mockImplementation((url) => {
      if (url.includes('/auth/dev/login')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            access_token: mockToken,
            token_type: 'Bearer'
          })
        });
      }
      return Promise.resolve({ ok: false });
    });
  });

  const renderDevProvider = () => {
    return render(
      <AuthProvider>
        <div>Test Content</div>
      </AuthProvider>
    );
  };

  it('should auto-login in development mode when not logged out', async () => {
    // Configure authService for auto-login scenario
    jest.spyOn(authService, 'getDevLogoutFlag').mockReturnValue(false);
    jest.spyOn(authService, 'getToken').mockReturnValue(null); // No existing token
    
    renderDevProvider();
    
    // Wait for the dev login to be called with the expected config
    await waitFor(() => {
      expect(authService.handleDevLogin).toHaveBeenCalledWith(
        expect.objectContaining({
          development_mode: true,
          endpoints: expect.objectContaining({
            dev_login: 'http://localhost:8081/auth/dev/login'
          })
        })
      );
    }, { timeout: 3000 });
    
    // Verify auth store was updated
    await waitFor(() => {
      expect(jwtDecode).toHaveBeenCalledWith(mockToken);
      expect(mockAuthStore.login).toHaveBeenCalled();
    });
  });

  it('should skip auto-login if user has logged out in dev mode', async () => {
    // Configure authService for skip scenario - user has logged out
    jest.spyOn(authService, 'getDevLogoutFlag').mockReturnValue(true);
    jest.spyOn(authService, 'getToken').mockReturnValue(null); // No existing token
    
    renderDevProvider();
    
    // Wait for the skip message to be logged
    await waitFor(() => {
      expect(logger.info).toHaveBeenCalledWith(
        'Skipping auto dev login - user has logged out',
        {
          component: 'AuthContext',
          action: 'auto_dev_login_skipped'
        }
      );
      expect(authService.handleDevLogin).not.toHaveBeenCalled();
    }, { timeout: 3000 });
  });

  it('should handle dev login failure gracefully', async () => {
    // Configure authService for failure scenario
    jest.spyOn(authService, 'getDevLogoutFlag').mockReturnValue(false);
    jest.spyOn(authService, 'getToken').mockReturnValue(null); // No existing token
    jest.spyOn(authService, 'handleDevLogin').mockResolvedValue(null); // Dev login fails
    
    renderDevProvider();
    
    // Wait for dev login to be attempted but fail gracefully
    await waitFor(() => {
      expect(authService.handleDevLogin).toHaveBeenCalled();
      expect(jwtDecode).not.toHaveBeenCalled();
      expect(mockAuthStore.login).not.toHaveBeenCalled();
    }, { timeout: 3000 });
  });
});