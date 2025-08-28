'use client';

import { useEffect, ReactNode, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/auth/context';
import { Loader2 } from 'lucide-react';
import { useGTMEvent } from '@/hooks/useGTMEvent';

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
  const { user, loading } = useAuth();
  const { trackError, trackPageView } = useGTMEvent();
  
  // Track if we've already reported auth failure for this mount
  const hasReportedAuthFailure = useRef(false);
  const hasReportedPageView = useRef(false);
  const lastPathname = useRef<string>();

  useEffect(() => {
    if (!loading) {
      const isAuthenticated = !!user;
      const currentPath = window.location.pathname;
      
      if (!isAuthenticated) {
        // Only track auth failure once per mount and path
        if (!hasReportedAuthFailure.current || lastPathname.current !== currentPath) {
          trackError('auth_required', 'User not authenticated', currentPath, false);
          hasReportedAuthFailure.current = true;
          lastPathname.current = currentPath;
        }
        router.push(redirectTo);
      } else {
        // Only track page view once per mount and path
        if (!hasReportedPageView.current || lastPathname.current !== currentPath) {
          trackPageView(currentPath, 'Protected Page Access');
          hasReportedPageView.current = true;
          lastPathname.current = currentPath;
        }
      }
      
      onAuthCheckComplete?.(isAuthenticated);
    }
  }, [loading, user, router, redirectTo, onAuthCheckComplete, trackError, trackPageView]);

  // Show loading state while checking auth
  if (loading || !user) {
    if (showLoading) {
      return <LoadingScreen />;
    }
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
    <div className="flex h-screen items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-50">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <div className="text-sm text-gray-600">Verifying authentication...</div>
      </div>
    </div>
  );
};