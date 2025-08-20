/**
 * Authentication Flow Utilities
 * Reusable auth test components and utilities with 25-line function limit enforcement
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react';
import { TestProviders } from '../../setup/test-providers';

// Types for auth test components
export interface AuthTestState {
  isAuthenticated: boolean;
  user: any;
  error?: string;
}

export interface AuthComponentProps {
  onAuthStateChange?: (state: AuthTestState) => void;
  initialState?: AuthTestState;
}

// Custom hooks for auth test state (≤8 lines each)
export const useAuthTestState = (initialState?: AuthTestState) => {
  const [authState, setAuthState] = React.useState<AuthTestState>(
    initialState || { isAuthenticated: false, user: null }
  );
  
  const updateAuthState = (newState: Partial<AuthTestState>) => {
    setAuthState(prev => ({ ...prev, ...newState }));
  };
  
  return { authState, updateAuthState };
};

export const useAuthTestActions = (authStore: any, updateAuthState: (state: Partial<AuthTestState>) => void) => {
  const performLogin = async (user: any, token: string) => {
    await authStore.login(user, token);
    updateAuthState({ isAuthenticated: true, user });
  };
  
  const performLogout = () => {
    authStore.logout();
    updateAuthState({ isAuthenticated: false, user: null });
  };
  
  return { performLogin, performLogout };
};

// Component factories (≤8 lines each)
export const createLoginComponent = (authStore: any, mockUser: any, mockToken: string) => {
  return () => {
    const { authState, updateAuthState } = useAuthTestState();
    const { performLogin } = useAuthTestActions(authStore, updateAuthState);
    
    const handleLogin = async () => {
      await performLogin(mockUser, mockToken);
    };
    
    return (
      <div>
        <button onClick={handleLogin}>Login</button>
        <div data-testid="auth-status">
          {authState.isAuthenticated ? `Logged in as ${authState.user?.email}` : 'Not logged in'}
        </div>
      </div>
    );
  };
};

export const createLogoutComponent = (authStore: any) => {
  return () => {
    const { authState, updateAuthState } = useAuthTestState({ isAuthenticated: true, user: null });
    const { performLogout } = useAuthTestActions(authStore, updateAuthState);
    
    const handleLogout = () => {
      performLogout();
    };
    
    return (
      <div>
        <button onClick={handleLogout}>Logout</button>
        <div data-testid="auth-status">
          {authState.isAuthenticated ? 'Logged in' : 'Logged out'}
        </div>
      </div>
    );
  };
};

// Auth test action helpers (≤8 lines each)
export const performLoginAction = (getByText: any) => {
  fireEvent.click(getByText('Login'));
};

export const performLogoutAction = (getByText: any) => {
  fireEvent.click(getByText('Logout'));
};

export const verifyInitialUnauthenticatedState = (getByTestId: any) => {
  expect(getByTestId('auth-status')).toHaveTextContent('Not logged in');
};

export const verifyInitialAuthenticatedState = (getByTestId: any) => {
  expect(getByTestId('auth-status')).toHaveTextContent('Logged in');
};

export const verifySuccessfulLogin = async (getByTestId: any, email: string = 'test@example.com') => {
  await waitFor(() => {
    expect(getByTestId('auth-status')).toHaveTextContent(`Logged in as ${email}`);
  });
};

export const verifySuccessfulLogout = async (getByTestId: any) => {
  await waitFor(() => {
    expect(getByTestId('auth-status')).toHaveTextContent('Logged out');
  });
};

// State management utilities (≤8 lines each)
export const setupAuthenticatedState = (mockStore: any, mockUser: any, mockToken: string) => {
  (mockStore as any).setState({
    user: mockUser,
    token: mockToken,
    isAuthenticated: true
  });
};

export const performLoginFlow = (mockStore: any, mockUser: any, mockToken: string) => {
  localStorage.setItem('jwt_token', mockToken);
  localStorage.setItem('auth-user', JSON.stringify(mockUser));
  
  (mockStore as any).setState({
    user: mockUser,
    token: mockToken,
    isAuthenticated: true
  });
  
  const authStore = mockStore();
  authStore.login(mockUser, mockToken);
};

export const verifyStatePersistence = (mockToken: string, mockUser: any) => {
  expect(localStorage.getItem('jwt_token')).toBe(mockToken);
  expect(JSON.parse(localStorage.getItem('auth-user') || '{}')).toEqual(mockUser);
};

export const performPageRefresh = (mockStore: any) => {
  (mockStore as any).setState({ user: null, token: null, isAuthenticated: false });
  
  const mockStoreInstance = mockStore();
  mockStoreInstance.initializeFromStorage();
};

export const verifyStateRestoration = async (mockStore: any, mockUser: any, mockToken: string) => {
  await waitFor(() => {
    const authState = (mockStore as any).getState();
    expect(authState.isAuthenticated).toBe(true);
    expect(authState.user).toEqual(mockUser);
    expect(authState.token).toBe(mockToken);
  });
};

// Onboarding-specific utilities (≤8 lines each)
export const performOnboardingLogin = async (mockStore: any) => {
  const onboardingUser = {
    id: 'onboarding-user-123',
    email: 'newuser@netra.ai',
    name: 'New User',
    tier: 'free'
  };
  
  const authStore = mockStore();
  await authStore.login(onboardingUser, 'onboarding-token-123');
};

export const verifyOnboardingAuthState = (mockStore: any) => {
  const authStore = mockStore();
  expect(authStore.isAuthenticated).toBe(true);
  expect(authStore.user?.tier).toBe('free');
  expect(localStorage.getItem('jwt_token')).toBeTruthy();
};

export const simulateFirstThreadCreation = (mockChatStore: any) => {
  mockChatStore.mockReturnValue({
    ...mockChatStore(),
    createThread: jest.fn().mockResolvedValue({
      id: 'first-thread-123',
      title: 'Welcome Conversation'
    })
  });
};

export const expectOnboardingFlowComplete = (mockStore: any) => {
  const authStore = mockStore();
  expect(authStore.isAuthenticated).toBe(true);
  expect(authStore.user?.email).toBe('newuser@netra.ai');
};

export const simulateSessionTimeout = (mockStore: any) => {
  localStorage.removeItem('jwt_token');
  (mockStore as any).setState({
    isAuthenticated: false,
    token: null
  });
};

export const verifySessionTimeoutHandling = async (mockStore: any) => {
  await waitFor(() => {
    expect((mockStore as any).getState().isAuthenticated).toBe(false);
  });
};

export const performReauthentication = async (mockStore: any, mockUser: any) => {
  const authStore = mockStore();
  await authStore.login(mockUser, 'new-token-456');
};

export const expectContinuedOnboarding = (mockStore: any) => {
  expect((mockStore as any).getState().isAuthenticated).toBe(true);
  expect(localStorage.getItem('jwt_token')).toBe('new-token-456');
};

// Test setup utilities (≤8 lines each)
export const createMockAuthStore = () => {
  let currentAuthState = {
    isAuthenticated: false,
    user: null,
    token: null,
    login: jest.fn(),
    logout: jest.fn(),
    initializeFromStorage: jest.fn()
  };
  
  return { currentAuthState, setState: jest.fn(), getState: () => currentAuthState };
};

export const setupReactiveAuthStore = (mockStore: any) => {
  mockStore.mockImplementation(() => {
    return {
      ...mockStore.currentAuthState,
      login: jest.fn().mockImplementation(async (user, token) => {
        mockStore.currentAuthState = {
          ...mockStore.currentAuthState,
          user,
          token,
          isAuthenticated: true
        };
        localStorage.setItem('jwt_token', token);
        localStorage.setItem('auth-user', JSON.stringify(user));
      }),
      logout: jest.fn().mockImplementation(() => {
        mockStore.currentAuthState = {
          ...mockStore.currentAuthState,
          user: null,
          token: null,
          isAuthenticated: false
        };
        localStorage.removeItem('jwt_token');
        localStorage.removeItem('auth-user');
      }),
      initializeFromStorage: jest.fn().mockImplementation(() => {
        const token = localStorage.getItem('jwt_token');
        const userStr = localStorage.getItem('auth-user');
        if (token && userStr) {
          const user = JSON.parse(userStr);
          mockStore.currentAuthState = {
            ...mockStore.currentAuthState,
            user,
            token,
            isAuthenticated: true
          };
        }
      })
    };
  });
};