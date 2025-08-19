/**
 * AuthContext Development Mode Tests
 * Tests development-specific authentication features
 * All functions ≤8 lines per architecture requirements
 */

import React from 'react';
import { render, waitFor } from '@testing-library/react';
import { AuthProvider } from '@/auth/context';
import { authService } from '@/auth/service';
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

// Mock dependencies
jest.mock('@/auth/service');
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

describe('AuthContext - Development Mode', () => {
  let mockAuthStore: any;

  beforeEach(() => {
    mockAuthStore = setupAuthStore();
    setupBasicMocks();
  });

  const renderDevProvider = () => {
    return render(
      <AuthProvider>
        <div>Test Content</div>
      </AuthProvider>
    );
  };

  const setupAutoLogin = (devConfig: any) => {
    (authService.getDevLogoutFlag as jest.Mock).mockReturnValue(false);
    (authService.handleDevLogin as jest.Mock).mockResolvedValue({
      access_token: mockToken,
      token_type: 'Bearer'
    });
    return devConfig;
  };

  const expectDevLogin = async (devConfig: any) => {
    await waitFor(() => {
      expect(authService.handleDevLogin).toHaveBeenCalledWith(devConfig);
    }, { timeout: 3000 });
  };

  const expectAuthStoreUpdate = async () => {
    await waitFor(() => {
      expect(jwtDecode).toHaveBeenCalledWith(mockToken);
      expect(mockAuthStore.login).toHaveBeenCalled();
    });
  };

  it('should auto-login in development mode when not logged out', async () => {
    const devConfig = setupDevModeMocks(true);
    setupAutoLogin(devConfig);
    renderDevProvider();
    await expectDevLogin(devConfig);
    await expectAuthStoreUpdate();
  });

  const setupSkipAutoLogin = () => {
    const devConfig = setupDevModeMocks(true);
    (authService.getDevLogoutFlag as jest.Mock).mockReturnValue(true);
    return devConfig;
  };

  const expectSkipMessage = async () => {
    await waitFor(() => {
      expect(logger.info).toHaveBeenCalledWith(
        'Skipping auto dev login - user has logged out',
        {
          component: 'AuthContext',
          action: 'auto_dev_login_skipped'
        }
      );
      expect(authService.handleDevLogin).not.toHaveBeenCalled();
    });
  };

  it('should skip auto-login if user has logged out in dev mode', async () => {
    setupSkipAutoLogin();
    renderDevProvider();
    await expectSkipMessage();
  });

  const setupDevLoginFailure = () => {
    const devConfig = setupDevModeMocks(true);
    (authService.handleDevLogin as jest.Mock).mockResolvedValue(null);
    return devConfig;
  };

  const expectNoAuthUpdate = async () => {
    await waitFor(() => {
      expect(authService.handleDevLogin).toHaveBeenCalled();
      expect(jwtDecode).not.toHaveBeenCalled();
      expect(mockAuthStore.login).not.toHaveBeenCalled();
    });
  };

  it('should handle dev login failure gracefully', async () => {
    setupDevLoginFailure();
    renderDevProvider();
    await expectNoAuthUpdate();
  });
});