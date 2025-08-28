/**
 * Authentication Test Helpers
 * 
 * Provides utilities for easily mocking authentication state in tests.
 * This module allows tests to override the default authenticated state
 * and test various authentication scenarios.
 */

import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { AuthProvider } from '@/auth/context';
import { GTMProvider } from '@/providers/GTMProvider';
import { WebSocketProvider } from '@/providers/WebSocketProvider';

// Default mock user for tests
export const mockTestUser = {
  id: 'test-user',
  email: 'test@example.com',
  full_name: 'Test User'
};

// Default mock JWT token (expires far in the future)
export const mockTestToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.test-signature';

// Default auth configuration for tests
export const mockAuthConfig = {
  development_mode: true,
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

// Authentication state options for tests
export interface AuthTestState {
  user?: any | null;
  loading?: boolean;
  error?: Error | null;
  authConfig?: any | null;
  token?: string | null;
  isAuthenticated?: boolean;
  initialized?: boolean;
}

/**
 * Set the global mock authentication state for tests
 * This function allows tests to override the default authenticated state
 */
export function setMockAuthState(state: AuthTestState): void {
  global.mockAuthState = {
    user: mockTestUser,
    loading: false,
    error: null,
    authConfig: mockAuthConfig,
    token: mockTestToken,
    isAuthenticated: true,
    initialized: true,
    ...state
  };

  // Also update localStorage to match
  if (state.token !== undefined) {
    if (state.token && global.localStorage) {
      global.localStorage.setItem('jwt_token', state.token);
      global.localStorage.setItem('token', state.token);
      global.localStorage.setItem('auth_token', state.token);
    } else if (global.localStorage) {
      global.localStorage.removeItem('jwt_token');
      global.localStorage.removeItem('token');
      global.localStorage.removeItem('auth_token');
    }
  }
}

/**
 * Reset authentication state to default authenticated state
 */
export function resetMockAuthState(): void {
  setMockAuthState({
    user: mockTestUser,
    loading: false,
    error: null,
    authConfig: mockAuthConfig,
    token: mockTestToken,
    isAuthenticated: true,
    initialized: true
  });
}

/**
 * Set authentication state to unauthenticated
 */
export function setUnauthenticatedState(): void {
  setMockAuthState({
    user: null,
    loading: false,
    error: null,
    authConfig: mockAuthConfig,
    token: null,
    isAuthenticated: false,
    initialized: true
  });
}

/**
 * Set authentication state to loading
 */
export function setLoadingAuthState(): void {
  setMockAuthState({
    user: null,
    loading: true,
    error: null,
    authConfig: null,
    token: null,
    isAuthenticated: false,
    initialized: false
  });
}

/**
 * Set authentication state to error
 */
export function setAuthErrorState(error: Error = new Error('Authentication failed')): void {
  setMockAuthState({
    user: null,
    loading: false,
    error,
    authConfig: mockAuthConfig,
    token: null,
    isAuthenticated: false,
    initialized: true
  });
}

/**
 * Comprehensive test wrapper that includes all necessary providers
 * This wrapper includes GTMProvider to prevent "useGTMContext must be used within a GTMProvider" errors
 */
export function renderWithProviders(
  ui: React.ReactElement,
  {
    authState,
    ...renderOptions
  }: {
    authState?: AuthTestState;
  } & Omit<RenderOptions, 'wrapper'> = {}
) {
  // Set auth state before rendering if provided
  if (authState) {
    setMockAuthState(authState);
  }

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <GTMProvider>
        <WebSocketProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
        </WebSocketProvider>
      </GTMProvider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}

/**
 * Simple auth wrapper without other providers
 * Use this when you only need auth context
 */
export function renderWithAuth(
  ui: React.ReactElement,
  {
    authState,
    ...renderOptions
  }: {
    authState?: AuthTestState;
  } & Omit<RenderOptions, 'wrapper'> = {}
) {
  if (authState) {
    setMockAuthState(authState);
  }

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <GTMProvider>
        <AuthProvider>
          {children}
        </AuthProvider>
      </GTMProvider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}

/**
 * Helper to simulate login action in tests
 */
export function simulateLogin(user = mockTestUser, token = mockTestToken): void {
  setMockAuthState({
    user,
    token,
    isAuthenticated: true,
    loading: false,
    initialized: true
  });
}

/**
 * Helper to simulate logout action in tests
 */
export function simulateLogout(): void {
  setUnauthenticatedState();
}

// Export commonly used auth states for convenience
export const authStates = {
  authenticated: {
    user: mockTestUser,
    loading: false,
    error: null,
    authConfig: mockAuthConfig,
    token: mockTestToken,
    isAuthenticated: true,
    initialized: true
  },
  unauthenticated: {
    user: null,
    loading: false,
    error: null,
    authConfig: mockAuthConfig,
    token: null,
    isAuthenticated: false,
    initialized: true
  },
  loading: {
    user: null,
    loading: true,
    error: null,
    authConfig: null,
    token: null,
    isAuthenticated: false,
    initialized: false
  },
  error: {
    user: null,
    loading: false,
    error: new Error('Authentication failed'),
    authConfig: mockAuthConfig,
    token: null,
    isAuthenticated: false,
    initialized: true
  }
};