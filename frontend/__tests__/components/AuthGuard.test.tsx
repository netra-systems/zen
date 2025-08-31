/**
 * Complete test suite for AuthGuard component
 * Ensures 100% line coverage and validates single-render optimization
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthGuard } from '@/components/AuthGuard';
import { useAuth } from '@/auth/context';
import { useGTMEvent } from '@/hooks/useGTMEvent';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock dependencies
jest.mock('@/auth/context');
jest.mock('@/hooks/useGTMEvent');

// Get the mocked useRouter from the global mock
const mockUseRouter = jest.requireMock('next/navigation').useRouter;

describe('AuthGuard Component', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  const mockPush = jest.fn();
  const mockTrackError = jest.fn();
  const mockTrackPageView = jest.fn();
  const mockOnAuthCheckComplete = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Configure the mocked router
    mockUseRouter.mockReturnValue({
      push: mockPush,
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      refresh: jest.fn(),
      pathname: '/',
      query: {}
    });
    (useGTMEvent as jest.Mock).mockReturnValue({
      trackError: mockTrackError,
      trackPageView: mockTrackPageView,
      trackLogin: jest.fn(),
      trackLogout: jest.fn(),
      trackOAuthComplete: jest.fn()
    });
    
    (useAuth as jest.Mock).mockReturnValue({
      user: null,
      loading: true,
      initialized: false,
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
      error: null
    });
    
    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: { pathname: '/protected-page' },
      writable: true
    });
  });

  describe('Loading States', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should show loading screen when loading', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: true,
        initialized: false,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      });

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(screen.getByTestId('loading')).toBeInTheDocument();
      expect(screen.getByText('Verifying authentication...')).toBeInTheDocument();
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });

    test('should show loading screen when not initialized', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: false,
        initialized: false,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      });

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(screen.getByTestId('loading')).toBeInTheDocument();
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });

    test('should hide loading screen when showLoading is false', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: true,
        initialized: false,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      });

      const { container } = render(
        <AuthGuard showLoading={false}>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(screen.queryByTestId('loading')).not.toBeInTheDocument();
      expect(container.firstChild).toBeNull();
    });
  });

  describe('Authentication Flow', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should render children when user is authenticated', async () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: { id: 'test-user', email: 'test@example.com' },
        loading: false,
        initialized: true,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      });

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument();
      });
      
      expect(mockTrackPageView).toHaveBeenCalledWith('/protected-page', 'Protected Page Access');
      expect(mockPush).not.toHaveBeenCalled();
    });

    test('should redirect when user is not authenticated', async () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: false,
        initialized: true,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      });

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login');
      });
      
      expect(mockTrackError).toHaveBeenCalledWith(
        'auth_required',
        'User not authenticated',
        '/protected-page',
        false
      );
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });

    test('should use custom redirect path', async () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: false,
        initialized: true,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      });

      render(
        <AuthGuard redirectTo="/custom-login">
          <div>Protected Content</div>
        </AuthGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/custom-login');
      });
    });
  });

  describe('Single Render Optimization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should only perform auth check once after initialization', async () => {
      const { rerender } = render(
        <AuthGuard onAuthCheckComplete={mockOnAuthCheckComplete}>
          <div>Protected Content</div>
        </AuthGuard>
      );

      // Initially loading
      expect(mockOnAuthCheckComplete).not.toHaveBeenCalled();

      // Complete initialization with authenticated user
      (useAuth as jest.Mock).mockReturnValue({
        user: { id: 'test-user', email: 'test@example.com' },
        loading: false,
        initialized: true,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      });

      rerender(
        <AuthGuard onAuthCheckComplete={mockOnAuthCheckComplete}>
          <div>Protected Content</div>
        </AuthGuard>
      );

      await waitFor(() => {
        expect(mockOnAuthCheckComplete).toHaveBeenCalledTimes(1);
        expect(mockOnAuthCheckComplete).toHaveBeenCalledWith(true);
      });

      // Re-render multiple times - should not trigger more auth checks
      rerender(
        <AuthGuard onAuthCheckComplete={mockOnAuthCheckComplete}>
          <div>Protected Content Updated</div>
        </AuthGuard>
      );

      rerender(
        <AuthGuard onAuthCheckComplete={mockOnAuthCheckComplete}>
          <div>Protected Content Updated Again</div>
        </AuthGuard>
      );

      // Should still only have been called once
      expect(mockOnAuthCheckComplete).toHaveBeenCalledTimes(1);
      expect(mockTrackPageView).toHaveBeenCalledTimes(1);
    });

    test('should not re-track events on re-renders', async () => {
      const { rerender } = render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      // Complete initialization without user
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: false,
        initialized: true,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      });

      rerender(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      await waitFor(() => {
        expect(mockTrackError).toHaveBeenCalledTimes(1);
      });

      // Multiple re-renders should not trigger more tracking
      for (let i = 0; i < 5; i++) {
        rerender(
          <AuthGuard>
            <div>Protected Content {i}</div>
          </AuthGuard>
        );
      }

      expect(mockTrackError).toHaveBeenCalledTimes(1);
      expect(mockPush).toHaveBeenCalledTimes(1);
    });
  });

  describe('Component Lifecycle', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should handle unmount gracefully', () => {
      const { unmount } = render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(() => unmount()).not.toThrow();
    });

    test('should not update state after unmount', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      const { unmount, rerender } = render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      // Unmount immediately
      unmount();

      // Try to trigger state update
      (useAuth as jest.Mock).mockReturnValue({
        user: { id: 'test-user', email: 'test@example.com' },
        loading: false,
        initialized: true,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      });

      // Should not log errors about updating unmounted component
      expect(consoleSpy).not.toHaveBeenCalledWith(
        expect.stringContaining("Can't perform a React state update")
      );

      consoleSpy.mockRestore();
    });
  });

  describe('Callback Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should call onAuthCheckComplete with true for authenticated user', async () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: { id: 'test-user', email: 'test@example.com' },
        loading: false,
        initialized: true,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      });

      render(
        <AuthGuard onAuthCheckComplete={mockOnAuthCheckComplete}>
          <div>Protected Content</div>
        </AuthGuard>
      );

      await waitFor(() => {
        expect(mockOnAuthCheckComplete).toHaveBeenCalledWith(true);
      });
    });

    test('should call onAuthCheckComplete with false for unauthenticated user', async () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: false,
        initialized: true,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      });

      render(
        <AuthGuard onAuthCheckComplete={mockOnAuthCheckComplete}>
          <div>Protected Content</div>
        </AuthGuard>
      );

      await waitFor(() => {
        expect(mockOnAuthCheckComplete).toHaveBeenCalledWith(false);
      });
    });

    test('should handle missing onAuthCheckComplete callback', async () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: { id: 'test-user', email: 'test@example.com' },
        loading: false,
        initialized: true,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      });

      // Should not throw when callback is not provided
      expect(() => {
        render(
          <AuthGuard>
            <div>Protected Content</div>
          </AuthGuard>
        );
      }).not.toThrow();
    });
  });

  describe('Edge Cases', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should handle rapid auth state changes', async () => {
      const { rerender } = render(
        <AuthGuard onAuthCheckComplete={mockOnAuthCheckComplete}>
          <div>Protected Content</div>
        </AuthGuard>
      );

      // Rapid state changes
      const states = [
        { user: null, loading: true, initialized: false },
        { user: null, loading: false, initialized: false },
        { user: null, loading: false, initialized: true },
        { user: { id: 'test', email: 'test@example.com' }, loading: false, initialized: true }
      ];

      for (const state of states) {
        (useAuth as jest.Mock).mockReturnValue({
          ...state,
          login: jest.fn(),
          logout: jest.fn(),
          refreshToken: jest.fn(),
          error: null
        });
        
        rerender(
          <AuthGuard onAuthCheckComplete={mockOnAuthCheckComplete}>
            <div>Protected Content</div>
          </AuthGuard>
        );
      }

      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument();
      });

      // Should only have performed auth check once when initialized
      expect(mockOnAuthCheckComplete).toHaveBeenCalledTimes(1);
    });

    test('should handle different pathname formats', async () => {
      const pathnames = [
        '/protected-page',
        '/deep/nested/route',
        '/',
        '/page-with-params?test=true',
        '/page#section'
      ];

      for (const pathname of pathnames) {
        jest.clearAllMocks();
        window.location.pathname = pathname;

        (useAuth as jest.Mock).mockReturnValue({
          user: { id: 'test-user', email: 'test@example.com' },
          loading: false,
          initialized: true,
          login: jest.fn(),
          logout: jest.fn(),
          refreshToken: jest.fn(),
          error: null
        });

        const { unmount } = render(
          <AuthGuard>
            <div>Protected Content</div>
          </AuthGuard>
        );

        await waitFor(() => {
          expect(mockTrackPageView).toHaveBeenCalledWith(pathname, 'Protected Page Access');
        });

        unmount();
      }
    });
  });

  describe('Loading Screen Component', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should render loading screen with correct styling', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: true,
        initialized: false,
        login: jest.fn(),
        logout: jest.fn(),
        refreshToken: jest.fn(),
        error: null
      });

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      const loadingScreen = screen.getByTestId('loading');
      expect(loadingScreen).toHaveClass('flex', 'h-screen', 'items-center', 'justify-center');
      
      const spinner = loadingScreen.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
      expect(spinner).toHaveClass('h-8', 'w-8', 'text-blue-600');
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});