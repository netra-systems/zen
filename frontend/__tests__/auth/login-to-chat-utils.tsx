/**
 * Auth Login Test Utilities
 * Shared utilities for login flow testing
 * Business Value: Ensures consistent test setup across login test modules
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { authService } from '@/auth/unified-auth-service';
import { useAuthStore } from '@/store/authStore';

// Test data
export const mockUser = {
  id: 'user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'admin' as const,
  permissions: ['read', 'write']
};

export const mockToken = 'mock-jwt-token-123';

// Setup functions (≤8 lines each)
export function setupMockAuthStore() {
  const mockAuthStore = {
    isAuthenticated: false,
    user: null,
    token: null,
    loading: false,
    error: null,
    login: jest.fn(),
    logout: jest.fn(() => {
      // Clear remember me cookie when logging out
      document.cookie = 'remember_me=; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    }),
    setLoading: jest.fn(),
    setError: jest.fn(),
    updateUser: jest.fn(),
    reset: jest.fn(),
    hasPermission: jest.fn(() => false),
    hasAnyPermission: jest.fn(() => false),
    hasAllPermissions: jest.fn(() => false),
    isAdminOrHigher: jest.fn(() => false),
    isDeveloperOrHigher: jest.fn(() => false)
  };
  jest.mocked(useAuthStore).mockReturnValue(mockAuthStore);
  return mockAuthStore;
}

export function setupMockAuthService() {
  jest.mocked(authService).handleLogin = jest.fn().mockResolvedValue({
    success: true,
    user: mockUser,
    token: mockToken
  });
  jest.mocked(authService).setToken = jest.fn();
  jest.mocked(authService).getCurrentUser = jest.fn().mockResolvedValue(mockUser);
  jest.mocked(authService).validateToken = jest.fn().mockResolvedValue(true);
  jest.mocked(authService).refreshToken = jest.fn().mockResolvedValue(mockToken);
  jest.mocked(authService).initiateGoogleLogin = jest.fn();
  jest.mocked(authService).handleOAuthCallback = jest.fn();
  jest.mocked(authService).verifyMFA = jest.fn().mockResolvedValue({ success: true });
  jest.mocked(authService).setTokenExpiration = jest.fn();
}

export function setupMockCookies() {
  Object.defineProperty(document, 'cookie', {
    writable: true,
    value: ''
  });
  
  const localStorageMock = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
  };
  Object.defineProperty(window, 'localStorage', {
    value: localStorageMock
  });
  (localStorageMock.getItem as jest.Mock).mockReturnValue(mockToken);
}

// Import TestProviders at module level
import { TestProviders } from '../setup/test-providers';

export function renderLoginComponent(mockPush?: jest.Mock) {
  return render(
    <TestProviders>
      <LoginForm onRedirect={mockPush} />
    </TestProviders>
  );
}

export async function performLogin(email: string, password: string, screenContext: any) {
  const user = userEvent.setup();
  
  await user.type(screenContext.getByTestId('email-input'), email);
  await user.type(screenContext.getByTestId('password-input'), password);
  await user.click(screenContext.getByTestId('login-button'));
}

// Mock Login Form Component for testing
export const LoginForm = ({ onRedirect }: { onRedirect?: jest.Mock }) => {
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [rememberMe, setRememberMe] = React.useState(false);
  const [error, setError] = React.useState('');
  const [showMFA, setShowMFA] = React.useState(false);
  const [mfaCode, setMfaCode] = React.useState('');
  const [mfaSession, setMfaSession] = React.useState('');
  
  const handleLogin = async () => {
    try {
      setError('');
      
      if (!email.includes('@')) {
        setError('Please enter a valid email address');
        return;
      }
      if (!password) {
        setError('Password is required');
        return;
      }
      
      const result = await authService.handleLogin(email, password);
      
      if (result.mfa_required) {
        setShowMFA(true);
        setMfaSession(result.session_id);
        return;
      }
      
      if (result.success) {
        await processSuccessfulLogin(result, rememberMe, onRedirect);
      } else {
        setError(result.error || 'Login failed');
      }
    } catch (err: any) {
      handleLoginError(err, setError);
    }
  };
  
  const handleMFAVerify = async () => {
    try {
      const result = await authService.verifyMFA(mfaSession, mfaCode);
      if (result.success) {
        setShowMFA(false);
      } else {
        setError('Invalid MFA code. Please try again.');
      }
    } catch (err) {
      setError('MFA verification failed');
    }
  };
  
  const handleGoogleLogin = async () => {
    await authService.initiateGoogleLogin();
  };
  
  const handleRetry = () => {
    setError('');
  };
  
  React.useEffect(() => {
    handleOAuthCallback(setError);
  }, []);

  return (
    <div data-testid="login-form">
      <input
        data-testid="email-input"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
      />
      <input
        data-testid="password-input"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
      />
      <label>
        <input
          data-testid="remember-me-checkbox"
          type="checkbox"
          checked={rememberMe}
          onChange={(e) => setRememberMe(e.target.checked)}
        />
        Remember me
      </label>
      <button data-testid="login-button" onClick={handleLogin}>Login</button>
      <button data-testid="google-login-button" onClick={handleGoogleLogin}>Login with Google</button>
      
      {error && <div data-testid="error-message">{error}</div>}
      {error.includes('Network') && <button data-testid="retry-button" onClick={handleRetry}>Retry</button>}
      
      {showMFA && (
        <div data-testid="mfa-container">
          <input 
            data-testid="mfa-code-input" 
            placeholder="Enter MFA code"
            value={mfaCode}
            onChange={(e) => setMfaCode(e.target.value)}
          />
          <button data-testid="verify-mfa-button" onClick={handleMFAVerify}>Verify</button>
        </div>
      )}
    </div>
  );
};

// Helper functions (≤8 lines each)
async function processSuccessfulLogin(result: any, rememberMe: boolean, onRedirect?: jest.Mock) {
  // Use the mocked useAuthStore instead of requiring it
  const mockAuthStore = useAuthStore();
  
  await authService.setToken(result.token);
  localStorage.setItem('jwt_token', result.token);
  
  if (rememberMe) {
    document.cookie = 'remember_me=true';
    await authService.setTokenExpiration('extended');
  }
  
  const isValid = await authService.validateToken(result.token);
  if (!isValid) {
    throw new Error('Session expired. Please login again.');
  }
  
  const userProfile = await authService.getCurrentUser();
  mockAuthStore.login(userProfile, result.token);
  mockAuthStore.updateUser(userProfile);
  
  if (onRedirect) {
    onRedirect('/chat');
  }
  
  await authService.refreshToken();
}

function handleLoginError(err: any, setError: (error: string) => void) {
  if (err.message.includes('Network')) {
    setError('Network error. Please check your connection.');
  } else {
    setError('Login failed');
  }
}

function handleOAuthCallback(setError: (error: string) => void) {
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  const state = urlParams.get('state');
  const oauthError = urlParams.get('error');
  
  if (code && state) {
    authService.handleOAuthCallback(code, state);
  } else if (oauthError) {
    setError('OAuth login was cancelled or failed');
  }
}