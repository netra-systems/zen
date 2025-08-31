/**
 * Auth Login Advanced Features Tests
 * Remember me, social login, and MFA functionality
 * Business Value: Ensures comprehensive auth experience for enterprise users
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 * Coverage: Advanced auth features for enhanced user experience
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '@/auth/context';
import { authService } from '@/auth/unified-auth-service';
import { useAuthStore } from '@/store/authStore';
import '@testing-library/jest-dom';
import {
  setupMockAuthStore,
  setupMockCookies,
  setupMockAuthService,
  renderLoginComponent,
  performLogin,
  mockUser,
  mockToken
} from './login-to-chat-utils';

// Mock dependencies for isolated auth testing
jest.mock('@/auth/service');
jest.mock('@/store/authStore');
jest.mock('@/lib/auth-service-config');
jest.mock('jwt-decode', () => ({
  jwtDecode: jest.fn()
}));

describe('Auth Login Advanced Features', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let mockAuthStore: any;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup({ delay: null }); // Disable delays for faster tests
    mockAuthStore = setupMockAuthStore();
    setupMockCookies();
    setupMockAuthService();
  });

  afterEach(() => {
    jest.clearAllMocks();
    jest.clearAllTimers();
      cleanupAntiHang();
  });

  describe('Remember Me Functionality', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('stores remember me preference in cookies', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await user.click(screen.getByTestId('remember-me-checkbox'));
        await performLogin('user@example.com', 'password123', screen);
      });
      
      expect(document.cookie).toContain('remember_me=true');
    }, 15000);

    it('extends token expiration with remember me', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await user.click(screen.getByTestId('remember-me-checkbox'));
        await performLogin('user@example.com', 'password123', screen);
      });
      
      expect(authService.setTokenExpiration).toHaveBeenCalledWith('extended');
    }, 15000);

    it('clears remember me on explicit logout', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await user.click(screen.getByTestId('remember-me-checkbox'));
        await performLogin('user@example.com', 'password123', screen);
      });
      
      await act(async () => {
        mockAuthStore.logout();
      });
      
      expect(document.cookie).not.toContain('remember_me=true');
    }, 15000);
  });

  describe('Social Login Integration', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('initiates Google OAuth flow', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await user.click(screen.getByTestId('google-login-button'));
      });
      
      expect(authService.initiateGoogleLogin).toHaveBeenCalled();
    }, 15000);

    it('handles OAuth callback with authorization code', async () => {
      window.history.pushState({}, '', '/auth/callback?code=oauth_code&state=oauth_state');
      
      renderLoginComponent();
      
      await waitFor(() => {
        expect(authService.handleOAuthCallback).toHaveBeenCalledWith('oauth_code', 'oauth_state');
      });
    }, 15000);

    it('displays error for failed OAuth flow', async () => {
      window.history.pushState({}, '', '/auth/callback?error=access_denied');
      
      renderLoginComponent();
      
      await waitFor(() => {
        expect(screen.getByText('OAuth login was cancelled or failed')).toBeInTheDocument();
      });
    }, 15000);
  });

  describe('MFA (Multi-Factor Authentication)', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('prompts for MFA code when required', async () => {
      jest.mocked(authService.handleLogin).mockResolvedValue({
        success: false,
        mfa_required: true,
        session_id: 'mfa_session_123'
      });
      
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('mfa@example.com', 'password123', screen);
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('mfa-code-input')).toBeInTheDocument();
      });
    }, 15000);

    it('validates MFA code and completes login', async () => {
      jest.mocked(authService.handleLogin).mockResolvedValue({
        success: false,
        mfa_required: true,
        session_id: 'mfa_session_123'
      });
      
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('mfa@example.com', 'password123', screen);
      });
      
      // Wait for MFA UI to appear
      await waitFor(() => {
        expect(screen.getByTestId('mfa-code-input')).toBeInTheDocument();
      });
      
      await act(async () => {
        await user.type(screen.getByTestId('mfa-code-input'), '123456');
        await user.click(screen.getByTestId('verify-mfa-button'));
      });
      
      expect(authService.verifyMFA).toHaveBeenCalledWith('mfa_session_123', '123456');
    }, 15000);

    it('handles invalid MFA code gracefully', async () => {
      jest.mocked(authService.handleLogin).mockResolvedValue({
        success: false,
        mfa_required: true,
        session_id: 'mfa_session_123'
      });
      
      jest.mocked(authService.verifyMFA).mockResolvedValue({
        success: false,
        error: 'Invalid MFA code'
      });
      
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('mfa@example.com', 'password123', screen);
      });
      
      // Wait for MFA UI to appear
      await waitFor(() => {
        expect(screen.getByTestId('mfa-code-input')).toBeInTheDocument();
      });
      
      await act(async () => {
        await user.type(screen.getByTestId('mfa-code-input'), '000000');
        await user.click(screen.getByTestId('verify-mfa-button'));
      });
      
      await waitFor(() => {
        expect(screen.getByText('Invalid MFA code. Please try again.')).toBeInTheDocument();
      });
    }, 15000);

    it('handles MFA verification failure', async () => {
      jest.mocked(authService.handleLogin).mockResolvedValue({
        success: false,
        mfa_required: true,
        session_id: 'mfa_session_456'
      });
      
      jest.mocked(authService.verifyMFA).mockRejectedValue(new Error('MFA service unavailable'));
      
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('mfa@example.com', 'password123', screen);
      });
      
      // Wait for MFA UI to appear
      await waitFor(() => {
        expect(screen.getByTestId('mfa-code-input')).toBeInTheDocument();
      });
      
      await act(async () => {
        await user.type(screen.getByTestId('mfa-code-input'), '123456');
        await user.click(screen.getByTestId('verify-mfa-button'));
      });
      
      await waitFor(() => {
        expect(screen.getByText('MFA verification failed')).toBeInTheDocument();
      });
    }, 15000);
  });
});