/**
 * Complete Authentication Flow Integration Tests
 * 
 * Tests comprehensive authentication flows including login, logout, 
 * token refresh, and state persistence for Netra Apex.
 * 
 * Business Value: Protects authentication security for all tiers,
 * prevents unauthorized access, ensures reliable user sessions.
 */

// Mock declarations (Jest hoisting)
const mockUseAuthStore = jest.fn();
const mockUseRouter = jest.fn();
const mockAuthService = {
  getAuthConfig: jest.fn(),
  getToken: jest.fn(),
  handleLogin: jest.fn(),
  handleLogout: jest.fn(),
  removeToken: jest.fn(),
  getDevLogoutFlag: jest.fn(),
  setDevLogoutFlag: jest.fn(),
  clearDevLogoutFlag: jest.fn(),
  handleDevLogin: jest.fn()
};

// Mock auth store before imports
jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));

// Mock auth service
jest.mock('@/auth/service', () => ({
  authService: mockAuthService
}));

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: mockUseRouter,
  usePathname: () => '/chat',
  useSearchParams: () => new URLSearchParams()
}));

// Mock JWT decode
jest.mock('jwt-decode', () => ({
  jwtDecode: jest.fn()
}));

import React from 'react';
import { render, fireEvent, waitFor, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { jwtDecode } from 'jwt-decode';
import { AuthProvider, AuthContext } from '@/auth/context';
import { setupTestEnvironment, resetTestState, mockUser, mockAuthToken } from '../test-utils/integration-test-setup';

// Test data for different user tiers
const testUsers = {
  free: { ...mockUser, tier: 'free', role: 'standard_user' },
  early: { ...mockUser, tier: 'early', role: 'power_user' },
  mid: { ...mockUser, tier: 'mid', role: 'power_user' },
  enterprise: { ...mockUser, tier: 'enterprise', role: 'admin' }
};

const mockAuthConfig = {
  development_mode: false,
  google_client_id: 'test-google-client-id',
  endpoints: {
    login: '/auth/login',
    logout: '/auth/logout',
    callback: '/auth/callback',
    token: '/auth/token',
    user: '/auth/me'
  },
  authorized_javascript_origins: ['http://localhost:3000'],
  authorized_redirect_uris: ['http://localhost:3000/auth/callback']
};

describe('Complete Authentication Flow Integration', () => {
  let mockRouter: any;

  beforeEach(() => {
    setupTestEnvironment();
    resetTestState();
    setupMockImplementations();
  });

  afterEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('OAuth Login Flow', () => {
    it('should complete OAuth login with token validation', async () => {
      const { mockLogin } = setupOAuthLoginScenario();
      const TestComponent = createAuthTestComponent();
      
      render(<TestComponent />);
      await triggerOAuthLogin();
      
      await verifyOAuthLoginSuccess(mockLogin);
      expectTokenStoredSecurely();
    });

    it('should handle OAuth callback with state validation', async () => {
      const { mockCallback } = setupOAuthCallbackScenario();
      
      await simulateOAuthCallback('valid-state', 'auth-code');
      await verifyCallbackProcessing(mockCallback);
      expectUserAuthenticated();
    });

    it('should reject invalid OAuth state', async () => {
      setupInvalidStateScenario();
      
      await simulateOAuthCallback('invalid-state', 'auth-code');
      expectAuthenticationRejected();
      expectSecurityLogEntry();
    });
  });

  describe('Development Mode Authentication', () => {
    it('should auto-login in development mode', async () => {
      const { mockDevLogin } = setupDevModeScenario();
      const TestComponent = createAuthTestComponent();
      
      render(<TestComponent />);
      await waitForDevAutoLogin();
      
      await verifyDevLoginSuccess(mockDevLogin);
      expectDevUserAuthenticated();
    });

    it('should respect dev logout flag', async () => {
      setupDevLoggedOutScenario();
      const TestComponent = createAuthTestComponent();
      
      render(<TestComponent />);
      await waitForAuthInitialization();
      
      expectNoAutoLogin();
      expectUnauthenticatedState();
    });
  });

  describe('Logout Flow', () => {
    it('should complete logout with full cleanup', async () => {
      const { mockLogout } = setupAuthenticatedScenario();
      const TestComponent = createAuthTestComponent();
      
      render(<TestComponent />);
      await triggerLogout();
      
      await verifyLogoutSuccess(mockLogout);
      expectCompleteCleanup();
    });

    it('should handle logout during active session', async () => {
      setupActiveSessionScenario();
      
      await performLogoutWhileActive();
      expectSessionTerminated();
      expectRedirectToLogin();
    });
  });

  describe('Token Management', () => {
    it('should validate token format and claims', async () => {
      const validToken = createValidJWT();
      
      await authenticateWithToken(validToken);
      expectTokenValidated();
      expectClaimsExtracted();
    });

    it('should handle malformed tokens', async () => {
      const malformedToken = 'invalid.token.format';
      
      await attemptAuthWithMalformedToken(malformedToken);
      expectTokenRejected();
      expectSecurityCleanup();
    });

    it('should handle expired tokens', async () => {
      const expiredToken = createExpiredJWT();
      
      await authenticateWithToken(expiredToken);
      expectTokenExpiredHandling();
      expectReauthenticationPrompt();
    });
  });

  // Helper functions for test setup (≤8 lines each)
  function setupMockImplementations() {
    mockUseAuthStore.mockReturnValue(createMockAuthStore());
    mockRouter = createMockRouter();
    mockUseRouter.mockReturnValue(mockRouter);
    mockAuthService.getAuthConfig.mockResolvedValue(mockAuthConfig);
    (jwtDecode as jest.Mock).mockReturnValue(testUsers.free);
  }

  function createMockAuthStore() {
    return {
      isAuthenticated: false,
      user: null,
      token: null,
      login: jest.fn(),
      logout: jest.fn(),
      setLoading: jest.fn(),
      setError: jest.fn()
    };
  }

  function createMockRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      refresh: jest.fn(),
      pathname: '/chat',
      query: {},
      asPath: '/chat'
    };
  }

  function createAuthTestComponent() {
    return () => {
      const authContext = React.useContext(AuthContext);
      return (
        <AuthProvider>
          <div>
            <button onClick={authContext?.login} data-testid="login-btn">
              Login
            </button>
            <button onClick={authContext?.logout} data-testid="logout-btn">
              Logout
            </button>
            <div data-testid="auth-status">
              {authContext?.user ? 'Authenticated' : 'Not authenticated'}
            </div>
          </div>
        </AuthProvider>
      );
    };
  }

  function setupOAuthLoginScenario() {
    const mockLogin = jest.fn();
    mockAuthService.handleLogin.mockImplementation(mockLogin);
    return { mockLogin };
  }

  async function triggerOAuthLogin() {
    const loginBtn = screen.getByTestId('login-btn');
    fireEvent.click(loginBtn);
  }

  async function verifyOAuthLoginSuccess(mockLogin: jest.Mock) {
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith(mockAuthConfig);
    });
  }

  function expectTokenStoredSecurely() {
    // Verify token is not stored in plain text
    const storedValues = Object.values(localStorage);
    const hasPlainToken = storedValues.some(value => value?.includes('test-token'));
    expect(hasPlainToken).toBe(false);
  }

  function setupOAuthCallbackScenario() {
    const mockCallback = jest.fn().mockResolvedValue({
      access_token: mockAuthToken,
      user: testUsers.free
    });
    return { mockCallback };
  }

  async function simulateOAuthCallback(state: string, code: string) {
    // Simulate OAuth callback URL parameters
    Object.defineProperty(window, 'location', {
      value: { search: `?state=${state}&code=${code}` },
      writable: true
    });
  }

  async function verifyCallbackProcessing(mockCallback: jest.Mock) {
    await waitFor(() => {
      expect(mockCallback).toHaveBeenCalledWith(
        expect.objectContaining({ code: 'auth-code' })
      );
    });
  }

  function expectUserAuthenticated() {
    const authStatus = screen.getByTestId('auth-status');
    expect(authStatus).toHaveTextContent('Authenticated');
  }

  function setupInvalidStateScenario() {
    mockAuthService.handleLogin.mockRejectedValue(
      new Error('Invalid OAuth state')
    );
  }

  function expectAuthenticationRejected() {
    const authStatus = screen.getByTestId('auth-status');
    expect(authStatus).toHaveTextContent('Not authenticated');
  }

  function expectSecurityLogEntry() {
    // Verify security event was logged
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('OAuth state validation failed')
    );
  }

  function setupDevModeScenario() {
    const devConfig = { ...mockAuthConfig, development_mode: true };
    mockAuthService.getAuthConfig.mockResolvedValue(devConfig);
    
    const mockDevLogin = jest.fn().mockResolvedValue({
      access_token: mockAuthToken,
      user: testUsers.free
    });
    mockAuthService.handleDevLogin.mockImplementation(mockDevLogin);
    mockAuthService.getDevLogoutFlag.mockReturnValue(false);
    
    return { mockDevLogin };
  }

  async function waitForDevAutoLogin() {
    await waitFor(() => {
      expect(mockAuthService.handleDevLogin).toHaveBeenCalled();
    }, { timeout: 2000 });
  }

  async function verifyDevLoginSuccess(mockDevLogin: jest.Mock) {
    expect(mockDevLogin).toHaveBeenCalledWith(
      expect.objectContaining({ development_mode: true })
    );
  }

  function expectDevUserAuthenticated() {
    expect(mockUseAuthStore().login).toHaveBeenCalledWith(
      testUsers.free,
      mockAuthToken
    );
  }

  function setupDevLoggedOutScenario() {
    const devConfig = { ...mockAuthConfig, development_mode: true };
    mockAuthService.getAuthConfig.mockResolvedValue(devConfig);
    mockAuthService.getDevLogoutFlag.mockReturnValue(true);
  }

  async function waitForAuthInitialization() {
    await waitFor(() => {
      expect(mockAuthService.getAuthConfig).toHaveBeenCalled();
    });
  }

  function expectNoAutoLogin() {
    expect(mockAuthService.handleDevLogin).not.toHaveBeenCalled();
  }

  function expectUnauthenticatedState() {
    expect(mockUseAuthStore().isAuthenticated).toBe(false);
  }

  function setupAuthenticatedScenario() {
    mockUseAuthStore.mockReturnValue({
      ...createMockAuthStore(),
      isAuthenticated: true,
      user: testUsers.free,
      token: mockAuthToken
    });
    
    const mockLogout = jest.fn();
    mockAuthService.handleLogout.mockImplementation(mockLogout);
    return { mockLogout };
  }

  async function triggerLogout() {
    const logoutBtn = screen.getByTestId('logout-btn');
    fireEvent.click(logoutBtn);
  }

  async function verifyLogoutSuccess(mockLogout: jest.Mock) {
    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledWith(mockAuthConfig);
    });
  }

  function expectCompleteCleanup() {
    expect(mockUseAuthStore().logout).toHaveBeenCalled();
    expect(localStorage.getItem('jwt_token')).toBeNull();
  }

  function setupActiveSessionScenario() {
    // Setup with active WebSocket connection and ongoing operations
    mockUseAuthStore.mockReturnValue({
      ...createMockAuthStore(),
      isAuthenticated: true,
      user: testUsers.enterprise
    });
  }

  async function performLogoutWhileActive() {
    await triggerLogout();
  }

  function expectSessionTerminated() {
    expect(mockUseAuthStore().logout).toHaveBeenCalled();
  }

  function expectRedirectToLogin() {
    expect(mockRouter.push).toHaveBeenCalledWith('/login');
  }

  function createValidJWT() {
    return 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.validclaims.signature';
  }

  async function authenticateWithToken(token: string) {
    localStorage.setItem('jwt_token', token);
    mockAuthService.getToken.mockReturnValue(token);
  }

  function expectTokenValidated() {
    expect(jwtDecode).toHaveBeenCalledWith(expect.any(String));
  }

  function expectClaimsExtracted() {
    expect(mockUseAuthStore().login).toHaveBeenCalled();
  }

  async function attemptAuthWithMalformedToken(token: string) {
    (jwtDecode as jest.Mock).mockImplementation(() => {
      throw new Error('Invalid token');
    });
    await authenticateWithToken(token);
  }

  function expectTokenRejected() {
    expect(mockAuthService.removeToken).toHaveBeenCalled();
  }

  function expectSecurityCleanup() {
    expect(mockUseAuthStore().logout).toHaveBeenCalled();
  }

  function createExpiredJWT() {
    const expiredClaims = { ...testUsers.free, exp: Math.floor(Date.now() / 1000) - 3600 };
    (jwtDecode as jest.Mock).mockReturnValue(expiredClaims);
    return 'expired.jwt.token';
  }

  function expectTokenExpiredHandling() {
    expect(mockAuthService.removeToken).toHaveBeenCalled();
  }

  function expectReauthenticationPrompt() {
    expect(mockRouter.push).toHaveBeenCalledWith('/login');
  }
});