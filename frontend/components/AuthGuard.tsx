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
    if (!isMounted.current || hasPerformedAuthCheck.current) return;
    if (loading || !initialized) return;
    
    hasPerformedAuthCheck.current = true;
    const isAuthenticated = !!user;
    const currentPath = window.location.pathname;
    
    if (!isAuthenticated) {
      trackError('auth_required', 'User not authenticated', currentPath, false);
      router.push(redirectTo);
    } else {
      trackPageView(currentPath, 'Protected Page Access');
    }
    
    onAuthCheckComplete?.(isAuthenticated);
  }, [initialized]); // Minimal dependencies - only re-run if initialized changes

  // Show loading state while checking auth or during initialization
  if (loading || !initialized || !user) {
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
    <div className="flex h-screen items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-50" data-testid="loading">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <div className="text-sm text-gray-600">Verifying authentication...</div>
      </div>
    </div>
  );
};