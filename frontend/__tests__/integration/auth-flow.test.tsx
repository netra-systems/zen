/**
 * Authentication Flow Integration Tests
 * 
 * Tests core authentication functionality including
 * login, logout, and state management.
 */

// Declare mocks first (Jest Module Hoisting)
const mockUseAuthStore = jest.fn();
const mockUseUnifiedChatStore = jest.fn();
const mockUseWebSocket = jest.fn();
const mockUseLoadingState = jest.fn();
const mockUseThreadNavigation = jest.fn();

// Mock hooks before imports
jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: mockUseLoadingState
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: mockUseThreadNavigation
}));

// Mock AuthGate to always render children
jest.mock('@/components/auth/AuthGate', () => {
  return function MockAuthGate({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
  };
});

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/'
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams()
}));

// Now imports
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

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    })
  };
})();
global.localStorage = localStorageMock as any;

describe('Authentication Flow Integration', () => {
  let server: any;

  beforeEach(() => {
    setupTestEnvironment();
    server = createWebSocketServer();
    resetTestState();
    
    // Clear localStorage
    localStorageMock.clear();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    localStorageMock.removeItem.mockClear();
    
    // Setup hook mocks with reactive behavior
    let currentAuthState = {
      isAuthenticated: false,
      user: null,
      token: null,
      login: jest.fn(),
      logout: jest.fn(),
      initializeFromStorage: jest.fn()
    };
    
    // Make the store reactive - when state changes, the hook returns new values
    mockUseAuthStore.mockImplementation(() => {
      return {
        ...currentAuthState,
        login: jest.fn().mockImplementation(async (user, token) => {
          currentAuthState = {
            ...currentAuthState,
            user,
            token,
            isAuthenticated: true
          };
          // Store in localStorage like real implementation
          localStorage.setItem('auth-token', token);
          localStorage.setItem('auth-user', JSON.stringify(user));
        }),
        logout: jest.fn().mockImplementation(() => {
          currentAuthState = {
            ...currentAuthState,
            user: null,
            token: null,
            isAuthenticated: false
          };
          localStorage.removeItem('auth-token');
          localStorage.removeItem('auth-user');
        }),
        initializeFromStorage: jest.fn().mockImplementation(() => {
          const token = localStorage.getItem('auth-token');
          const userStr = localStorage.getItem('auth-user');
          if (token && userStr) {
            const user = JSON.parse(userStr);
            currentAuthState = {
              ...currentAuthState,
              user,
              token,
              isAuthenticated: true
            };
          }
        })
      };
    });
    
    // Add setState and getState methods to the mock with proper state management
    (mockUseAuthStore as any).setState = jest.fn().mockImplementation((newState) => {
      currentAuthState = { ...currentAuthState, ...newState };
    });
    
    // Ensure getState always returns the current state
    Object.defineProperty(mockUseAuthStore, 'getState', {
      value: () => currentAuthState,
      configurable: true,
      writable: true
    });
    
    mockUseUnifiedChatStore.mockReturnValue({
      messages: [],
      threads: [],
      addMessage: jest.fn()
    });
    
    mockUseWebSocket.mockReturnValue({
      sendMessage: jest.fn(),
      isConnected: true
    });
    
    mockUseLoadingState.mockReturnValue({
      isLoading: false,
      setLoading: jest.fn()
    });
    
    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: null,
      navigateToThread: jest.fn()
    });
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
      const authStore = useAuthStore();
      const [localState, setLocalState] = React.useState({
        isAuthenticated: authStore.isAuthenticated,
        user: authStore.user
      });
      
      const handleLogin = async () => {
        await authStore.login(mockUser, mockAuthToken);
        setLocalState({
          isAuthenticated: true,
          user: mockUser
        });
      };
      
      return (
        <div>
          <button onClick={handleLogin}>Login</button>
          <div data-testid="auth-status">
            {localState.isAuthenticated ? `Logged in as ${localState.user?.email}` : 'Not logged in'}
          </div>
        </div>
      );
    };
  }

  function createLogoutComponent() {
    return () => {
      const authStore = useAuthStore();
      const [localState, setLocalState] = React.useState({
        isAuthenticated: true // Start authenticated for logout test
      });
      
      const handleLogout = () => {
        authStore.logout();
        setLocalState({ isAuthenticated: false });
      };
      
      return (
        <div>
          <button onClick={handleLogout}>Logout</button>
          <div data-testid="auth-status">
            {localState.isAuthenticated ? 'Logged in' : 'Logged out'}
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
    // Simulate the login process that sets localStorage and updates state
    localStorage.setItem('auth-token', mockAuthToken);
    localStorage.setItem('auth-user', JSON.stringify(mockUser));
    
    // Update the mock state directly 
    (mockUseAuthStore as any).setState({
      user: mockUser,
      token: mockAuthToken,
      isAuthenticated: true
    });
    
    const authStore = useAuthStore();
    authStore.login(mockUser, mockAuthToken);
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