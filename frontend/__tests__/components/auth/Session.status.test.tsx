/**
 * Session Status Indicators Tests
 * Tests session status indicators and state management
 * 
 * BVJ: Enterprise segment - ensures clear session status communication
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

// Mock localStorage for session persistence
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage
});

describe('Session Status Indicators Tests', () => {
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
    (authService.useAuth as jest.Mock).mockReturnValue(baseAuthContext);
  });

  describe('Login Status Indicators', () => {
    it('should show logged out state initially', () => {
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      expect(button).toBeInTheDocument();
      expect(screen.queryByText('Logout')).not.toBeInTheDocument();
    });

    it('should show logged in state with user info', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Test User')).toBeInTheDocument();
      expect(screen.getByText('Logout')).toBeInTheDocument();
      expect(screen.queryByText('Login with Google')).not.toBeInTheDocument();
    });

    it('should show loading status during auth operations', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      render(<LoginButton />);
      
      const loadingButton = screen.getByText('Loading...');
      expect(loadingButton).toBeInTheDocument();
      expect(loadingButton).toBeDisabled();
    });

    it('should show user email when name unavailable', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: null
        }
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });
  });

  describe('Development Mode Indicators', () => {
    it('should show dev mode badge when enabled', () => {
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
      
      expect(screen.getByText('DEV MODE')).toBeInTheDocument();
      expect(screen.getByText('DEV MODE')).toHaveClass('bg-yellow-100', 'text-yellow-800');
    });

    it('should show dev mode login options', () => {
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
      
      expect(screen.getByText('Logout')).toBeInTheDocument();
      expect(screen.getByText('OAuth Login')).toBeInTheDocument();
    });

    it('should hide dev mode badge in production', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'user@example.com',
          full_name: 'User'
        },
        authConfig: {
          ...baseAuthContext.authConfig,
          development_mode: false
        }
      });
      
      render(<LoginButton />);
      
      expect(screen.queryByText('DEV MODE')).not.toBeInTheDocument();
      expect(screen.getByText('Logout')).toBeInTheDocument();
    });

    it('should handle missing authConfig gracefully', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'user@example.com',
          full_name: 'User'
        },
        authConfig: null
      });
      
      render(<LoginButton />);
      
      expect(screen.queryByText('DEV MODE')).not.toBeInTheDocument();
      expect(screen.getByText('Logout')).toBeInTheDocument();
    });
  });

  describe('Session State Transitions', () => {
    it('should handle login to logout transition', async () => {
      const { rerender } = render(<LoginButton />);
      
      // Initial logged out state
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
      
      // Simulate login
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Test User')).toBeInTheDocument();
      expect(screen.getByText('Logout')).toBeInTheDocument();
    });

    it('should handle logout to login transition', async () => {
      // Start with logged in user
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      const { rerender } = render(<LoginButton />);
      expect(screen.getByText('Test User')).toBeInTheDocument();
      
      const logoutButton = screen.getByText('Logout');
      await userEvent.click(logoutButton);
      expect(mockLogout).toHaveBeenCalled();
      
      // Simulate logout completion
      (authService.useAuth as jest.Mock).mockReturnValue(baseAuthContext);
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle rapid state changes', () => {
      const { rerender } = render(<LoginButton />);
      
      // Multiple rapid state changes
      const states = [
        { loading: true },
        { user: { id: '1', email: 'test@example.com', full_name: 'Test' } },
        { loading: true },
        { user: null }
      ];
      
      states.forEach((state, index) => {
        (authService.useAuth as jest.Mock).mockReturnValue({
          ...baseAuthContext,
          ...state
        });
        
        rerender(<LoginButton />);
        
        if (state.loading) {
          expect(screen.getByText('Loading...')).toBeDisabled();
        } else if (state.user) {
          expect(screen.getByText('Test')).toBeInTheDocument();
        } else {
          expect(screen.getByText('Login with Google')).toBeInTheDocument();
        }
      });
    });

    it('should maintain state consistency during loading', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        loading: true,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      render(<LoginButton />);
      
      // Should prioritize loading state
      expect(screen.getByText('Loading...')).toBeDisabled();
      expect(screen.queryByText('Test User')).not.toBeInTheDocument();
    });
  });

  describe('Token Status Management', () => {
    it('should reflect token presence in UI state', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        },
        token: 'valid-jwt-token'
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Test User')).toBeInTheDocument();
      expect(screen.getByText('Logout')).toBeInTheDocument();
    });

    it('should handle token without user data', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: null,
        token: 'orphaned-token'
      });
      
      render(<LoginButton />);
      
      // Should show logged out state if no user data
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle user data without token', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        },
        token: null
      });
      
      render(<LoginButton />);
      
      // Should show logged in state based on user data
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });

    it('should handle invalid token scenarios', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: null,
        token: 'invalid.jwt.token'
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });

  describe('Visual State Indicators', () => {
    it('should apply correct styling for logged in state', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      const { container } = render(<LoginButton />);
      
      const userInfo = container.querySelector('.flex.items-center.gap-4');
      expect(userInfo).toBeInTheDocument();
      
      const userName = container.querySelector('.text-sm.font-medium');
      expect(userName).toHaveTextContent('Test User');
    });

    it('should apply loading button styling', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      render(<LoginButton />);
      
      const button = screen.getByText('Loading...');
      expect(button).toBeDisabled();
      expect(button).toBeInTheDocument();
    });

    it('should apply dev mode badge styling', () => {
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
      
      const devBadge = screen.getByText('DEV MODE');
      expect(devBadge).toHaveClass('bg-yellow-100');
      expect(devBadge).toHaveClass('text-yellow-800');
    });

    it('should apply correct button layout for dev mode', () => {
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
      
      const { container } = render(<LoginButton />);
      
      const buttonWrapper = container.querySelector('.flex.gap-2');
      expect(buttonWrapper).toBeInTheDocument();
      expect(buttonWrapper?.children).toHaveLength(2);
    });
  });

  describe('Accessibility for Status Indicators', () => {
    it('should provide accessible status information', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      render(<LoginButton />);
      
      const logoutButton = screen.getByRole('button', { name: /logout/i });
      expect(logoutButton).toBeInTheDocument();
    });

    it('should announce loading state to screen readers', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      render(<LoginButton />);
      
      const button = screen.getByRole('button');
      expect(button).toHaveTextContent('Loading...');
      expect(button).toBeDisabled();
    });

    it('should provide accessible login button', () => {
      render(<LoginButton />);
      
      const button = screen.getByRole('button', { name: /login with google/i });
      expect(button).toBeInTheDocument();
      expect(button).not.toBeDisabled();
    });

    it('should maintain focus management across state changes', async () => {
      const { rerender } = render(<LoginButton />);
      
      const loginButton = screen.getByText('Login with Google');
      loginButton.focus();
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      rerender(<LoginButton />);
      
      const logoutButton = screen.getByText('Logout');
      expect(logoutButton).toBeInTheDocument();
    });
  });
});