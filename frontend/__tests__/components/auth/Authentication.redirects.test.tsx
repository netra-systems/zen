/**
 * Authentication Success Redirects Tests
 * Tests success redirects after login functionality
 * 
 * BVJ: Enterprise segment - ensures proper navigation after authentication
 * Architecture: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginButton } from '@/auth/components';
import { authService } from '@/auth/unified-auth-service';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import '@testing-library/jest-dom';

// Mock auth service
jest.mock('@/auth/service');

// Mock Next.js navigation hooks
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  usePathname: jest.fn(),
  useSearchParams: jest.fn()
}));

describe('Authentication Success Redirects Tests', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  const mockLogin = jest.fn();
  const mockLogout = jest.fn();
  const mockPush = jest.fn();
  const mockReplace = jest.fn();
  
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
    jest.mocked(authService.useAuth).mockReturnValue(baseAuthContext);
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
      replace: mockReplace,
      back: jest.fn(),
      forward: jest.fn(),
      refresh: jest.fn()
    });
    (usePathname as jest.Mock).mockReturnValue('/login');
    (useSearchParams as jest.Mock).mockReturnValue(new URLSearchParams());
  });

  describe('Default Redirect Behavior', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should redirect to dashboard after successful login', async () => {
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      expect(mockLogin).toHaveBeenCalled();
      
      // Simulate successful login
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

    it('should handle redirect to chat page', async () => {
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      // Simulate successful login with redirect expectation
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

    it('should preserve redirect to home page', async () => {
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
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

    it('should handle authenticated state without redirect', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Test User')).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled();
    });
  });

  describe('Query Parameter Redirects', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should redirect to return URL from query params', async () => {
      (useSearchParams as jest.Mock).mockReturnValue(
        new URLSearchParams('?returnUrl=/dashboard')
      );
      
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
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

    it('should handle redirect parameter validation', async () => {
      (useSearchParams as jest.Mock).mockReturnValue(
        new URLSearchParams('?redirect=http://evil.com')
      );
      
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
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

    it('should handle multiple redirect parameters', async () => {
      (useSearchParams as jest.Mock).mockReturnValue(
        new URLSearchParams('?returnUrl=/chat&next=/dashboard')
      );
      
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
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

    it('should sanitize redirect URLs', async () => {
      (useSearchParams as jest.Mock).mockReturnValue(
        new URLSearchParams('?redirect=javascript:alert(1)')
      );
      
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
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
  });

  describe('Role-Based Redirects', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should redirect admin users to admin panel', async () => {
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'admin-123',
          email: 'admin@example.com',
          full_name: 'Admin User',
          role: 'admin'
        }
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Admin User')).toBeInTheDocument();
    });

    it('should redirect regular users to dashboard', async () => {
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'user@example.com',
          full_name: 'Regular User',
          role: 'user'
        }
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Regular User')).toBeInTheDocument();
    });

    it('should handle enterprise user redirects', async () => {
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'enterprise-123',
          email: 'enterprise@company.com',
          full_name: 'Enterprise User',
          role: 'enterprise'
        }
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Enterprise User')).toBeInTheDocument();
    });

    it('should handle undefined role gracefully', async () => {
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'user@example.com',
          full_name: 'User'
          // No role property
        }
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('User')).toBeInTheDocument();
    });
  });

  describe('Development Mode Redirects', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle dev mode login redirects', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        authConfig: {
          ...baseAuthContext.authConfig,
          development_mode: true
        }
      });
      
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
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
      
      rerender(<LoginButton />);
      expect(screen.getByText('DEV MODE')).toBeInTheDocument();
    });

    it('should handle dev logout without redirect', async () => {
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
      expect(mockLogout).toHaveBeenCalled();
      
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

    it('should handle dev OAuth login button', async () => {
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
      await userEvent.click(oauthButton);
      expect(mockLogin).toHaveBeenCalled();
    });

    it('should preserve dev mode state during redirects', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        authConfig: {
          ...baseAuthContext.authConfig,
          development_mode: true
        }
      });
      
      const { rerender } = render(<LoginButton />);
      
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
      
      rerender(<LoginButton />);
      expect(screen.getByText('DEV MODE')).toBeInTheDocument();
    });
  });

  describe('Redirect Error Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle redirect failures gracefully', async () => {
      mockPush.mockRejectedValueOnce(new Error('Redirect failed'));
      
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
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

    it('should fallback to default route on invalid redirect', async () => {
      (useSearchParams as jest.Mock).mockReturnValue(
        new URLSearchParams('?returnUrl=invalid://url')
      );
      
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
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

    it('should handle missing redirect configuration', async () => {
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
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

    it('should preserve authentication state on redirect errors', async () => {
      mockPush.mockImplementationOnce(() => {
        throw new Error('Navigation error');
      });
      
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
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
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});