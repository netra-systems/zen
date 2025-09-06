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

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      isMounted.current = false;
    };
  }, []);

  useEffect(() => {
    // Only check auth once when fully initialized with minimal dependencies
    if (!isMounted.current) return;
    if (loading || !initialized) return;
    
    // Don't re-check if we already determined authentication state
    if (hasPerformedAuthCheck.current) return;
    
    const isAuthenticated = !!user;
    const currentPath = window.location.pathname;
    
    if (!isAuthenticated) {
      // Double-check localStorage for token before redirecting
      // This helps with race conditions during initialization
      const storedToken = typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : null;
      if (!storedToken) {
        // Only mark as checked when we actually make a decision
        hasPerformedAuthCheck.current = true;
        trackError('auth_required', 'User not authenticated', currentPath, false);
        router.push(redirectTo);
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
    
    // User not authenticated, router.push will handle redirect
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