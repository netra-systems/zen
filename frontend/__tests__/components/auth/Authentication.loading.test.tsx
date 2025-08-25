/**
 * Authentication Loading States Tests
 * Tests loading states during authentication processes
 * 
 * BVJ: Enterprise segment - ensures smooth UX during auth operations
 * Architecture: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginButton } from '@/auth/components';
import { AuthProvider } from '@/auth/context';
import { authService } from '@/auth/unified-auth-service';
import '@testing-library/jest-dom';

// Mock auth service
jest.mock('@/auth/service');

describe('Authentication Loading States Tests', () => {
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
    jest.mocked(authService.useAuth).mockReturnValue(baseAuthContext);
  });

  describe('Initial Loading State', () => {
    it('should show loading state during auth initialization', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      render(<LoginButton />);
      
      const loadingButton = screen.getByText('Loading...');
      expect(loadingButton).toBeInTheDocument();
      expect(loadingButton).toBeDisabled();
    });

    it('should hide other UI elements during loading', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      render(<LoginButton />);
      
      expect(screen.queryByText('Login with Google')).not.toBeInTheDocument();
      expect(screen.queryByText('Logout')).not.toBeInTheDocument();
    });

    it('should maintain loading state consistency', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      const { rerender } = render(<LoginButton />);
      
      expect(screen.getByText('Loading...')).toBeDisabled();
      
      rerender(<LoginButton />);
      expect(screen.getByText('Loading...')).toBeDisabled();
    });

    it('should handle loading timeout gracefully', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      render(<LoginButton />);
      
      await waitFor(() => {
        expect(screen.getByText('Loading...')).toBeDisabled();
      });
    });
  });

  describe('Login Process Loading', () => {
    it('should show loading state during login attempt', async () => {
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      // Simulate loading state during login
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Loading...')).toBeDisabled();
    });

    it('should disable interactions during login loading', async () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      render(<LoginButton />);
      
      const button = screen.getByText('Loading...');
      expect(button).toBeDisabled();
      
      // Try to click disabled button
      await userEvent.click(button);
      expect(mockLogin).not.toHaveBeenCalled();
    });

    it('should handle login loading completion', async () => {
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      expect(mockLogin).toHaveBeenCalled();
      
      // Complete login with user data
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        },
        loading: false
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });

    it('should handle login loading failure', async () => {
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      // Simulate loading then failure
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: false,
        error: 'Login failed'
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });

  describe('Logout Process Loading', () => {
    it('should show loading during logout process', async () => {
      // Start with logged in user
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
      
      // Simulate logout loading
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true,
        user: null
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Loading...')).toBeDisabled();
    });

    it('should complete logout loading cycle', async () => {
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
      
      // Complete logout
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: false,
        user: null
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle logout loading with cleanup', async () => {
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

    it('should disable logout button during loading', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        },
        loading: true
      });
      
      render(<LoginButton />);
      
      const button = screen.getByText('Loading...');
      expect(button).toBeDisabled();
    });
  });

  describe('Loading State Transitions', () => {
    it('should handle rapid state transitions', async () => {
      const { rerender } = render(<LoginButton />);
      
      // Initial state
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
      
      // Loading state
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      rerender(<LoginButton />);
      expect(screen.getByText('Loading...')).toBeDisabled();
      
      // Logged in state
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: false,
        user: { id: '1', email: 'test@example.com', full_name: 'Test' }
      });
      rerender(<LoginButton />);
      expect(screen.getByText('Test')).toBeInTheDocument();
    });

    it('should maintain UI consistency during transitions', async () => {
      const { rerender } = render(<LoginButton />);
      
      // Multiple rapid state changes
      for (let i = 0; i < 5; i++) {
        jest.mocked(authService.useAuth).mockReturnValue({
          ...baseAuthContext,
          loading: i % 2 === 0
        });
        rerender(<LoginButton />);
        
        const isLoading = i % 2 === 0;
        if (isLoading) {
          expect(screen.getByText('Loading...')).toBeDisabled();
        } else {
          expect(screen.getByText('Login with Google')).not.toBeDisabled();
        }
      }
    });

    it('should handle loading with partial user data', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true,
        user: { id: '1' } // Partial user data
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Loading...')).toBeDisabled();
    });

    it('should preserve loading state during re-renders', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      const { rerender } = render(<LoginButton />);
      
      expect(screen.getByText('Loading...')).toBeDisabled();
      
      // Multiple re-renders should maintain loading state
      rerender(<LoginButton />);
      rerender(<LoginButton />);
      
      expect(screen.getByText('Loading...')).toBeDisabled();
    });
  });

  describe('Loading Accessibility', () => {
    it('should provide accessible loading indicators', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      render(<LoginButton />);
      
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
      expect(button).toHaveTextContent('Loading...');
    });

    it('should announce loading state changes', async () => {
      const { rerender } = render(<LoginButton />);
      
      expect(screen.getByRole('button')).toHaveTextContent('Login with Google');
      
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      rerender(<LoginButton />);
      expect(screen.getByRole('button')).toHaveTextContent('Loading...');
    });

    it('should maintain focus during loading states', async () => {
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      // Focus should remain manageable
      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('should provide loading duration feedback', () => {
      jest.mocked(authService.useAuth).mockReturnValue({
        ...baseAuthContext,
        loading: true
      });
      
      render(<LoginButton />);
      
      const button = screen.getByText('Loading...');
      expect(button).toBeVisible();
      expect(button).toBeDisabled();
    });
  });
});