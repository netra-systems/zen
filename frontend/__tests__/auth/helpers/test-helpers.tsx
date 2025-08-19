/**
 * Shared test helpers for auth context tests
 * Each helper function ≤8 lines per architecture requirements
 * Updated for auth service independence
 */

import React from 'react';
import { renderHook } from '@testing-library/react';
import { AuthProvider, AuthContext } from '@/auth/context';
import { authService } from '@/auth/service';
import { jwtDecode } from 'jwt-decode';
import { useAuthStore } from '@/store/authStore';
import { logger } from '@/lib/logger';
import { mockAuthServiceResponses } from '@/__tests__/mocks/auth-service-mock';

// Mock data - uses independent auth service endpoints
export const mockAuthConfig = {
  development_mode: false,
  google_client_id: 'mock-google-client-id',
  endpoints: {
    login: 'http://localhost:8081/auth/login',
    logout: 'http://localhost:8081/auth/logout',
    callback: 'http://localhost:8081/auth/callback',
    token: 'http://localhost:8081/auth/token',
    user: 'http://localhost:8081/auth/me',
    dev_login: 'http://localhost:8081/auth/dev/login'
  },
  authorized_javascript_origins: ['http://localhost:3000'],
  authorized_redirect_uris: ['http://localhost:3000/auth/callback']
};

export const mockUser = {
  id: 'user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  sub: 'user-123',
  name: 'Test User',
  role: 'admin'
};

export const mockToken = 'mock-jwt-token-123';

// Setup functions (≤8 lines each)
export const setupBasicMocks = () => {
  jest.clearAllMocks();
  (authService.getAuthConfig as jest.Mock).mockResolvedValue(mockAuthConfig);
  (authService.getToken as jest.Mock).mockReturnValue(null);
  (authService.getDevLogoutFlag as jest.Mock).mockReturnValue(false);
  setupAuthServiceMethods();
  setupAuthServiceClientMocks();
  (jwtDecode as jest.Mock).mockReturnValue(mockUser);
};

export const setupAuthServiceMethods = () => {
  (authService.handleLogin as jest.Mock).mockImplementation(() => {});
  (authService.handleLogout as jest.Mock).mockImplementation(() => Promise.resolve());
  (authService.setDevLogoutFlag as jest.Mock).mockImplementation(() => {});
  (authService.clearDevLogoutFlag as jest.Mock).mockImplementation(() => {});
  (authService.removeToken as jest.Mock).mockImplementation(() => {});
  (authService.handleDevLogin as jest.Mock).mockResolvedValue(mockAuthServiceResponses.devLogin);
  (authService.getAuthHeaders as jest.Mock).mockReturnValue({});
};

export const setupAuthServiceClientMocks = () => {
  // Mock auth service client for independent service communication
  const authServiceClient = require('@/lib/auth-service-config').authService;
  if (authServiceClient) {
    authServiceClient.getConfig = jest.fn().mockResolvedValue(mockAuthServiceResponses.config);
    authServiceClient.getSession = jest.fn().mockResolvedValue(mockAuthServiceResponses.session);
    authServiceClient.getCurrentUser = jest.fn().mockResolvedValue(mockAuthServiceResponses.user);
  }
};

export const setupAuthStore = () => {
  const mockAuthStore = {
    login: jest.fn(),
    logout: jest.fn(),
    user: null,
    token: null,
    isAuthenticated: false
  };
  (useAuthStore as jest.Mock).mockReturnValue(mockAuthStore);
  return mockAuthStore;
};

export const setupTokenMocks = (token: string = mockToken) => {
  (authService.getToken as jest.Mock).mockReturnValue(token);
  (jwtDecode as jest.Mock).mockReturnValue(mockUser);
};

export const setupDevModeMocks = (isDevMode: boolean = true) => {
  const devConfig = { ...mockAuthConfig, development_mode: isDevMode };
  (authService.getAuthConfig as jest.Mock).mockResolvedValue(devConfig);
  return devConfig;
};

export const setupAuthConfigError = () => {
  (authService.getAuthConfig as jest.Mock).mockRejectedValue(new Error('Network error'));
};

// Wrapper components (≤8 lines each)
export const createAuthWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  );
};

export const createContextHook = () => {
  return () => {
    const context = React.useContext(AuthContext);
    return context;
  };
};

// Test execution helpers (≤8 lines each)
export const renderWithAuthProvider = (ui: React.ReactElement) => {
  const wrapper = createAuthWrapper();
  return { wrapper };
};

export const renderAuthHook = () => {
  const wrapper = createAuthWrapper();
  const hook = createContextHook();
  return renderHook(hook, { wrapper });
};

// Assertion helpers (≤8 lines each)
export const expectAuthStoreLogin = (mockStore: any, user = mockUser, token = mockToken) => {
  expect(mockStore.login).toHaveBeenCalledWith(
    expect.objectContaining({
      id: user.id || user.sub || '',
      email: user.email,
      full_name: user.full_name || user.name,
      role: user.role
    }),
    token
  );
};

export const expectContextValues = (result: any, expectedValues: any) => {
  expect(result.current).toMatchObject(expectedValues);
};