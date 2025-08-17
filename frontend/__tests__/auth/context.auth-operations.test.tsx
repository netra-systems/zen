/**
 * AuthContext Auth Operations Tests  
 * Tests login and logout functionality
 * All functions ≤8 lines per architecture requirements
 */

import React from 'react';
import { waitFor, act } from '@testing-library/react';
import { authService } from '@/auth/service';
import '@testing-library/jest-dom';
import {
  setupBasicMocks,
  setupAuthStore,
  setupAuthConfigError,
  setupDevModeMocks,
  renderAuthHook,
  mockAuthConfig
} from './helpers/test-helpers';

// Mock dependencies
jest.mock('@/auth/service');
jest.mock('jwt-decode');
jest.mock('@/store/authStore');

describe('AuthContext - Auth Operations', () => {
  let mockAuthStore: any;

  beforeEach(() => {
    mockAuthStore = setupAuthStore();
    setupBasicMocks();
  });

  const waitForAuthConfig = async (result: any) => {
    await waitFor(() => {
      expect(result.current).toBeDefined();
      expect(result.current?.authConfig).toEqual(mockAuthConfig);
    });
  };

  const performLogin = (result: any) => {
    act(() => {
      result.current?.login();
    });
  };

  it('should handle login action', async () => {
    const { result } = renderAuthHook();
    await waitForAuthConfig(result);
    performLogin(result);
    expect(authService.clearDevLogoutFlag).toHaveBeenCalled();
    expect(authService.handleLogin).toHaveBeenCalledWith(mockAuthConfig);
  });

  const setupLoginWithError = () => {
    setupAuthConfigError();
    return renderAuthHook();
  };

  const expectNoLogin = () => {
    expect(authService.handleLogin).not.toHaveBeenCalled();
  };

  it('should not login when auth config is not available', async () => {
    const { result } = setupLoginWithError();
    await waitFor(() => {
      expect(result.current).toBeDefined();
    });
    performLogin(result);
    expectNoLogin();
  });

  const performLogout = async (result: any) => {
    await act(async () => {
      await result.current?.logout();
    });
  };

  const expectLogoutBehavior = async () => {
    expect(authService.handleLogout).toHaveBeenCalledWith(mockAuthConfig);
    await waitFor(() => {
      expect(mockAuthStore.logout).toHaveBeenCalled();
    });
  };

  it('should handle logout action', async () => {
    const { result } = renderAuthHook();
    await waitForAuthConfig(result);
    await performLogout(result);
    await expectLogoutBehavior();
  });

  const setupDevModeLogout = () => {
    const devConfig = setupDevModeMocks(true);
    (authService.getDevLogoutFlag as jest.Mock).mockReturnValue(false);
    return { devConfig, result: renderAuthHook() };
  };

  const expectDevLogoutFlag = () => {
    expect(authService.setDevLogoutFlag).toHaveBeenCalled();
  };

  it('should set dev logout flag in development mode', async () => {
    const { devConfig, result } = setupDevModeLogout();
    await waitFor(() => {
      expect(result.current?.authConfig).toEqual(devConfig);
    });
    await performLogout(result);
    expectDevLogoutFlag();
    expect(authService.handleLogout).toHaveBeenCalledWith(devConfig);
  });

  const setupLogoutWithError = () => {
    setupAuthConfigError();
    return renderAuthHook();
  };

  const expectNoLogout = () => {
    expect(authService.handleLogout).not.toHaveBeenCalled();
  };

  it('should not logout when auth config is not available', async () => {
    const { result } = setupLogoutWithError();
    await waitFor(() => {
      expect(result.current).toBeDefined();
    });
    await performLogout(result);
    expectNoLogout();
  });
});