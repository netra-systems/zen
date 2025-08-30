'use client';

import { NextPage } from 'next';
import { useAuth } from '@/auth/context';
import { useRouter } from 'next/navigation';
import { useEffect, useRef } from 'react';

const HomePage: NextPage = () => {
  const { user, loading, initialized } = useAuth();
  const router = useRouter();
  const hasRedirectedRef = useRef(false);

  useEffect(() => {
    // Prevent multiple redirects
    if (hasRedirectedRef.current) {
      return;
    }

    // Only redirect after auth is fully initialized and not loading
    if (initialized && !loading) {
      hasRedirectedRef.current = true;
      
      // Add small delay to ensure auth state is stable
      const redirectTimer = setTimeout(() => {
        if (!user) {
          router.push('/login');
        } else {
          router.push('/chat');
        }
      }, 100);

      return () => clearTimeout(redirectTimer);
    }
  }, [initialized, loading, user, router]);

  // Show loading while auth is initializing or loading
  if (!initialized || loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
          <p className="text-gray-600">Loading Netra AI...</p>
        </div>
      </div>
    );
  }

  // Return null when redirecting (redirect will happen via useEffect)
  return null;
};

export default HomePage;
