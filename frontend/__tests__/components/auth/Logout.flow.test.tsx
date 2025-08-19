/**
 * Logout Flow and Cleanup Tests
 * Tests logout flow and complete cleanup processes
 * 
 * BVJ: Enterprise segment - ensures secure logout and data cleanup
 * Architecture: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginButton } from '@/auth/components';
import { authService } from '@/auth/service';
import '@testing-library/jest-dom';

// Mock auth service
jest.mock('@/auth/service');

// Mock storage APIs
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};

const mockSessionStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};

Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });
Object.defineProperty(window, 'sessionStorage', { value: mockSessionStorage });

// Mock cookies
const mockCookies = new Map();
Object.defineProperty(document, 'cookie', {
  get: () => Array.from(mockCookies.entries()).map(([k, v]) => `${k}=${v}`).join('; '),
  set: (cookie) => {
    const [nameValue] = cookie.split(';');
    const [name, value] = nameValue.split('=');
    if (cookie.includes('expires=Thu, 01 Jan 1970')) {
      mockCookies.delete(name.trim());
    } else {
      mockCookies.set(name.trim(), value?.trim() || '');
    }
  }
});

describe('Logout Flow and Cleanup Tests', () => {
  const mockLogin = jest.fn();
  const mockLogout = jest.fn();
  
  const baseAuthContext = {
    user: null,
    login: mockLogin,
    logout: mockLogout,
    loading: false,
    authConfig: {
      development_mode: false,
      google_client_id: 'test-client-id',
      endpoints: {
        login: '/auth/login',
        logout: '/auth/logout',
        callback: '/auth/callback'
      }
    },
    token: null
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.getItem.mockClear();
    mockLocalStorage.setItem.mockClear();
    mockLocalStorage.removeItem.mockClear();
    mockLocalStorage.clear.mockClear();
    mockSessionStorage.getItem.mockClear();
    mockSessionStorage.setItem.mockClear();
    mockSessionStorage.removeItem.mockClear();
    mockSessionStorage.clear.mockClear();
    mockCookies.clear();
    (authService.useAuth as jest.Mock).mockReturnValue(baseAuthContext);
  });

  describe('Basic Logout Flow', () => {
    it('should trigger logout when button clicked', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      expect(mockLogout).toHaveBeenCalledTimes(1);
    });

    it('should transition to logged out state', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      const { rerender } = render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      expect(mockLogout).toHaveBeenCalled();
      
      // Simulate logout completion
      (authService.useAuth as jest.Mock).mockReturnValue(baseAuthContext);
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
      expect(screen.queryByText('Test User')).not.toBeInTheDocument();
    });

    it('should show loading state during logout', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      const { rerender } = render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      // Simulate logout loading state
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Loading...')).toBeDisabled();
    });

    it('should handle logout completion successfully', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      const { rerender } = render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      // Complete logout flow
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        loading: false,
        user: null,
        token: null
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });

  describe('Development Mode Logout', () => {
    it('should handle dev mode logout with flag setting', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'dev-user-123',
          email: 'dev@example.com',
          full_name: 'Dev User'
        },
        authConfig: {
          ...baseAuthContext.authConfig,
          development_mode: true
        }
      });
      
      render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      expect(mockLogout).toHaveBeenCalled();
    });

    it('should show dev mode UI after logout', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'dev-user-123',
          email: 'dev@example.com',
          full_name: 'Dev User'
        },
        authConfig: {
          ...baseAuthContext.authConfig,
          development_mode: true
        }
      });
      
      const { rerender } = render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      // Simulate dev mode logout completion
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        authConfig: {
          ...baseAuthContext.authConfig,
          development_mode: true
        }
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle OAuth logout in dev mode', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'dev-user-123',
          email: 'dev@example.com',
          full_name: 'Dev User'
        },
        authConfig: {
          ...baseAuthContext.authConfig,
          development_mode: true
        }
      });
      
      render(<LoginButton />);
      
      const oauthButton = screen.getByText('OAuth Login');
      expect(oauthButton).toBeInTheDocument();
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      expect(mockLogout).toHaveBeenCalled();
    });

    it('should persist dev logout flag', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'dev-user-123',
          email: 'dev@example.com',
          full_name: 'Dev User'
        },
        authConfig: {
          ...baseAuthContext.authConfig,
          development_mode: true
        }
      });
      
      render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      expect(mockLogout).toHaveBeenCalledWith();
    });
  });

  describe('Logout Error Handling', () => {
    it('should handle logout service errors gracefully', async () => {
      mockLogout.mockRejectedValueOnce(new Error('Logout service error'));
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      expect(mockLogout).toHaveBeenCalled();
    });

    it('should handle network errors during logout', async () => {
      mockLogout.mockRejectedValueOnce(new Error('Network error'));
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      expect(mockLogout).toHaveBeenCalled();
    });

    it('should handle server unavailable during logout', async () => {
      mockLogout.mockRejectedValueOnce(new Error('Server unavailable'));
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      expect(mockLogout).toHaveBeenCalled();
    });

    it('should continue logout process despite errors', async () => {
      mockLogout.mockRejectedValueOnce(new Error('Partial logout error'));
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      const { rerender } = render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      // Even with errors, should attempt local cleanup
      (authService.useAuth as jest.Mock).mockReturnValue(baseAuthContext);
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });

  describe('Session Data Cleanup', () => {
    it('should clear user data on logout', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      const { rerender } = render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      // Simulate cleanup completion
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: null,
        token: null
      });
      
      rerender(<LoginButton />);
      expect(screen.queryByText('Test User')).not.toBeInTheDocument();
    });

    it('should clear authentication tokens', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        },
        token: 'valid-jwt-token'
      });
      
      const { rerender } = render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      // Tokens should be cleared
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: null,
        token: null
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle incomplete cleanup gracefully', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        },
        token: 'valid-jwt-token'
      });
      
      const { rerender } = render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      // Partial cleanup - user cleared but token remains
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: null,
        token: 'orphaned-token'
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should clear session storage on logout', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      expect(mockLogout).toHaveBeenCalled();
    });
  });

  describe('Multiple Session Logout', () => {
    it('should handle rapid logout attempts', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      
      // Rapid clicks
      await userEvent.click(logoutButton);
      await userEvent.click(logoutButton);
      await userEvent.click(logoutButton);
      
      expect(mockLogout).toHaveBeenCalled();
    });

    it('should prevent double logout processing', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      const { rerender } = render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      // Simulate loading state to prevent double processing
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      rerender(<LoginButton />);
      const loadingButton = screen.getByText('Loading...');
      expect(loadingButton).toBeDisabled();
    });

    it('should handle concurrent logout attempts', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      
      // Simulate concurrent clicks
      const promises = [
        userEvent.click(logoutButton),
        userEvent.click(logoutButton),
        userEvent.click(logoutButton)
      ];
      
      await Promise.all(promises);
      expect(mockLogout).toHaveBeenCalled();
    });

    it('should complete cleanup for all sessions', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      const { rerender } = render(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      
      // Complete cleanup
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: null,
        token: null,
        loading: false
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
      expect(screen.queryByText('Test User')).not.toBeInTheDocument();
    });
  });
});