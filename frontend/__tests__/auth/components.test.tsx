/**
 * AI AGENT MODIFICATION METADATA
 * ================================
 * Timestamp: 2025-08-11T18:10:00Z
 * Agent: Claude Opus 4.1 (claude-opus-4-1-20250805) via claude-code
 * Context: Create comprehensive test suite for auth/components.tsx with 100% coverage
 * Git: v7 | feature-auth-tests | dirty
 * Change: Test | Scope: Auth | Risk: Low
 * Session: auth-test-improvement | Seq: 3
 * Review: Pending | Score: 95/100
 * ================================
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LoginButton } from '@/auth/components';
import { authService } from '@/auth/service';
import '@testing-library/jest-dom';

// Mock auth service
jest.mock('@/auth/service');

// Mock UI components
jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, disabled, variant, size, ...props }: any) => (
    <button 
      onClick={onClick} 
      disabled={disabled}
      data-variant={variant}
      data-size={size}
      {...props}
    >
      {children}
    </button>
  )
}));

jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, variant, className }: any) => (
    <span data-variant={variant} className={className}>
      {children}
    </span>
  )
}));

describe('LoginButton Component', () => {
  const mockLogin = jest.fn();
  const mockLogout = jest.fn();
  
  const mockAuthContext = {
    user: null,
    login: mockLogin,
    logout: mockLogout,
    loading: false,
    authConfig: null,
    token: null
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (authService.useAuth as jest.Mock).mockReturnValue(mockAuthContext);
  });

  describe('Loading State', () => {
    it('should render loading state when loading is true', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        loading: true
      });

      render(<LoginButton />);

      const button = screen.getByRole('button');
      expect(button).toHaveTextContent('Loading...');
      expect(button).toBeDisabled();
    });

    it('should not be clickable when loading', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        loading: true
      });

      render(<LoginButton />);

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(mockLogin).not.toHaveBeenCalled();
      expect(mockLogout).not.toHaveBeenCalled();
    });
  });

  describe('Logged Out State', () => {
    it('should render login button when user is not authenticated', () => {
      render(<LoginButton />);

      const button = screen.getByRole('button');
      expect(button).toHaveTextContent('Login with Google');
      expect(button).toHaveAttribute('data-size', 'lg');
    });

    it('should call login function when login button is clicked', () => {
      render(<LoginButton />);

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(mockLogin).toHaveBeenCalledTimes(1);
    });

    it('should render correctly with null auth config', () => {
      render(<LoginButton />);

      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });

  describe('Logged In State - Production Mode', () => {
    const mockUser = {
      id: 'user-123',
      email: 'test@example.com',
      full_name: 'Test User'
    };

    beforeEach(() => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        user: mockUser,
        authConfig: {
          development_mode: false,
          endpoints: {}
        }
      });
    });

    it('should display user name when authenticated', () => {
      render(<LoginButton />);

      expect(screen.getByText('Test User')).toBeInTheDocument();
    });

    it('should display email when full_name is not available', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        user: { ...mockUser, full_name: null },
        authConfig: {
          development_mode: false,
          endpoints: {}
        }
      });

      render(<LoginButton />);

      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });

    it('should render logout button in production mode', () => {
      render(<LoginButton />);

      const logoutButton = screen.getByText('Logout');
      expect(logoutButton).toBeInTheDocument();
      expect(logoutButton.parentElement).not.toHaveAttribute('data-variant', 'outline');
    });

    it('should call logout function when logout button is clicked', () => {
      render(<LoginButton />);

      const logoutButton = screen.getByText('Logout');
      fireEvent.click(logoutButton);

      expect(mockLogout).toHaveBeenCalledTimes(1);
    });

    it('should not show DEV MODE badge in production', () => {
      render(<LoginButton />);

      expect(screen.queryByText('DEV MODE')).not.toBeInTheDocument();
    });
  });

  describe('Logged In State - Development Mode', () => {
    const mockUser = {
      id: 'user-123',
      email: 'dev@example.com',
      full_name: 'Dev User'
    };

    beforeEach(() => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        user: mockUser,
        authConfig: {
          development_mode: true,
          endpoints: {}
        }
      });
    });

    it('should show DEV MODE badge in development mode', () => {
      render(<LoginButton />);

      const badge = screen.getByText('DEV MODE');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
      expect(badge).toHaveAttribute('data-variant', 'secondary');
    });

    it('should render both logout and OAuth login buttons in dev mode', () => {
      render(<LoginButton />);

      expect(screen.getByText('Logout')).toBeInTheDocument();
      expect(screen.getByText('OAuth Login')).toBeInTheDocument();
    });

    it('should style logout button as outline variant in dev mode', () => {
      render(<LoginButton />);

      const logoutButton = screen.getByText('Logout');
      expect(logoutButton).toHaveAttribute('data-variant', 'outline');
      expect(logoutButton).toHaveAttribute('data-size', 'sm');
    });

    it('should style OAuth login button as default variant in dev mode', () => {
      render(<LoginButton />);

      const oauthButton = screen.getByText('OAuth Login');
      expect(oauthButton).toHaveAttribute('data-variant', 'default');
      expect(oauthButton).toHaveAttribute('data-size', 'sm');
    });

    it('should call logout when dev logout button is clicked', () => {
      render(<LoginButton />);

      const logoutButton = screen.getByText('Logout');
      fireEvent.click(logoutButton);

      expect(mockLogout).toHaveBeenCalledTimes(1);
    });

    it('should call login when OAuth login button is clicked in dev mode', () => {
      render(<LoginButton />);

      const oauthButton = screen.getByText('OAuth Login');
      fireEvent.click(oauthButton);

      expect(mockLogin).toHaveBeenCalledTimes(1);
    });
  });

  describe('Edge Cases', () => {
    it('should handle user with no name or email', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        user: {
          id: 'user-123',
          email: null,
          full_name: null
        },
        authConfig: {
          development_mode: false,
          endpoints: {}
        }
      });

      render(<LoginButton />);

      // Should still render the component without crashing
      expect(screen.getByText('Logout')).toBeInTheDocument();
    });

    it('should handle undefined auth config gracefully', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        },
        authConfig: undefined
      });

      render(<LoginButton />);

      // Should not show DEV MODE badge when config is undefined
      expect(screen.queryByText('DEV MODE')).not.toBeInTheDocument();
      // Should show regular logout button
      expect(screen.getByText('Logout')).toBeInTheDocument();
    });

    it('should handle rapid state changes', () => {
      const { rerender } = render(<LoginButton />);

      // Initially logged out
      expect(screen.getByText('Login with Google')).toBeInTheDocument();

      // Change to logged in
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        },
        authConfig: {
          development_mode: false,
          endpoints: {}
        }
      });
      rerender(<LoginButton />);
      expect(screen.getByText('Test User')).toBeInTheDocument();

      // Change to loading
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        loading: true
      });
      rerender(<LoginButton />);
      expect(screen.getByText('Loading...')).toBeInTheDocument();

      // Back to logged out
      (authService.useAuth as jest.Mock).mockReturnValue(mockAuthContext);
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle empty string user names', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: ''
        },
        authConfig: {
          development_mode: false,
          endpoints: {}
        }
      });

      render(<LoginButton />);

      // Should fall back to email when full_name is empty string
      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible button roles', () => {
      render(<LoginButton />);

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('should properly disable button when loading', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        loading: true
      });

      render(<LoginButton />);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('disabled');
    });

    it('should have proper button text for screen readers', () => {
      render(<LoginButton />);

      expect(screen.getByRole('button')).toHaveTextContent('Login with Google');
    });
  });

  describe('Layout and Styling', () => {
    it('should apply correct layout classes for logged in state', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        },
        authConfig: {
          development_mode: false,
          endpoints: {}
        }
      });

      const { container } = render(<LoginButton />);

      const wrapper = container.querySelector('.flex.items-center.gap-4');
      expect(wrapper).toBeInTheDocument();
    });

    it('should apply correct text styling for user name', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        },
        authConfig: {
          development_mode: false,
          endpoints: {}
        }
      });

      const { container } = render(<LoginButton />);

      const userName = container.querySelector('.text-sm.font-medium');
      expect(userName).toHaveTextContent('Test User');
    });

    it('should apply correct layout for dev mode buttons', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        user: {
          id: 'user-123',
          email: 'dev@example.com',
          full_name: 'Dev User'
        },
        authConfig: {
          development_mode: true,
          endpoints: {}
        }
      });

      const { container } = render(<LoginButton />);

      const buttonWrapper = container.querySelector('.flex.gap-2');
      expect(buttonWrapper).toBeInTheDocument();
      expect(buttonWrapper?.children).toHaveLength(2);
    });
  });

  describe('Integration Tests', () => {
    it('should handle complete login flow', async () => {
      const { rerender } = render(<LoginButton />);

      // Initial state - logged out
      const loginButton = screen.getByText('Login with Google');
      fireEvent.click(loginButton);
      expect(mockLogin).toHaveBeenCalled();

      // Simulate successful login
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        },
        authConfig: {
          development_mode: false,
          endpoints: {}
        }
      });
      rerender(<LoginButton />);

      // Verify logged in state
      expect(screen.getByText('Test User')).toBeInTheDocument();
      expect(screen.getByText('Logout')).toBeInTheDocument();
    });

    it('should handle complete logout flow', async () => {
      // Start logged in
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        },
        authConfig: {
          development_mode: false,
          endpoints: {}
        }
      });

      const { rerender } = render(<LoginButton />);

      // Click logout
      const logoutButton = screen.getByText('Logout');
      fireEvent.click(logoutButton);
      expect(mockLogout).toHaveBeenCalled();

      // Simulate successful logout
      (authService.useAuth as jest.Mock).mockReturnValue(mockAuthContext);
      rerender(<LoginButton />);

      // Verify logged out state
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });
});