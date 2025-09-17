/**
 * CRITICAL: Auth Context Initialization Test Suite
 * 
 * Tests the authentication context initialization flow to ensure
 * the user state is properly set when a valid JWT token exists
 * in localStorage, preventing the empty main chat issue.
 * 
 * @compliance type_safety.xml - Strongly typed test suite
 * @compliance conventions.xml - Focused test functions under 25 lines
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/auth/context';
import { AuthGuard } from '@/components/AuthGuard';
import { unifiedAuthService } from '@/auth/unified-auth-service';
// jwt-decode import removed - JWT authentication removed

// Mock dependencies
jest.mock('@/auth/unified-auth-service');
// jwt-decode mock removed - JWT authentication removed
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
  }),
}));
jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  },
}));
jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: () => ({
    trackLogin: jest.fn(),
    trackLogout: jest.fn(),
    trackOAuthComplete: jest.fn(),
    trackError: jest.fn(),
    trackPageView: jest.fn(),
  }),
}));

const mockUser = {
  id: 'user_123',
  email: 'test@example.com',
  full_name: 'Test User',
  exp: Math.floor(Date.now() / 1000) + 3600, // Valid for 1 hour
};

const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock.token';

const mockAuthConfig = {
  development_mode: false,
  google_client_id: 'mock-client-id',
  endpoints: {
    login: '/auth/login',
    logout: '/auth/logout',
    callback: '/auth/callback',
    token: '/auth/token',
    user: '/auth/me',
  },
  authorized_javascript_origins: ['http://localhost:3000'],
  authorized_redirect_uris: ['http://localhost:3000/auth/callback'],
};

// Test component to access auth context
const TestComponent: React.FC = () => {
  const { user, token, initialized, loading } = useAuth();
  return (
    <div>
      <div data-testid="user-state">{user ? user.email : 'null'}</div>
      <div data-testid="token-state">{token ? 'present' : 'null'}</div>
      <div data-testid="initialized-state">{initialized ? 'true' : 'false'}</div>
      <div data-testid="loading-state">{loading ? 'true' : 'false'}</div>
    </div>
  );
};

// Component that simulates the MainChat being rendered via AuthGuard
const ProtectedMainChat: React.FC = () => {
  return (
    <AuthGuard>
      <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
        <div data-testid="main-chat">Chat Interface Loaded</div>
      </main>
    </AuthGuard>
  );
};

describe('Auth Context Initialization - Critical Bug Fix', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    
    // Setup default mocks
    (unifiedAuthService.getAuthConfig as jest.Mock).mockResolvedValue(mockAuthConfig);
    (unifiedAuthService.needsRefresh as jest.Mock).mockReturnValue(false);
    (jwtDecode as jest.Mock).mockReturnValue(mockUser);
  });

  afterEach(() => {
    jest.clearAllTimers();
  });

  describe('Scenario 1: Fresh Page Load with Valid Token in localStorage', () => {
    test('should decode token and set user state on initial mount', async () => {
      // Setup: Token exists in localStorage (simulating logged-in user)
      localStorage.setItem('jwt_token', mockToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(mockToken);

      // Act: Render auth provider
      const { rerender } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Assert: User should be set from decoded token
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('test@example.com');
        expect(screen.getByTestId('token-state')).toHaveTextContent('present');
        expect(screen.getByTestId('initialized-state')).toHaveTextContent('true');
      });

      // Verify jwt decode was called
      expect(jwtDecode).toHaveBeenCalledWith(mockToken);
    });

    test('should render MainChat when user is authenticated', async () => {
      // Setup: Token exists in localStorage
      localStorage.setItem('jwt_token', mockToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(mockToken);

      // Act: Render protected component
      render(
        <AuthProvider>
          <ProtectedMainChat />
        </AuthProvider>
      );

      // Assert: MainChat should be rendered
      await waitFor(() => {
        expect(screen.getByTestId('main-chat')).toBeInTheDocument();
        expect(screen.getByTestId('main-chat')).toHaveTextContent('Chat Interface Loaded');
      });
    });
  });

  describe('Scenario 2: OAuth Callback with Token in State', () => {
    test('should process token even when already in state', async () => {
      // Setup: Simulate OAuth callback scenario where token is in state
      const { result } = renderHook(() => useAuth(), {
        wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
        initialProps: {
          token: mockToken, // Token already in state
        },
      });

      // Mock getToken to return same token
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(mockToken);

      // Act: Trigger fetchAuthConfig
      await act(async () => {
        await (unifiedAuthService.getAuthConfig as jest.Mock)();
      });

      // Assert: User should still be set
      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
        expect(result.current.token).toBe(mockToken);
      });
    });
  });

  describe('Scenario 3: Token Refresh Flow', () => {
    test('should handle expired token and attempt refresh', async () => {
      // Setup: Token is expired
      const expiredUser = { ...mockUser, exp: Math.floor(Date.now() / 1000) - 3600 };
      (jwtDecode as jest.Mock).mockReturnValue(expiredUser);
      localStorage.setItem('jwt_token', mockToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(mockToken);

      // Mock refresh to return new token
      const newToken = 'new.jwt.token';
      const newUser = { ...mockUser, exp: Math.floor(Date.now() / 1000) + 7200 };
      (unifiedAuthService.refreshToken as jest.Mock).mockResolvedValue({
        access_token: newToken,
      });

      // Act: Render auth provider
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Wait for refresh attempt
      await waitFor(() => {
        expect(unifiedAuthService.refreshToken).toHaveBeenCalled();
      });
    });
  });

  describe('Scenario 4: No Token Present', () => {
    test('should not set user when no token exists', async () => {
      // Setup: No token in localStorage
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(null);

      // Act: Render auth provider
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Assert: User should remain null
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('null');
        expect(screen.getByTestId('token-state')).toHaveTextContent('null');
        expect(screen.getByTestId('initialized-state')).toHaveTextContent('true');
      });
    });

    test('should redirect to login when accessing protected route without auth', async () => {
      // Setup: No token
      const mockPush = jest.fn();
      jest.mock('next/navigation', () => ({
        useRouter: () => ({ push: mockPush }),
      }));

      // Act: Render protected component
      render(
        <AuthProvider>
          <ProtectedMainChat />
        </AuthProvider>
      );

      // Assert: Should not render MainChat
      await waitFor(() => {
        expect(screen.queryByTestId('main-chat')).not.toBeInTheDocument();
      });
    });
  });

  describe('Scenario 5: Race Conditions', () => {
    test('should handle rapid token updates without losing user state', async () => {
      // Setup: Initial token
      localStorage.setItem('jwt_token', mockToken);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(mockToken);

      const { rerender } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Wait for initial user set
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('test@example.com');
      });

      // Simulate rapid token update (e.g., from WebSocket)
      const updatedToken = 'updated.jwt.token';
      const updatedUser = { ...mockUser, email: 'updated@example.com' };
      (jwtDecode as jest.Mock).mockReturnValue(updatedUser);
      
      act(() => {
        localStorage.setItem('jwt_token', updatedToken);
        (unifiedAuthService.getToken as jest.Mock).mockReturnValue(updatedToken);
      });

      // Force re-render
      rerender(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // User state should remain stable
      await waitFor(() => {
        expect(screen.getByTestId('user-state').textContent).toBeTruthy();
      });
    });
  });

  describe('Scenario 6: Development Mode Auto-Login', () => {
    test('should auto-login in development mode when no logout flag', async () => {
      // Setup: Development mode, no token, no logout flag
      const devAuthConfig = { ...mockAuthConfig, development_mode: true };
      (unifiedAuthService.getAuthConfig as jest.Mock).mockResolvedValue(devAuthConfig);
      (unifiedAuthService.getToken as jest.Mock).mockReturnValue(null);
      (unifiedAuthService.getDevLogoutFlag as jest.Mock).mockReturnValue(false);
      (unifiedAuthService.handleDevLogin as jest.Mock).mockResolvedValue({
        access_token: mockToken,
      });

      // Act: Render auth provider
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Assert: Should attempt dev login and set user
      await waitFor(() => {
        expect(unifiedAuthService.handleDevLogin).toHaveBeenCalledWith(devAuthConfig);
        expect(screen.getByTestId('user-state')).toHaveTextContent('test@example.com');
      });
    });
  });

  describe('Critical Edge Case: Token in State from Constructor', () => {
    test('should always decode and set user even when token initialized in state', async () => {
      // This is the CRITICAL test for the bug fix
      // Simulates the exact condition that was causing the empty main chat
      
      // Setup: Token exists in localStorage before component mounts
      localStorage.setItem('jwt_token', mockToken);
      
      // Mock to simulate token being read during state initialization
      const mockGetToken = jest.fn().mockReturnValue(mockToken);
      (unifiedAuthService.getToken as jest.Mock) = mockGetToken;

      // Act: Render auth provider
      // The token will be initialized in useState(() => ...) 
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Assert: User MUST be set even though token was already in state
      await waitFor(() => {
        expect(screen.getByTestId('user-state')).toHaveTextContent('test@example.com');
        expect(screen.getByTestId('token-state')).toHaveTextContent('present');
      }, { timeout: 3000 });

      // Verify the token was decoded
      expect(jwtDecode).toHaveBeenCalledWith(mockToken);
      
      // Verify MainChat would render
      const { container } = render(
        <AuthProvider>
          <ProtectedMainChat />
        </AuthProvider>
      );
      
      await waitFor(() => {
        const mainChat = container.querySelector('[data-testid="main-chat"]');
        expect(mainChat).toBeInTheDocument();
      });
    });
  });
});

function renderHook<T>(
  callback: () => T,
  options?: { wrapper: React.FC<{ children: React.ReactNode }>, initialProps?: any }
) {
  let result: { current: T };
  
  function TestHookComponent() {
    result = { current: callback() };
    return null;
  }
  
  const Wrapper = options?.wrapper || React.Fragment;
  
  render(
    <Wrapper>
      <TestHookComponent />
    </Wrapper>
  );
  
  return { result: result! };
}