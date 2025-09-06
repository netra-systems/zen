/**
 * Auth Flow Stability Regression Tests
 * 
 * Tests to prevent regression of authentication flow issues:
 * - Redirect loops
 * - Auth check race conditions
 * - Token handling edge cases
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import { AuthGuard } from '@/components/AuthGuard';
import { AuthContext, AuthContextType } from '@/auth/context';

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

// Mock GTM hooks
jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: () => ({
    trackError: jest.fn(),
    trackPageView: jest.fn(),
    trackLogin: jest.fn(),
    trackLogout: jest.fn(),
    trackOAuthComplete: jest.fn(),
  }),
}));

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  }
}));

describe('Auth Flow Stability Regression Tests', () => {
  let mockPush: jest.Mock;
  let mockReplace: jest.Mock;
  
  beforeEach(() => {
    mockPush = jest.fn();
    mockReplace = jest.fn();
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
      replace: mockReplace,
      pathname: '/protected',
    });
    
    // Clear localStorage and ensure clean state
    localStorage.clear();
    jest.clearAllMocks();
    
    // Mock window.location.pathname for AuthGuard (delete first to avoid redefinition error)
    delete (window as any).location;
    (window as any).location = {
      pathname: '/protected',
      href: 'http://localhost:3000/protected',
    };
  });
  
  const createAuthContext = (overrides?: Partial<AuthContextType>): AuthContextType => ({
    user: null,
    login: jest.fn(),
    logout: jest.fn(),
    loading: false,
    authConfig: null,
    token: null,
    initialized: true,
    ...overrides,
  });
  
  const renderWithAuth = (
    children: React.ReactNode,
    authValue: AuthContextType
  ) => {
    return render(
      <AuthContext.Provider value={authValue}>
        {children}
      </AuthContext.Provider>
    );
  };
  
  describe('Prevent Redirect Loops', () => {
    it('should not create redirect loop when token exists but user not loaded', async () => {
      // Set token in localStorage
      localStorage.setItem('jwt_token', 'test-token');
      
      const authValue = createAuthContext({
        user: null,
        loading: false,
        initialized: true,
      });
      
      renderWithAuth(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>,
        authValue
      );
      
      // Wait a bit to ensure no rapid redirects
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Should not redirect when token exists
      expect(mockPush).not.toHaveBeenCalled();
    });
    
    it('should perform auth check only once per mount', async () => {
      // Ensure no token in localStorage
      localStorage.clear();
      
      const authValue = createAuthContext({
        user: null,
        loading: false,
        initialized: true,
      });
      
      const { rerender } = renderWithAuth(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>,
        authValue
      );
      
      // Initial redirect - wait longer and provide more specific expectations
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login');
      }, { timeout: 3000 });
      
      // Clear mock to track new calls
      mockPush.mockClear();
      
      // Trigger multiple re-renders with the same auth state
      for (let i = 0; i < 5; i++) {
        rerender(
          <AuthContext.Provider value={authValue}>
            <AuthGuard>
              <div>Protected Content</div>
            </AuthGuard>
          </AuthContext.Provider>
        );
      }
      
      // Wait a bit to ensure no additional calls
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Should not redirect again
      expect(mockPush).not.toHaveBeenCalled();
    });
    
    it('should not reset hasPerformedAuthCheck when token exists', async () => {
      localStorage.setItem('jwt_token', 'test-token');
      
      // Start with no user
      const authValue = createAuthContext({
        user: null,
        loading: false,
        initialized: true,
      });
      
      const { rerender } = renderWithAuth(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>,
        authValue
      );
      
      // Should not redirect when token exists
      expect(mockPush).not.toHaveBeenCalled();
      
      // Update auth context with user
      const updatedAuthValue = createAuthContext({
        user: { id: '1', email: 'test@example.com', full_name: 'Test User' },
        loading: false,
        initialized: true,
      });
      
      rerender(
        <AuthContext.Provider value={updatedAuthValue}>
          <AuthGuard>
            <div>Protected Content</div>
          </AuthGuard>
        </AuthContext.Provider>
      );
      
      // Should render protected content
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
      
      // Should still not have redirected
      expect(mockPush).not.toHaveBeenCalled();
    });
  });
  
  describe('Auth Check Race Conditions', () => {
    it('should wait for initialization before checking auth', async () => {
      // Ensure no token in localStorage
      localStorage.clear();
      
      // Start uninitialized
      const authValue = createAuthContext({
        user: null,
        loading: true,
        initialized: false,
      });
      
      const { rerender } = renderWithAuth(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>,
        authValue
      );
      
      // Should not redirect while not initialized
      expect(mockPush).not.toHaveBeenCalled();
      
      // Become initialized without user and no token
      const initializedAuthValue = createAuthContext({
        user: null,
        loading: false,
        initialized: true,
      });
      
      rerender(
        <AuthContext.Provider value={initializedAuthValue}>
          <AuthGuard>
            <div>Protected Content</div>
          </AuthGuard>
        </AuthContext.Provider>
      );
      
      // Now should redirect
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login');
      }, { timeout: 3000 });
    });
    
    it('should handle rapid auth state changes', async () => {
      // Simulate rapid auth state changes
      const states = [
        createAuthContext({ user: null, loading: true, initialized: false }),
        createAuthContext({ user: null, loading: true, initialized: true }),
        createAuthContext({ user: null, loading: false, initialized: true }),
        createAuthContext({ 
          user: { id: '1', email: 'test@example.com', full_name: 'Test User' }, 
          loading: false, 
          initialized: true 
        }),
      ];
      
      const { rerender } = renderWithAuth(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>,
        states[0]
      );
      
      // Rapidly change states
      for (const state of states.slice(1)) {
        rerender(
          <AuthContext.Provider value={state}>
            <AuthGuard>
              <div>Protected Content</div>
            </AuthGuard>
          </AuthContext.Provider>
        );
      }
      
      // Should eventually show protected content without redirecting
      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument();
      });
      
      // Should not have redirected (user was authenticated in final state)
      expect(mockPush).not.toHaveBeenCalled();
    });
  });
  
  describe('Token Handling Edge Cases', () => {
    it('should handle token removal during session', async () => {
      localStorage.setItem('jwt_token', 'test-token');
      
      const authValue = createAuthContext({
        user: { id: '1', email: 'test@example.com', full_name: 'Test User' },
        loading: false,
        initialized: true,
        token: 'test-token',
      });
      
      const { rerender } = renderWithAuth(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>,
        authValue
      );
      
      // Should show protected content
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
      
      // Remove token and create a new component instance to trigger fresh auth check
      localStorage.removeItem('jwt_token');
      const noTokenAuthValue = createAuthContext({
        user: null,
        loading: false,
        initialized: true,
        token: null,
      });
      
      // Unmount and remount to trigger fresh auth check
      rerender(<div />);
      rerender(
        <AuthContext.Provider value={noTokenAuthValue}>
          <AuthGuard>
            <div>Protected Content</div>
          </AuthGuard>
        </AuthContext.Provider>
      );
      
      // Should redirect to login
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login');
      }, { timeout: 3000 });
    });
    
    it('should handle expired token gracefully', async () => {
      // Set an "expired" token
      localStorage.setItem('jwt_token', 'expired-token');
      
      const authValue = createAuthContext({
        user: null,
        loading: false,
        initialized: true,
        token: null,  // Auth context couldn't validate the token
      });
      
      renderWithAuth(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>,
        authValue
      );
      
      // Wait to see behavior
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Should wait for auth context to process the token
      // Not immediately redirect since token exists in localStorage
      expect(mockPush).not.toHaveBeenCalled();
    });
    
    it('should handle custom redirect paths', async () => {
      // Ensure no token in localStorage
      localStorage.clear();
      
      const authValue = createAuthContext({
        user: null,
        loading: false,
        initialized: true,
      });
      
      renderWithAuth(
        <AuthGuard redirectTo="/custom-login">
          <div>Protected Content</div>
        </AuthGuard>,
        authValue
      );
      
      // Should redirect to custom path
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/custom-login');
      }, { timeout: 3000 });
    });
  });
  
  describe('Component Unmount Handling', () => {
    it('should not perform auth actions after unmount', async () => {
      const authValue = createAuthContext({
        user: null,
        loading: true,
        initialized: false,
      });
      
      const { unmount } = renderWithAuth(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>,
        authValue
      );
      
      // Unmount immediately
      unmount();
      
      // Simulate delayed auth initialization
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Should not have called router after unmount
      expect(mockPush).not.toHaveBeenCalled();
    });
  });
  
  describe('Cypress Test Environment', () => {
    it('should allow rendering without authentication in Cypress', () => {
      // Simulate Cypress environment
      (window as any).Cypress = {};
      
      const authValue = createAuthContext({
        user: null,
        loading: false,
        initialized: true,
      });
      
      renderWithAuth(
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>,
        authValue
      );
      
      // Should render content without redirecting
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
      expect(mockPush).not.toHaveBeenCalled();
      
      // Clean up
      delete (window as any).Cypress;
    });
  });
});