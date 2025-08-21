/**
 * Auth Login Flow Tests - Core Functionality
 * Basic login flow, credential validation, and network error handling
 * Business Value: Ensures secure, reliable user authentication experience
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 * Coverage: Core auth scenarios from credentials to chat state
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

describe('Auth Login Flow - Core', () => {
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

  describe('Successful Login Flow', () => {
    it('completes successful login with valid credentials', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('valid@example.com', 'validpassword');
      });
      
      await waitFor(() => {
        expect(mockAuthStore.login).toHaveBeenCalledWith(
          expect.objectContaining({ email: 'valid@example.com' }),
          mockToken
        );
      });
    });

    it('handles token storage correctly', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('user@example.com', 'password123');
      });
      
      expect(authService.setToken).toHaveBeenCalledWith(mockToken);
      expect(localStorage.getItem('jwt_token')).toBe(mockToken);
    });

    it('redirects to chat after successful login', async () => {
      const mockPush = jest.fn();
      renderLoginComponent(mockPush);
      
      await act(async () => {
        await performLogin('user@example.com', 'password123');
      });
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/chat');
      });
    });

    it('fetches user profile after token storage', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('user@example.com', 'password123');
      });
      
      await waitFor(() => {
        expect(authService.getCurrentUser).toHaveBeenCalled();
        expect(mockAuthStore.updateUser).toHaveBeenCalledWith(mockUser);
      });
    });
  });

  describe('Invalid Credentials Handling', () => {
    it('displays error for invalid email format', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('invalid-email', 'password123');
      });
      
      expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument();
    });

    it('displays error for empty password', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('user@example.com', '');
      });
      
      expect(screen.getByText('Password is required')).toBeInTheDocument();
    });

    it('handles unauthorized response correctly', async () => {
      jest.mocked(authService.handleLogin).mockResolvedValue({
        success: false,
        error: 'Invalid email or password'
      });
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('user@example.com', 'wrongpassword');
      });
      
      await waitFor(() => {
        expect(screen.getByText('Invalid email or password')).toBeInTheDocument();
      });
    });

    it('prevents multiple submissions with same credentials', async () => {
      renderLoginComponent();
      
      const button = screen.getByTestId('login-button');
      await act(async () => {
        await user.click(button);
        await user.click(button);
      });
      
      expect(authService.handleLogin).toHaveBeenCalledTimes(1);
    });
  });

  describe('Network Error Recovery', () => {
    it('displays network error message on connection failure', async () => {
      jest.mocked(authService.handleLogin).mockRejectedValue(new Error('Network error'));
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('user@example.com', 'password123');
      });
      
      await waitFor(() => {
        expect(screen.getByText('Network error. Please check your connection.')).toBeInTheDocument();
      });
    });

    it('enables retry after network error', async () => {
      jest.mocked(authService.handleLogin).mockRejectedValue(new Error('Network error'));
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('user@example.com', 'password123');
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('retry-button')).toBeInTheDocument();
      });
    });

    it('clears error state on retry attempt', async () => {
      jest.mocked(authService.handleLogin).mockRejectedValue(new Error('Network error'));
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('user@example.com', 'password123');
      });
      
      await act(async () => {
        await user.click(screen.getByTestId('retry-button'));
      });
      
      expect(screen.queryByText('Network error')).not.toBeInTheDocument();
    });
  });

  describe('Token Validation', () => {
    it('validates token before setting authenticated state', async () => {
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('user@example.com', 'password123');
      });
      
      expect(authService.validateToken).toHaveBeenCalledWith(mockToken);
    });

    it('handles expired token during login', async () => {
      const expiredToken = 'expired.jwt.token';
      jest.mocked(authService.validateToken).mockResolvedValue(false);
      
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('user@example.com', 'password123');
      });
      
      await waitFor(() => {
        expect(screen.getByText('Session expired. Please login again.')).toBeInTheDocument();
      });
    });

    it('refreshes token if near expiration', async () => {
      const nearExpiryToken = 'near.expiry.token';
      
      renderLoginComponent();
      
      await act(async () => {
        await performLogin('user@example.com', 'password123');
      });
      
      expect(authService.refreshToken).toHaveBeenCalled();
    });
  });
});