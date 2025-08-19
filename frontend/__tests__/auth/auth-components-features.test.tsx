/**
 * Auth Components Features Tests
 * Tests edge cases, accessibility, layout, and integration scenarios
 * 
 * BVJ: Enterprise segment - ensures robust component behavior and accessibility
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

describe('Auth Components Features', () => {
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

      expect(screen.queryByText('DEV MODE')).not.toBeInTheDocument();
      expect(screen.getByText('Logout')).toBeInTheDocument();
    });

    it('should handle rapid state changes', () => {
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
    it('should handle complete login flow', () => {
      const { rerender } = render(<LoginButton />);

      const loginButton = screen.getByText('Login with Google');
      fireEvent.click(loginButton);
      expect(mockLogin).toHaveBeenCalled();

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
      expect(screen.getByText('Logout')).toBeInTheDocument();
    });

    it('should handle complete logout flow', () => {
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

      const logoutButton = screen.getByText('Logout');
      fireEvent.click(logoutButton);
      expect(mockLogout).toHaveBeenCalled();

      (authService.useAuth as jest.Mock).mockReturnValue(mockAuthContext);
      rerender(<LoginButton />);

      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });
});