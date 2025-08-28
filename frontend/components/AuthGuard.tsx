'use client';

import { useEffect, ReactNode } from 'react';
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

  useEffect(() => {
    if (!loading) {
      const isAuthenticated = !!user;
      
      if (!isAuthenticated) {
        // Track authentication failure
        trackError('auth_required', 'User not authenticated', window.location.pathname, false);
        router.push(redirectTo);
      } else {
        // Track successful authentication check
        trackPageView(window.location.pathname, 'Protected Page Access');
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