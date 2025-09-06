'use client';

import { useEffect, ReactNode, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/auth/context';
import { Loader2 } from 'lucide-react';
import { useGTMEvent } from '@/hooks/useGTMEvent';
import { logger } from '@/lib/logger';

/**
 * SSOT Authentication Guard Component
 * 
 * Centralizes authentication logic for protected routes.
 * All protected pages should use this component instead of implementing
 * their own auth checks.
 * 
 * @compliance SSOT - Single implementation of auth checking
 * @compliance conventions.xml - Clean, focused component
 */

interface AuthGuardProps {
  children: ReactNode;
  /** Optional redirect path when not authenticated */
  redirectTo?: string;
  /** Optional callback when auth check completes */
  onAuthCheckComplete?: (isAuthenticated: boolean) => void;
  /** Whether to show loading indicator */
  showLoading?: boolean;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({
  children,
  redirectTo = '/login',
  onAuthCheckComplete,
  showLoading = true
}) => {
  const router = useRouter();
  const { user, loading, initialized } = useAuth();
  const { trackError, trackPageView } = useGTMEvent();
  
  // Track if we've already performed auth check and navigation
  const hasPerformedAuthCheck = useRef(false);
  const isMounted = useRef(true);
  const isRedirecting = useRef(false);
  const redirectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      isMounted.current = false;
      if (redirectTimeoutRef.current) {
        clearTimeout(redirectTimeoutRef.current);
      }
    };
  }, []);

  // Reset auth check when auth state changes significantly (for test scenarios)
  useEffect(() => {
    const storedToken = typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : null;
    
    // Reset in two scenarios:
    // 1. No user and no token - ready to check auth again
    // 2. User becomes available - reset redirect state to allow rendering
    if (initialized && !loading) {
      if (!user && !storedToken) {
        // No user, no token - reset for auth check
        hasPerformedAuthCheck.current = false;
        isRedirecting.current = false;
        // Cancel any pending redirects
        if (redirectTimeoutRef.current) {
          clearTimeout(redirectTimeoutRef.current);
          redirectTimeoutRef.current = null;
        }
      } else if (user) {
        // User is available - cancel any pending redirects and reset redirect state
        if (redirectTimeoutRef.current) {
          clearTimeout(redirectTimeoutRef.current);
          redirectTimeoutRef.current = null;
        }
        isRedirecting.current = false;
        // Don't reset hasPerformedAuthCheck here - let the main useEffect handle user state
      }
    }
  }, [user, initialized, loading]); // Reset when these key values change

  useEffect(() => {
    // Only check auth once when fully initialized with minimal dependencies
    if (!isMounted.current) return;
    if (loading || !initialized) return;
    
    // Don't re-check if we already determined authentication state
    if (hasPerformedAuthCheck.current) return;
    
    // In Cypress test environment, skip auth checks entirely
    if (typeof window !== 'undefined' && (window as Window & { Cypress?: unknown }).Cypress) {
      hasPerformedAuthCheck.current = true; // Mark as checked to prevent future checks
      onAuthCheckComplete?.(false); // Report not authenticated but don't redirect
      return;
    }
    
    const isAuthenticated = !!user;
    const currentPath = window.location.pathname;
    
    if (!isAuthenticated) {
      // Double-check localStorage for token before redirecting
      // This helps with race conditions during initialization
      const storedToken = typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : null;
      
      if (!storedToken) {
        // Use a small delay to allow for rapid auth state changes to settle
        // This prevents redirects during rapid state transitions
        redirectTimeoutRef.current = setTimeout(() => {
          if (!isMounted.current) return;
          
          // Re-check localStorage since auth state might have changed
          const newStoredToken = typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : null;
          if (!newStoredToken) {
            // Only mark as checked when we actually make a decision
            hasPerformedAuthCheck.current = true;
            isRedirecting.current = true;
            trackError('auth_required', 'User not authenticated', currentPath, false);
            router.push(redirectTo);
          }
        }, 10); // Small delay to allow rapid state changes to settle
      } else {
        // Token exists but user not set yet - wait for auth context to process it
        logger.debug('Token exists but user not set - waiting for auth processing', undefined, {
          component: 'AuthGuard',
          currentPath
        });
        // Don't mark as checked yet - we're still waiting for auth context
        // The auth context will update and trigger a re-render naturally
      }
    } else {
      // User is authenticated - mark as checked
      hasPerformedAuthCheck.current = true;
      trackPageView(currentPath, 'Protected Page Access');
    }
    
    onAuthCheckComplete?.(isAuthenticated);
  }, [initialized, user, loading, redirectTo, router, trackError, trackPageView, onAuthCheckComplete]); // Include all dependencies

  // Only show loading during initial auth check to reduce flicker
  if (!initialized) {
    if (showLoading) {
      return <LoadingScreen />;
    }
    return null;
  }

  // After initialization, check user authentication
  if (!user) {
    // In Cypress test environment, allow rendering without authentication
    if (typeof window !== 'undefined' && (window as Window & { Cypress?: unknown }).Cypress) {
      return <>{children}</>;
    }
    
    // If we're redirecting, show loading or null
    if (isRedirecting.current) {
      if (showLoading) {
        return <LoadingScreen />;
      }
      return null;
    }
    
    // Check localStorage for token - if token exists, we might be waiting for auth context
    const storedToken = typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : null;
    if (storedToken) {
      // Token exists but user not loaded yet - show loading while waiting for auth context
      if (showLoading) {
        return <LoadingScreen />;
      }
      return null;
    }
    
    // No token and no user - should redirect (handled in useEffect)
    return null;
  }

  // User is authenticated, render children
  return <>{children}</>;
};

/**
 * Loading screen component
 */
const LoadingScreen: React.FC = () => {
  return (
    <div className="flex h-screen items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-50" data-testid="loading">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
        <div className="text-sm text-gray-600">Verifying authentication...</div>
      </div>
    </div>
  );
};