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
  setupAuthServiceMethods,
  renderAuthHook,
  mockAuthConfig
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

describe('AuthContext - Auth Operations', () => {
  let mockAuthStore: any;

  beforeEach(() => {
    mockAuthStore = setupAuthStore();
    setupBasicMocks();
  });

  const waitForAuthConfig = async (result: any) => {
    await waitFor(() => {
      expect(result.current).toBeDefined();
      expect(result.current?.authConfig).toEqual(expect.objectContaining({
        development_mode: expect.any(Boolean),
        google_client_id: mockAuthConfig.google_client_id,
        endpoints: mockAuthConfig.endpoints,
        authorized_javascript_origins: mockAuthConfig.authorized_javascript_origins,
        authorized_redirect_uris: mockAuthConfig.authorized_redirect_uris
      }));
      expect(result.current?.loading).toBe(false);
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
    
    // Ensure auth config is properly set before calling login
    expect(result.current?.authConfig).toBeTruthy();
    
    performLogin(result);
    
    // Wait for the login action to complete
    await waitFor(() => {
      expect(authService.clearDevLogoutFlag).toHaveBeenCalled();
    });
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
    
    // Ensure auth config is properly set before calling logout  
    expect(result.current?.authConfig).toBeTruthy();
    
    await performLogout(result);
    
    // Wait for logout methods to be called
    await waitFor(() => {
      expect(authService.handleLogout).toHaveBeenCalledWith(mockAuthConfig);
    });
    await waitFor(() => {
      expect(mockAuthStore.logout).toHaveBeenCalled();
    });
  });

  it('should set dev logout flag in development mode', async () => {
    // Override the auth config to be in development mode
    const devConfig = { ...mockAuthConfig, development_mode: true };
    jest.mocked(authService.getAuthConfig).mockResolvedValue(devConfig);
    
    const { result } = renderAuthHook();
    
    // Wait for the context to load with dev config
    await waitFor(() => {
      expect(result.current).toBeDefined();
      expect(result.current?.authConfig?.development_mode).toBe(true);
    });
    
    // Perform logout
    await performLogout(result);
    
    // Check dev logout flag was set
    expect(authService.setDevLogoutFlag).toHaveBeenCalled();
    expect(authService.handleLogout).toHaveBeenCalledWith(
      expect.objectContaining({ development_mode: true })
    );
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