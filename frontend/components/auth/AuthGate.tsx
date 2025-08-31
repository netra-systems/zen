"use client";

import React, { ReactNode } from 'react';
import { useAuthState } from '@/hooks/useAuthState';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

/**
 * Auth Gate Component - Wrapper for Authentication-Protected Content
 * 
 * Business Value: Drives Free → Paid conversions with clear CTAs
 * - Shows fallback content for unauthenticated users
 * - Loading states during auth verification
 * - Conversion-focused messaging for free users
 * 
 * Architecture: <100 lines, ≤8 line functions
 */

export interface AuthGateProps {
  children: ReactNode;
  fallback?: ReactNode;
  showLoginPrompt?: boolean;
  requireTier?: 'Early' | 'Mid' | 'Enterprise';
  customMessage?: string;
}

// Helper component for loading state (≤8 lines)
const AuthLoadingState: React.FC = () => (
  <div className="flex items-center justify-center p-6">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
    <span className="ml-3 text-gray-600">Verifying access...</span>
  </div>
);

// Helper component for login prompt (≤8 lines)
const LoginPrompt: React.FC<{ message?: string }> = ({ message }) => (
  <Card className="p-6 text-center bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
    <h3 className="text-lg font-semibold text-gray-900 mb-2">
      🚀 Unlock AI Optimization
    </h3>
    <p className="text-gray-600 mb-4">
      {message || "Start saving 20-40% on your AI costs with Netra Apex"}
    </p>
    <Button className="w-full bg-blue-600 hover:bg-blue-700">
      Start Free Trial
    </Button>
  </Card>
);

// Helper component for tier upgrade prompt (≤8 lines)
const TierUpgradePrompt: React.FC<{ requiredTier: string; currentTier: string }> = ({ 
  requiredTier, 
  currentTier 
}) => (
  <Card className="p-6 text-center bg-gradient-to-br from-amber-50 to-orange-50 border-amber-200">
    <h3 className="text-lg font-semibold text-gray-900 mb-2">
      ⭐ {requiredTier} Feature
    </h3>
    <p className="text-gray-600 mb-4">
      Upgrade from {currentTier} to {requiredTier} to access this feature
    </p>
    <Button className="w-full bg-amber-600 hover:bg-amber-700" disabled>
      Upgrade to {requiredTier}
    </Button>
  </Card>
);

// Helper function to check tier access (≤8 lines)
const checkTierAccess = (currentTier: string, requiredTier?: string): boolean => {
  if (!requiredTier) return true;
  const tierLevels = { Free: 0, Early: 1, Mid: 2, Enterprise: 3 };
  const current = tierLevels[currentTier as keyof typeof tierLevels] || 0;
  const required = tierLevels[requiredTier as keyof typeof tierLevels] || 0;
  return current >= required;
};

// Main AuthGate component (≤8 lines per function)
export const AuthGate: React.FC<AuthGateProps> = ({
  children,
  fallback,
  showLoginPrompt = true,
  requireTier,
  customMessage
}) => {
  const { isAuthenticated, isLoading, userTier } = useAuthState();

  // Show loading state during auth check (≤8 lines)
  if (isLoading) {
    return <AuthLoadingState />;
  }

  // Show login prompt for unauthenticated users (≤8 lines)
  if (!isAuthenticated) {
    if (fallback) return <>{fallback}</>;
    if (!showLoginPrompt) return null;
    return <LoginPrompt message={customMessage} />;
  }

  // Check tier requirements (≤8 lines)
  if (requireTier && !checkTierAccess(userTier, requireTier)) {
    return <TierUpgradePrompt requiredTier={requireTier} currentTier={userTier} />;
  }

  // Render protected content
  return <>{children}</>;
};