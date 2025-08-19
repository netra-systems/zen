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
import { authService } from '@/auth/service';
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
  let mockAuthStore: any;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    mockAuthStore = setupMockAuthStore();
    setupMockCookies();
    setupMockAuthService();
    
    jest.clearAllTimers();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  describe('Remember Me Functionality', () => {
    it('stores remember me preference in cookies', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await user.click(screen.getByTestId('remember-me-checkbox'));
        await performLogin('user@example.com', 'password123');
      });
      
      expect(document.cookie).toContain('remember_me=true');
    });

    it('extends token expiration with remember me', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await user.click(screen.getByTestId('remember-me-checkbox'));
        await performLogin('user@example.com', 'password123');
      });
      
      expect(authService.setTokenExpiration).toHaveBeenCalledWith('extended');
    });

    it('clears remember me on explicit logout', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await user.click(screen.getByTestId('remember-me-checkbox'));
        await performLogin('user@example.com', 'password123');
      });
      
      await act(async () => {
        mockAuthStore.logout();
      });
      
      expect(document.cookie).not.toContain('remember_me=true');
    });
  });

  describe('Social Login Integration', () => {
    it('initiates Google OAuth flow', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await user.click(screen.getByTestId('google-login-button'));
      });
      
      expect(authService.initiateGoogleLogin).toHaveBeenCalled();
    });

    it('handles OAuth callback with authorization code', async () => {
      window.history.pushState({}, '', '/auth/callback?code=oauth_code&state=oauth_state');
      
      renderLoginComponent();
      
      await waitFor(() => {
        expect(authService.handleOAuthCallback).toHaveBeenCalledWith('oauth_code', 'oauth_state');
      });
    });

    it('displays error for failed OAuth flow', async () => {
      window.history.pushState({}, '', '/auth/callback?error=access_denied');
      
      renderLoginComponent();
      
      await waitFor(() => {
        expect(screen.getByText('OAuth login was cancelled or failed')).toBeInTheDocument();
      });
    });
  });

  describe('MFA (Multi-Factor Authentication)', () => {
    it('prompts for MFA code when required', async () => {
      (authService.handleLogin as jest.Mock).mockResolvedValue({
        success: false,
        mfa_required: true,
        session_id: 'mfa_session_123'
      });
      
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('mfa@example.com', 'password123');
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('mfa-code-input')).toBeInTheDocument();
      });
    });

    it('validates MFA code and completes login', async () => {
      (authService.handleLogin as jest.Mock).mockResolvedValue({
        success: false,
        mfa_required: true,
        session_id: 'mfa_session_123'
      });
      
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('mfa@example.com', 'password123');
        await user.type(screen.getByTestId('mfa-code-input'), '123456');
        await user.click(screen.getByTestId('verify-mfa-button'));
      });
      
      expect(authService.verifyMFA).toHaveBeenCalledWith('mfa_session_123', '123456');
    });

    it('handles invalid MFA code gracefully', async () => {
      (authService.verifyMFA as jest.Mock).mockResolvedValue({
        success: false,
        error: 'Invalid MFA code'
      });
      
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('mfa@example.com', 'password123');
        await user.type(screen.getByTestId('mfa-code-input'), '000000');
        await user.click(screen.getByTestId('verify-mfa-button'));
      });
      
      await waitFor(() => {
        expect(screen.getByText('Invalid MFA code. Please try again.')).toBeInTheDocument();
      });
    });

    it('handles MFA verification failure', async () => {
      (authService.handleLogin as jest.Mock).mockResolvedValue({
        success: false,
        mfa_required: true,
        session_id: 'mfa_session_456'
      });
      
      (authService.verifyMFA as jest.Mock).mockRejectedValue(new Error('MFA service unavailable'));
      
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('mfa@example.com', 'password123');
        await user.type(screen.getByTestId('mfa-code-input'), '123456');
        await user.click(screen.getByTestId('verify-mfa-button'));
      });
      
      await waitFor(() => {
        expect(screen.getByText('MFA verification failed')).toBeInTheDocument();
      });
    });
  });
});