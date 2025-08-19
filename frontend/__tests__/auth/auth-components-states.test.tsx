/**
 * Auth Components State Tests
 * Tests loading, logged out, and logged in states
 * 
 * BVJ: Enterprise segment - ensures reliable UI states for auth components
 * Architecture: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { LoginButton } from '@/auth/components';
import { authService } from '@/auth/service';
import '@testing-library/jest-dom';

// Mock auth service
jest.mock('@/auth/service');

// Import real UI components
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

describe('Auth Components States', () => {
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

  describe('State Transitions', () => {
    it('should handle state change from loading to logged out', () => {
      const { rerender } = render(<LoginButton />);

      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        loading: true
      });
      rerender(<LoginButton />);
      expect(screen.getByText('Loading...')).toBeInTheDocument();

      (authService.useAuth as jest.Mock).mockReturnValue(mockAuthContext);
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle state change from logged out to logged in', () => {
      const { rerender } = render(<LoginButton />);

      expect(screen.getByText('Login with Google')).toBeInTheDocument();

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
    });

    it('should handle development mode toggle', () => {
      const { rerender } = render(<LoginButton />);

      (authService.useAuth as jest.Mock).mockReturnValue({
        ...mockAuthContext,
        user: {
          id: 'user-123',
          email: 'dev@example.com',
          full_name: 'Dev User'
        },
        authConfig: {
          development_mode: false,
          endpoints: {}
        }
      });
      rerender(<LoginButton />);
      expect(screen.queryByText('DEV MODE')).not.toBeInTheDocument();

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
      rerender(<LoginButton />);
      expect(screen.getByText('DEV MODE')).toBeInTheDocument();
    });
  });
});