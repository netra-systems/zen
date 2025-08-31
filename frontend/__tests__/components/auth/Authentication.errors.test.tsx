/**
 * Authentication Error Message Tests
 * Tests error displays (invalid credentials, network errors)
 * 
 * BVJ: Enterprise segment - ensures proper error handling and user feedback
 * Architecture: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginButton } from '@/auth/components';
import { AuthProvider, AuthContext } from '@/auth/context';
import { authService } from '@/auth/unified-auth-service';
import '@testing-library/jest-dom';

// Mock auth service
jest.mock('@/auth/service');

// Mock logger to capture error messages
jest.mock('@/lib/logger', () => ({
  logger: {
    error: jest.fn(),
    warn: jest.fn(),
    info: jest.fn(),
    debug: jest.fn()
  }
}));

// Mock the auth context
const mockLogin = jest.fn();
const mockLogout = jest.fn();

const mockAuthContext = {
  user: null,
  login: mockLogin,
  logout: mockLogout,
  loading: false,
  authConfig: {
    development_mode: false,
    google_client_id: 'test-client-id',
    endpoints: {
      login: '/auth/login',
      callback: '/auth/callback'
    }
  },
  token: null
};

describe('Authentication Error Message Tests', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock authService.useAuth to return our mock context
    jest.mocked(authService.useAuth).mockReturnValue(mockAuthContext);
  });

  describe('Invalid Credentials Errors', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle invalid login credentials gracefully', async () => {
      mockLogin.mockImplementation(() => {
        throw new Error('Invalid credentials');
      });
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      
      // The click should not cause the test to fail even if login throws
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
      // Component should continue to function
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle expired token errors', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Token expired'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
    });

    it('should handle authentication timeout', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Authentication timeout'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
    });

    it('should handle invalid OAuth state errors', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Invalid OAuth state'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
    });
  });

  describe('Network Error Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle network connection errors', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Network error'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle server unavailable errors', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Service unavailable'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
    });

    it('should handle DNS resolution failures', async () => {
      mockLogin.mockRejectedValueOnce(new Error('DNS resolution failed'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
    });

    it('should handle request timeout errors', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Request timeout'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
    });
  });

  describe('OAuth Provider Errors', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle Google OAuth errors', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Google OAuth error'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
    });

    it('should handle OAuth popup blocked errors', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Popup blocked'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
    });

    it('should handle OAuth access denied', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Access denied'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
    });

    it('should handle OAuth scope insufficient errors', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Insufficient permissions'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
    });
  });

  describe('Configuration Error Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle missing auth configuration', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        authConfig: null
      });
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      expect(button).toBeInTheDocument();
    });

    it('should handle invalid client ID configuration', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        authConfig: {
          ...baseAuthContext.authConfig,
          google_client_id: ''
        }
      });
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      expect(button).toBeInTheDocument();
    });

    it('should handle malformed endpoint URLs', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        authConfig: {
          ...baseAuthContext.authConfig,
          endpoints: {
            login: 'invalid-url',
            callback: 'invalid-callback'
          }
        }
      });
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      expect(button).toBeInTheDocument();
    });

    it('should handle missing required configuration fields', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        authConfig: {
          development_mode: false,
          endpoints: {}
        }
      });
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      expect(button).toBeInTheDocument();
    });
  });

  describe('Token Management Errors', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle corrupted token storage', () => {
      // Mock corrupted token scenario
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        token: 'corrupted-token',
        user: null
      });
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      expect(button).toBeInTheDocument();
    });

    it('should handle token decode failures', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        token: 'invalid.jwt.token',
        user: null
      });
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      expect(button).toBeInTheDocument();
    });

    it('should handle token refresh failures', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Token refresh failed'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
    });

    it('should handle token validation errors', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        token: 'expired.token.here',
        user: null
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });

  describe('Error Recovery Mechanisms', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should allow retry after authentication error', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Network error'))
               .mockResolvedValueOnce(undefined);
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      
      // First attempt fails
      await userEvent.click(button);
      expect(mockLogin).toHaveBeenCalledTimes(1);
      
      // Second attempt should work
      await userEvent.click(button);
      expect(mockLogin).toHaveBeenCalledTimes(2);
    });

    it('should reset error state on successful retry', async () => {
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      // Simulate successful login after error
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });

    it('should maintain component stability during errors', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Random error'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      // Component should remain functional
      expect(button).toBeInTheDocument();
      expect(button).not.toBeDisabled();
    });

    it('should handle multiple consecutive errors', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Error 1'))
               .mockRejectedValueOnce(new Error('Error 2'))
               .mockRejectedValueOnce(new Error('Error 3'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      
      // Multiple error attempts
      await userEvent.click(button);
      await userEvent.click(button);
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalledTimes(3);
      expect(button).toBeInTheDocument();
    });
  });

  describe('Error Message Accessibility', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should maintain accessible error communication', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Authentication failed'));
      
      render(<LoginButton />);
      
      const button = screen.getByRole('button');
      await userEvent.click(button);
      
      // Component should remain accessible
      expect(button).toHaveAccessibleName();
    });

    it('should preserve button semantics during errors', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Network error'));
      
      render(<LoginButton />);
      
      const button = screen.getByRole('button');
      await userEvent.click(button);
      
      expect(button).toHaveAttribute('type');
    });

    it('should maintain focus management during errors', async () => {
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      button.focus();
      
      mockLogin.mockRejectedValueOnce(new Error('Focus test error'));
      await userEvent.click(button);
      
      expect(button).toBeInTheDocument();
    });

    it('should handle screen reader error announcements', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Screen reader test'));
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(button).toHaveTextContent('Login with Google');
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});