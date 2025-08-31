/**
 * AuthContext Auth Operations Tests  
 * Tests login and logout functionality
 * All functions ≤8 lines per architecture requirements
 */
// Unmock auth service for proper service functionality
jest.unmock('@/auth/service');


import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import React from 'react';
import { waitFor, act } from '@testing-library/react';
import { authService } from '@/auth/unified-auth-service';
import '@testing-library/jest-dom';
import { setupBasicMocks,
  setupAuthStore,
  setupAuthConfigError,
  setupDevModeMocks,
  setupAuthServiceMethods,
  renderAuthHook,
  mockAuthConfig
} from './helpers/test-helpers';

// Mock the entire auth module to ensure the context gets the mocked version
jest.mock('@/auth/service', () => ({
  authService: {
    getAuthConfig: jest.fn(),
    handleLogin: jest.fn(),
    handleLogout: jest.fn(),
    clearDevLogoutFlag: jest.fn(),
    setDevLogoutFlag: jest.fn(),
    getToken: jest.fn(),
    getDevLogoutFlag: jest.fn(),
    removeToken: jest.fn(),
    handleDevLogin: jest.fn(),
    getAuthHeaders: jest.fn(),
    useAuth: jest.fn(),
  }
}));

jest.mock('@/auth', () => ({
  ...jest.requireActual('@/auth'),
  authService: {
    getAuthConfig: jest.fn(),
    handleLogin: jest.fn(),
    handleLogout: jest.fn(),
    clearDevLogoutFlag: jest.fn(),
    setDevLogoutFlag: jest.fn(),
    getToken: jest.fn(),
    getDevLogoutFlag: jest.fn(),
    removeToken: jest.fn(),
    handleDevLogin: jest.fn(),
    getAuthHeaders: jest.fn(),
    useAuth: jest.fn(),
  }
}));

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
  setupAntiHang();
    jest.setTimeout(10000);
  let mockAuthStore: any;
  let mockAuthService: any;

  beforeEach(() => {
    mockAuthStore = setupAuthStore();
    
    // Get the mocked authService instance
    mockAuthService = require('@/auth/service').authService;
    
    // Setup the mock implementations directly
    mockAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
    mockAuthService.getToken.mockReturnValue(null);
    mockAuthService.getDevLogoutFlag.mockReturnValue(false);
    mockAuthService.handleLogin.mockImplementation(() => {});
    mockAuthService.handleLogout.mockImplementation(() => Promise.resolve());
    mockAuthService.setDevLogoutFlag.mockImplementation(() => {});
    mockAuthService.clearDevLogoutFlag.mockImplementation(() => {});
    mockAuthService.removeToken.mockImplementation(() => {});
    mockAuthService.handleDevLogin.mockResolvedValue({ access_token: 'dev-token', token_type: 'Bearer' });
    mockAuthService.getAuthHeaders.mockReturnValue({});
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
      console.log('Calling login, authConfig at call time:', result.current?.authConfig);
      result.current?.login();
    });
  };

  it('should handle login action', async () => {
    const { result } = renderAuthHook();
    await waitForAuthConfig(result);
    
    // Debug: Check what the context actually has
    console.log('Auth config from context:', result.current?.authConfig);
    console.log('Login function type:', typeof result.current?.login);
    
    // Ensure auth config is properly set before calling login
    expect(result.current?.authConfig).toBeTruthy();
    
    // Spy on the actual login function to ensure it's called
    const loginSpy = jest.spyOn(result.current, 'login');
    
    performLogin(result);
    
    // Verify the login function was actually called
    expect(loginSpy).toHaveBeenCalled();
    
    // Wait for the login action to complete
    await waitFor(() => {
      expect(mockAuthService.clearDevLogoutFlag).toHaveBeenCalled();
    });
    expect(mockAuthService.handleLogin).toHaveBeenCalledWith(mockAuthConfig);
  });

  const setupLoginWithError = () => {
    mockAuthService.getAuthConfig.mockRejectedValue(new Error('Network error'));
    return renderAuthHook();
  };

  const expectNoLogin = () => {
    expect(mockAuthService.handleLogin).not.toHaveBeenCalled();
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
      expect(mockAuthService.handleLogout).toHaveBeenCalledWith(mockAuthConfig);
    });
    await waitFor(() => {
      expect(mockAuthStore.logout).toHaveBeenCalled();
    });
  });

  it('should set dev logout flag in development mode', async () => {
    // Override the auth config to be in development mode
    const devConfig = { ...mockAuthConfig, development_mode: true };
    mockAuthService.getAuthConfig.mockResolvedValue(devConfig);
    
    const { result } = renderAuthHook();
    
    // Wait for the context to load with dev config
    await waitFor(() => {
      expect(result.current).toBeDefined();
      expect(result.current?.authConfig?.development_mode).toBe(true);
      expect(result.current?.loading).toBe(false);
    });
    
    // Perform logout
    await performLogout(result);
    
    // Wait for dev logout flag and logout methods to be called
    await waitFor(() => {
      expect(mockAuthService.setDevLogoutFlag).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(mockAuthService.handleLogout).toHaveBeenCalledWith(
        expect.objectContaining({ development_mode: true })
      );
    });
  });

  const setupLogoutWithError = () => {
    mockAuthService.getAuthConfig.mockRejectedValue(new Error('Network error'));
    return renderAuthHook();
  };

  const expectNoLogout = () => {
    expect(mockAuthService.handleLogout).not.toHaveBeenCalled();
  };

  it('should not logout when auth config is not available', async () => {
    const { result } = setupLogoutWithError();
    await waitFor(() => {
      expect(result.current).toBeDefined();
    });
    await performLogout(result);
    expectNoLogout();
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});