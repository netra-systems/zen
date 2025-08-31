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
import { authService } from '@/auth/unified-auth-service';
import '@testing-library/jest-dom';

// Mock auth service for component testing
jest.mock('@/auth/service');

// Import real UI components
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

describe('Auth Components Features', () => {
      setupAntiHang();
    jest.setTimeout(10000);
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
    jest.mocked(authService.useAuth).mockReturnValue(mockAuthContext);
  });

  describe('Edge Cases', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle user with no name or email', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
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

      jest.mocked(authService.useAuth).mockReturnValue({
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

      jest.mocked(authService.useAuth).mockReturnValue({
        ...mockAuthContext,
        loading: true
      });
      rerender(<LoginButton />);
      expect(screen.getByText('Loading...')).toBeInTheDocument();

      jest.mocked(authService.useAuth).mockReturnValue(mockAuthContext);
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle empty string user names', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
        setupAntiHang();
      jest.setTimeout(10000);
    it('should have accessible button roles', () => {
      render(<LoginButton />);

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('should properly disable button when loading', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
        setupAntiHang();
      jest.setTimeout(10000);
    it('should apply correct layout classes for logged in state', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
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
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle complete login flow', () => {
      const { rerender } = render(<LoginButton />);

      const loginButton = screen.getByText('Login with Google');
      fireEvent.click(loginButton);
      expect(mockLogin).toHaveBeenCalled();

      jest.mocked(authService.useAuth).mockReturnValue({
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
      jest.mocked(authService.useAuth).mockReturnValue({
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

      jest.mocked(authService.useAuth).mockReturnValue(mockAuthContext);
      rerender(<LoginButton />);

      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});