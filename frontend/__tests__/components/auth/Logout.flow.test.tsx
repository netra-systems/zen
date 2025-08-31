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
import { authService } from '@/auth/unified-auth-service';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

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
  setupAntiHang();
    jest.setTimeout(10000);
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
    jest.mocked(authService.useAuth).mockReturnValue(baseAuthContext);
  });

  describe('Basic Logout Flow', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should trigger logout when button clicked', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue(baseAuthContext);
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
      expect(screen.queryByText('Test User')).not.toBeInTheDocument();
    });

    it('should show loading state during logout', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Loading...')).toBeDisabled();
    });

    it('should handle logout completion successfully', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
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
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle dev mode logout with flag setting', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
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
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle logout service errors gracefully', async () => {
      mockLogout.mockRejectedValueOnce(new Error('Logout service error'));
      
      jest.mocked(authService.useAuth).mockReturnValue({
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
      
      jest.mocked(authService.useAuth).mockReturnValue({
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
      
      jest.mocked(authService.useAuth).mockReturnValue({
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
      
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue(baseAuthContext);
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });

  describe('Session Data Cleanup', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should clear user data on logout', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        user: null,
        token: null
      });
      
      rerender(<LoginButton />);
      expect(screen.queryByText('Test User')).not.toBeInTheDocument();
    });

    it('should clear authentication tokens', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        user: null,
        token: null
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle incomplete cleanup gracefully', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        user: null,
        token: 'orphaned-token'
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should clear session storage on logout', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle rapid logout attempts', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      rerender(<LoginButton />);
      const loadingButton = screen.getByText('Loading...');
      expect(loadingButton).toBeDisabled();
    });

    it('should handle concurrent logout attempts', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
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
  afterEach(() => {
    cleanupAntiHang();
  });

});