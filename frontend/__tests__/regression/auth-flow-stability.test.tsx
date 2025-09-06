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
  useGTMEvent: jest.fn(),
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
  let originalLocalStorage: Storage;
  let mockTrackError: jest.Mock;
  let mockTrackPageView: jest.Mock;
  let mockTrackLogin: jest.Mock;
  let mockTrackLogout: jest.Mock;
  let mockTrackOAuthComplete: jest.Mock;
  
  beforeAll(() => {
    // Store the original localStorage
    originalLocalStorage = global.localStorage;
    
    // Create stable GTM mock functions
    mockTrackError = jest.fn();
    mockTrackPageView = jest.fn();
    mockTrackLogin = jest.fn();
    mockTrackLogout = jest.fn();
    mockTrackOAuthComplete = jest.fn();
  });
  
  beforeEach(() => {
    mockPush = jest.fn();
    mockReplace = jest.fn();
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
      replace: mockReplace,
      pathname: '/protected',
    });
    
    // Clear global mock auth state to ensure clean test state
    global.mockAuthState = undefined;
    
    // Mock GTM with stable functions
    (require('@/hooks/useGTMEvent').useGTMEvent as jest.Mock).mockReturnValue({
      trackError: mockTrackError,
      trackPageView: mockTrackPageView,
      trackLogin: mockTrackLogin,
      trackLogout: mockTrackLogout,
      trackOAuthComplete: mockTrackOAuthComplete,
    });
    
    // Create a fresh localStorage mock for each test
    const localStorageMock = {
      getItem: jest.fn().mockReturnValue(null),
      setItem: jest.fn(),
      removeItem: jest.fn(),
      clear: jest.fn(),
      length: 0,
      key: jest.fn().mockReturnValue(null),
    };
    
    Object.defineProperty(global, 'localStorage', {
      value: localStorageMock,
      writable: true,
      configurable: true
    });
    
    // Also ensure window.localStorage is mocked consistently
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true,
      configurable: true
    });
    
    jest.clearAllMocks();
    
    // Mock window.location.pathname for AuthGuard (delete first to avoid redefinition error)
    delete (window as any).location;
    (window as any).location = {
      pathname: '/protected',
      href: 'http://localhost:3000/protected',
    };
  });
  
  afterAll(() => {
    // Restore original localStorage
    Object.defineProperty(global, 'localStorage', {
      value: originalLocalStorage,
      writable: true,
      configurable: true
    });
  });
  
  // Helper to set localStorage value and ensure it's properly mocked
  const setLocalStorageToken = (token: string | null) => {
    const mockReturnValue = token;
    (localStorage.getItem as jest.Mock).mockImplementation((key: string) => {
      if (key === 'jwt_token') return mockReturnValue;
      return null;
    });
    (window.localStorage.getItem as jest.Mock).mockImplementation((key: string) => {
      if (key === 'jwt_token') return mockReturnValue;
      return null;
    });
  };
  
  // Helper to ensure localStorage is completely empty
  const ensureLocalStorageEmpty = () => {
    (localStorage.getItem as jest.Mock).mockImplementation(() => null);
    (window.localStorage.getItem as jest.Mock).mockImplementation(() => null);
  };
  
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
    // Set global mock auth state to override the jest mock
    global.mockAuthState = authValue;
    
    return render(
      <AuthContext.Provider value={authValue}>
        {children}
      </AuthContext.Provider>
    );
  };
  
  describe('Prevent Redirect Loops', () => {
    it('should not create redirect loop when token exists but user not loaded', async () => {
      // Set token in localStorage mock
      setLocalStorageToken('test-token');
      
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
      // Ensure localStorage is completely empty
      ensureLocalStorageEmpty();
      
      // Debug: Check that localStorage is properly mocked
      expect(localStorage.getItem('jwt_token')).toBeNull();
      expect(window.localStorage.getItem('jwt_token')).toBeNull();
      
      const authValue = createAuthContext({
        user: null,
        loading: false,
        initialized: true,
      });
      
      // Use a key to force component remount
      const { rerender } = renderWithAuth(
        <AuthGuard key="test-1">
          <div>Protected Content</div>
        </AuthGuard>,
        authValue
      );
      
      // Wait for auth check to complete
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Debug: Check if the localStorage call was made during rendering
      expect(localStorage.getItem).toHaveBeenCalled();
      
      // Debug: Check if trackError was called (this happens right before redirect)
      expect(mockTrackError).toHaveBeenCalled();
      
      // Should redirect once
      expect(mockPush).toHaveBeenCalledWith('/login');
      expect(mockPush).toHaveBeenCalledTimes(1);
      
      // Clear mock to track new calls
      mockPush.mockClear();
      
      // Trigger multiple re-renders with the same auth state (same key - no remount)
      for (let i = 0; i < 5; i++) {
        rerender(
          <AuthContext.Provider value={authValue}>
            <AuthGuard key="test-1">
              <div>Protected Content</div>
            </AuthGuard>
          </AuthContext.Provider>
        );
      }
      
      // Wait to ensure no additional calls
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Should not redirect again (hasPerformedAuthCheck prevents multiple calls)
      expect(mockPush).not.toHaveBeenCalled();
    });
    
    it('should not reset hasPerformedAuthCheck when token exists', async () => {
      // Set token in localStorage mock
      setLocalStorageToken('test-token');
      
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
      
      // Set global mock auth state for rerender
      global.mockAuthState = updatedAuthValue;
      
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
      // Ensure localStorage is completely empty
      ensureLocalStorageEmpty();
      
      // Start uninitialized
      const authValue = createAuthContext({
        user: null,
        loading: true,
        initialized: false,
      });
      
      const { rerender } = renderWithAuth(
        <AuthGuard key="test-2">
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
      
      // Set global mock auth state for rerender
      global.mockAuthState = initializedAuthValue;
      
      rerender(
        <AuthContext.Provider value={initializedAuthValue}>
          <AuthGuard key="test-2">
            <div>Protected Content</div>
          </AuthGuard>
        </AuthContext.Provider>
      );
      
      // Wait for auth check to complete after initialization
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Now should redirect
      expect(mockPush).toHaveBeenCalledWith('/login');
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
        // Set global mock auth state for each rerender
        global.mockAuthState = state;
        
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
      // Start with token in localStorage
      setLocalStorageToken('test-token');
      
      const authValue = createAuthContext({
        user: { id: '1', email: 'test@example.com', full_name: 'Test User' },
        loading: false,
        initialized: true,
        token: 'test-token',
      });
      
      const { rerender } = renderWithAuth(
        <AuthGuard key="test-3-authenticated">
          <div>Protected Content</div>
        </AuthGuard>,
        authValue
      );
      
      // Should show protected content
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
      
      // Remove token and clear localStorage
      ensureLocalStorageEmpty();
      const noTokenAuthValue = createAuthContext({
        user: null,
        loading: false,
        initialized: true,
        token: null,
      });
      
      // Use a different key to force fresh component mount with fresh hasPerformedAuthCheck
      // Set global mock auth state for rerender
      global.mockAuthState = noTokenAuthValue;
      
      rerender(
        <AuthContext.Provider value={noTokenAuthValue}>
          <AuthGuard key="test-3-unauthenticated">
            <div>Protected Content</div>
          </AuthGuard>
        </AuthContext.Provider>
      );
      
      // Wait for auth check to complete
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Should redirect to login since token was removed
      expect(mockPush).toHaveBeenCalledWith('/login');
    });
    
    it('should handle expired token gracefully', async () => {
      // Set an "expired" token in localStorage mock
      setLocalStorageToken('expired-token');
      
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
      // Ensure localStorage is completely empty
      ensureLocalStorageEmpty();
      
      const authValue = createAuthContext({
        user: null,
        loading: false,
        initialized: true,
      });
      
      renderWithAuth(
        <AuthGuard key="test-4" redirectTo="/custom-login">
          <div>Protected Content</div>
        </AuthGuard>,
        authValue
      );
      
      // Wait for auth check to complete
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Should redirect to custom path
      expect(mockPush).toHaveBeenCalledWith('/custom-login');
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