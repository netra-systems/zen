/**
 * Authentication Flow Integration Tests
 * 
 * Tests core authentication functionality including
 * login, logout, and state management.
 */

import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import { useAuthStore } from '@/store/authStore';
import { TestProviders } from '../test-utils/providers';
import {
  setupTestEnvironment,
  createWebSocketServer,
  resetTestState,
  mockUser,
  mockAuthToken,
  expectAuthenticatedState,
  expectUnauthenticatedState,
  performFullCleanup,
  mockNextRouter
} from '../test-utils/integration-test-setup';

// Setup mocks
mockNextRouter();

describe('Authentication Flow Integration', () => {
  let server: any;

  beforeEach(() => {
    setupTestEnvironment();
    server = createWebSocketServer();
    resetTestState();
  });

  afterEach(() => {
    performFullCleanup(server);
  });

  it('should handle login and authentication', async () => {
    const LoginComponent = createLoginComponent();
    const { getByText, getByTestId } = render(<LoginComponent />);
    
    verifyInitialUnauthenticatedState(getByTestId);
    performLoginAction(getByText);
    
    await verifySuccessfulLogin(getByTestId);
    expectAuthenticatedState();
  });

  it('should handle logout and cleanup', async () => {
    setupAuthenticatedState();
    
    const LogoutComponent = createLogoutComponent();
    const { getByText, getByTestId } = render(<LogoutComponent />);
    
    verifyInitialAuthenticatedState(getByTestId);
    performLogoutAction(getByText);
    
    await verifySuccessfulLogout(getByTestId);
    expectUnauthenticatedState();
  });

  it('should persist authentication state', async () => {
    performLoginFlow();
    verifyStatePersistence();
    performPageRefresh();
    await verifyStateRestoration();
  });

  // Component factories
  function createLoginComponent() {
    return () => {
      const { login, isAuthenticated, user } = useAuthStore();
      
      const handleLogin = async () => {
        await login(mockUser, mockAuthToken);
      };
      
      return (
        <div>
          <button onClick={handleLogin}>Login</button>
          <div data-testid="auth-status">
            {isAuthenticated ? `Logged in as ${user?.email}` : 'Not logged in'}
          </div>
        </div>
      );
    };
  }

  function createLogoutComponent() {
    return () => {
      const { logout, isAuthenticated } = useAuthStore();
      
      return (
        <div>
          <button onClick={logout}>Logout</button>
          <div data-testid="auth-status">
            {isAuthenticated ? 'Logged in' : 'Logged out'}
          </div>
        </div>
      );
    };
  }

  // Test action helpers
  function verifyInitialUnauthenticatedState(getByTestId: any) {
    expect(getByTestId('auth-status')).toHaveTextContent('Not logged in');
  }

  function performLoginAction(getByText: any) {
    fireEvent.click(getByText('Login'));
  }

  function verifyInitialAuthenticatedState(getByTestId: any) {
    expect(getByTestId('auth-status')).toHaveTextContent('Logged in');
  }

  function performLogoutAction(getByText: any) {
    fireEvent.click(getByText('Logout'));
  }

  async function verifySuccessfulLogin(getByTestId: any) {
    await waitFor(() => {
      expect(getByTestId('auth-status')).toHaveTextContent('Logged in as test@example.com');
    });
  }

  async function verifySuccessfulLogout(getByTestId: any) {
    await waitFor(() => {
      expect(getByTestId('auth-status')).toHaveTextContent('Logged out');
    });
  }

  function setupAuthenticatedState() {
    useAuthStore.setState({
      user: mockUser,
      token: mockAuthToken,
      isAuthenticated: true
    });
  }

  function performLoginFlow() {
    useAuthStore.getState().login(mockUser, mockAuthToken);
  }

  function verifyStatePersistence() {
    expect(localStorage.getItem('auth-token')).toBe(mockAuthToken);
    expect(JSON.parse(localStorage.getItem('auth-user') || '{}')).toEqual(mockUser);
  }

  function performPageRefresh() {
    // Simulate page refresh by resetting store and calling initialization
    useAuthStore.setState({ user: null, token: null, isAuthenticated: false });
    useAuthStore.getState().initializeFromStorage();
  }

  async function verifyStateRestoration() {
    await waitFor(() => {
      expectAuthenticatedState();
    });
  }
});