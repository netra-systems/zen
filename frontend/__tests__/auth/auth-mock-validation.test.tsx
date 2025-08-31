/**
 * Authentication Mock Validation Tests
 * 
 * Tests to validate that our authentication mocking system works correctly
 * and provides consistent authentication state across different scenarios.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { useAuth } from '@/auth/context';
import {
  renderWithAuth,
  setMockAuthState,
  setUnauthenticatedState,
  setLoadingAuthState,
  resetMockAuthState,
  authStates,
  mockTestUser,
  mockTestToken
} from '@/__tests__/test-utils/auth-test-helpers';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Simple test component to display auth state
const AuthStateDisplay = () => {
  const auth = useAuth();
  
  return (
    <div data-testid="auth-display">
      <div data-testid="user">{auth.user ? auth.user.email : 'no-user'}</div>
      <div data-testid="loading">{auth.loading ? 'loading' : 'loaded'}</div>
      <div data-testid="authenticated">{auth.isAuthenticated ? 'authenticated' : 'not-authenticated'}</div>
      <div data-testid="token">{auth.token || 'no-token'}</div>
      <div data-testid="initialized">{auth.initialized ? 'initialized' : 'not-initialized'}</div>
    </div>
  );
};

describe('Authentication Mock System', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    resetMockAuthState();
  });

  describe('Default authenticated state', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should provide authenticated user by default', () => {
      renderWithAuth(<AuthStateDisplay />);
      
      expect(screen.getByTestId('user')).toHaveTextContent(mockTestUser.email);
      expect(screen.getByTestId('loading')).toHaveTextContent('loaded');
      expect(screen.getByTestId('authenticated')).toHaveTextContent('authenticated');
      expect(screen.getByTestId('token')).toHaveTextContent(mockTestToken);
      expect(screen.getByTestId('initialized')).toHaveTextContent('initialized');
    });
  });

  describe('Unauthenticated state', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should allow setting unauthenticated state', () => {
      setUnauthenticatedState();
      
      renderWithAuth(<AuthStateDisplay />);
      
      expect(screen.getByTestId('user')).toHaveTextContent('no-user');
      expect(screen.getByTestId('loading')).toHaveTextContent('loaded');
      expect(screen.getByTestId('authenticated')).toHaveTextContent('not-authenticated');
      expect(screen.getByTestId('token')).toHaveTextContent('no-token');
      expect(screen.getByTestId('initialized')).toHaveTextContent('initialized');
    });
  });

  describe('Loading state', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should allow setting loading state', () => {
      setLoadingAuthState();
      
      renderWithAuth(<AuthStateDisplay />);
      
      expect(screen.getByTestId('user')).toHaveTextContent('no-user');
      expect(screen.getByTestId('loading')).toHaveTextContent('loading');
      expect(screen.getByTestId('authenticated')).toHaveTextContent('not-authenticated');
      expect(screen.getByTestId('token')).toHaveTextContent('no-token');
      expect(screen.getByTestId('initialized')).toHaveTextContent('not-initialized');
    });
  });

  describe('Custom auth state', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should allow setting custom auth state', () => {
      const customUser = {
        id: 'custom-user',
        email: 'custom@example.com',
        full_name: 'Custom User'
      };
      const customToken = 'custom-token-123';
      
      setMockAuthState({
        user: customUser,
        token: customToken,
        isAuthenticated: true,
        loading: false,
        initialized: true
      });
      
      renderWithAuth(<AuthStateDisplay />);
      
      expect(screen.getByTestId('user')).toHaveTextContent('custom@example.com');
      expect(screen.getByTestId('token')).toHaveTextContent('custom-token-123');
      expect(screen.getByTestId('authenticated')).toHaveTextContent('authenticated');
    });
  });

  describe('Predefined auth states', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should work with authenticated state', () => {
      renderWithAuth(<AuthStateDisplay />, { authState: authStates.authenticated });
      
      expect(screen.getByTestId('authenticated')).toHaveTextContent('authenticated');
      expect(screen.getByTestId('loading')).toHaveTextContent('loaded');
    });

    it('should work with unauthenticated state', () => {
      renderWithAuth(<AuthStateDisplay />, { authState: authStates.unauthenticated });
      
      expect(screen.getByTestId('authenticated')).toHaveTextContent('not-authenticated');
      expect(screen.getByTestId('user')).toHaveTextContent('no-user');
    });

    it('should work with loading state', () => {
      renderWithAuth(<AuthStateDisplay />, { authState: authStates.loading });
      
      expect(screen.getByTestId('loading')).toHaveTextContent('loading');
      expect(screen.getByTestId('initialized')).toHaveTextContent('not-initialized');
    });

    it('should work with error state', () => {
      renderWithAuth(<AuthStateDisplay />, { authState: authStates.error });
      
      expect(screen.getByTestId('authenticated')).toHaveTextContent('not-authenticated');
      expect(screen.getByTestId('loading')).toHaveTextContent('loaded');
    });
  });

  describe('Auth state persistence', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should maintain auth state across multiple renders', () => {
      setMockAuthState({
        user: { id: 'persistent-user', email: 'persist@example.com', full_name: 'Persistent User' },
        isAuthenticated: true,
        token: 'persistent-token',
        loading: false,
        initialized: true
      });
      
      const { rerender } = renderWithAuth(<AuthStateDisplay />);
      
      expect(screen.getByTestId('user')).toHaveTextContent('persist@example.com');
      
      // Rerender the same component
      rerender(<AuthStateDisplay />);
      
      // Should still show the same auth state
      expect(screen.getByTestId('user')).toHaveTextContent('persist@example.com');
      expect(screen.getByTestId('token')).toHaveTextContent('persistent-token');
    });
  });

  describe('State reset functionality', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should reset to default authenticated state', () => {
      // First set unauthenticated
      setUnauthenticatedState();
      const { rerender } = renderWithAuth(<AuthStateDisplay />);
      expect(screen.getByTestId('authenticated')).toHaveTextContent('not-authenticated');
      
      // Reset to default
      resetMockAuthState();
      rerender(<AuthStateDisplay />);
      expect(screen.getByTestId('authenticated')).toHaveTextContent('authenticated');
      expect(screen.getByTestId('user')).toHaveTextContent(mockTestUser.email);
    });
  });
});

describe('Global Auth State Management', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  it('should update localStorage when token changes', () => {
    const testToken = 'test-storage-token';
    
    setMockAuthState({
      token: testToken,
      isAuthenticated: true
    });
    
    // Check that localStorage was updated
    expect(global.localStorage.getItem('jwt_token')).toBe(testToken);
    expect(global.localStorage.getItem('token')).toBe(testToken);
    expect(global.localStorage.getItem('auth_token')).toBe(testToken);
  });

  it('should clear localStorage when token is null', () => {
    setMockAuthState({
      token: null,
      isAuthenticated: false
    });
    
    // Check that localStorage was cleared
    expect(global.localStorage.getItem('jwt_token')).toBeNull();
    expect(global.localStorage.getItem('token')).toBeNull();
    expect(global.localStorage.getItem('auth_token')).toBeNull();
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});