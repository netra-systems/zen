/**
 * Test Suite: AuthGuard Race Condition Prevention
 * Tests that AuthGuard waits for initialization before making auth decisions
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import { AuthGuard } from '@/components/AuthGuard';
import { useAuth } from '@/auth/context';
import { useGTMEvent } from '@/hooks/useGTMEvent';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock dependencies
jest.mock('next/navigation', () => ({
  useRouter: jest.fn()
}));

jest.mock('@/auth/context', () => ({
  useAuth: jest.fn()
}));

jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: jest.fn()
}));

describe('AuthGuard - Race Condition Prevention', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  const mockPush = jest.fn();
  const mockTrackError = jest.fn();
  const mockTrackPageView = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue({ push: mockPush });
    (useGTMEvent as jest.Mock).mockReturnValue({
      trackError: mockTrackError,
      trackPageView: mockTrackPageView
    });
  });

  describe('Initialization State Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should show loading when loading=true regardless of initialized state', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: true,
        initialized: false
      });

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(screen.getByText('Verifying authentication...')).toBeInTheDocument();
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled();
    });

    it('should show loading when initialized=false even if loading=false', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: false,
        initialized: false
      });

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(screen.getByText('Verifying authentication...')).toBeInTheDocument();
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled(); // No redirect yet!
    });

    it('should only redirect when both loading=false AND initialized=true', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: false,
        initialized: true // Now fully initialized
      });

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(mockPush).toHaveBeenCalledWith('/login');
      expect(mockTrackError).toHaveBeenCalledWith(
        'auth_required',
        'User not authenticated',
        '/',
        false
      );
    });

    it('should render content when user authenticated and initialized', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: { id: 'test-user', email: 'test@example.com' },
        loading: false,
        initialized: true
      });

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(screen.getByText('Protected Content')).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled();
      expect(mockTrackPageView).toHaveBeenCalledWith('/', 'Protected Page Access');
    });
  });

  describe('Progressive State Transitions', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle progressive initialization states correctly', () => {
      const { rerender } = render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      // Stage 1: Loading auth config
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: true,
        initialized: false
      });
      rerender(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );
      expect(screen.getByText('Verifying authentication...')).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled();

      // Stage 2: Auth config loaded, but not initialized
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: false,
        initialized: false
      });
      rerender(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );
      expect(screen.getByText('Verifying authentication...')).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled(); // Still no redirect!

      // Stage 3: Fully initialized with user
      (useAuth as jest.Mock).mockReturnValue({
        user: { id: 'test-user', email: 'test@example.com' },
        loading: false,
        initialized: true
      });
      rerender(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled();
    });

    it('should handle token restoration during initialization', async () => {
      // Simulate the actual flow when a token is being restored
      const { rerender } = render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      // Initial state - loading
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: true,
        initialized: false
      });
      rerender(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );
      expect(mockPush).not.toHaveBeenCalled();

      // Token found and being validated
      (useAuth as jest.Mock).mockReturnValue({
        user: null, // User not decoded yet
        loading: false,
        initialized: false // Still validating
      });
      rerender(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );
      expect(mockPush).not.toHaveBeenCalled(); // Don't redirect yet!

      // Token validated and user set
      (useAuth as jest.Mock).mockReturnValue({
        user: { id: 'restored-user', email: 'restored@example.com' },
        loading: false,
        initialized: true
      });
      rerender(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled(); // User was authenticated!
    });
  });

  describe('Custom Props', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should redirect to custom path when not authenticated', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: false,
        initialized: true
      });

      render(
        <AuthGuard redirectTo="/custom-login">
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(mockPush).toHaveBeenCalledWith('/custom-login');
    });

    it('should call onAuthCheckComplete callback', () => {
      const onComplete = jest.fn();
      
      (useAuth as jest.Mock).mockReturnValue({
        user: { id: 'test-user', email: 'test@example.com' },
        loading: false,
        initialized: true
      });

      render(
        <AuthGuard onAuthCheckComplete={onComplete}>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(onComplete).toHaveBeenCalledWith(true);
    });

    it('should respect showLoading=false prop', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: true,
        initialized: false
      });

      render(
        <AuthGuard showLoading={false}>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(screen.queryByText('Verifying authentication...')).not.toBeInTheDocument();
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });
  });

  describe('GTM Event Tracking', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track auth failure only once per mount and path', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: false,
        initialized: true
      });

      const { rerender } = render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(mockTrackError).toHaveBeenCalledTimes(1);

      // Re-render with same state
      rerender(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      // Should not track again
      expect(mockTrackError).toHaveBeenCalledTimes(1);
    });

    it('should track page view for authenticated access', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: { id: 'test-user', email: 'test@example.com' },
        loading: false,
        initialized: true
      });

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(mockTrackPageView).toHaveBeenCalledWith('/', 'Protected Page Access');
      expect(mockTrackError).not.toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle rapid state changes gracefully', () => {
      const { rerender } = render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      // Rapid state changes
      const states = [
        { user: null, loading: true, initialized: false },
        { user: null, loading: false, initialized: false },
        { user: null, loading: true, initialized: false },
        { user: null, loading: false, initialized: true },
        { user: { id: 'user', email: 'test@example.com' }, loading: false, initialized: true }
      ];

      states.forEach(state => {
        (useAuth as jest.Mock).mockReturnValue(state);
        rerender(
          <AuthGuard>
            <div>Protected Content</div>
          </AuthGuard>
        );
      });

      // Should end up with content displayed
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled();
    });

    it('should handle undefined user gracefully', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: undefined, // undefined instead of null
        loading: false,
        initialized: true
      });

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(mockPush).toHaveBeenCalledWith('/login');
    });

    it('should prevent multiple redirects', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: false,
        initialized: true
      });

      const { rerender } = render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      expect(mockPush).toHaveBeenCalledTimes(1);

      // Multiple re-renders shouldn't cause multiple redirects
      for (let i = 0; i < 5; i++) {
        rerender(
          <AuthGuard>
            <div>Protected Content</div>
          </AuthGuard>
        );
      }

      expect(mockPush).toHaveBeenCalledTimes(1);
    });
  });

  describe('Loading Screen', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should display loading screen with correct styling', () => {
      (useAuth as jest.Mock).mockReturnValue({
        user: null,
        loading: true,
        initialized: false
      });

      render(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      );

      const loadingContainer = screen.getByText('Verifying authentication...').parentElement?.parentElement;
      expect(loadingContainer).toHaveClass('flex', 'h-screen', 'items-center', 'justify-center');
      
      // Check for spinner
      const spinner = loadingContainer?.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});