/**
 * @fileoverview Tests for AuthContext initialization state tracking
 * 
 * Tests that the AuthContext properly tracks initialization state to prevent
 * AuthGuard race conditions where users are redirected before auth state loads.
 */

import React from 'react';
import { render, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/auth/context';

// Mock the unified auth service
jest.mock('@/auth/unified-auth-service', () => ({
  unifiedAuthService: {
    getAuthConfig: jest.fn(),
    getToken: jest.fn(),
    getDevLogoutFlag: jest.fn(),
    needsRefresh: jest.fn(),
    getEnvironment: jest.fn(() => 'development'),
  },
}));

// Mock the auth store
jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));

// Mock the GTM hook
jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: () => ({
    trackLogin: jest.fn(),
    trackLogout: jest.fn(),
    trackOAuthComplete: jest.fn(),
    trackError: jest.fn(),
  }),
}));

// Mock jwt-decode
jest.mock('jwt-decode', () => ({
  jwtDecode: jest.fn(() => ({
    sub: 'test-user',
    email: 'test@example.com',
    exp: Math.floor(Date.now() / 1000) + 3600, // expires in 1 hour
  })),
}));

// Test component to access auth state
const TestComponent = () => {
  const { loading, initialized, user, token } = useAuth();
  return (
    <div data-testid="auth-state">
      <span data-testid="loading">{loading.toString()}</span>
      <span data-testid="initialized">{initialized.toString()}</span>
      <span data-testid="user">{user ? 'authenticated' : 'not-authenticated'}</span>
      <span data-testid="token">{token ? 'has-token' : 'no-token'}</span>
    </div>
  );
};

describe('AuthContext Initialization', () => {
  beforeEach(() => {
    // Clear localStorage
    localStorage.clear();
    jest.clearAllMocks();
  });

  test('should include initialized field in context', async () => {
    const { getByTestId } = render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Should have the initialized field
    expect(getByTestId('initialized')).toBeInTheDocument();
  });
});