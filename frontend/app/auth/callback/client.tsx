'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { logger } from '@/utils/debug-logger';

export default function AuthCallbackClient() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const handleCallback = async () => {
      const token = searchParams.get('token');
      const error = searchParams.get('message');

      if (error) {
        logger.error('OAuth error:', error);
        router.push('/login?error=' + encodeURIComponent(error));
        return;
      }

      if (token) {
        // Store the token
        localStorage.setItem('jwt_token', token);
        
        // Redirect to main page or dashboard
        router.push('/');
      } else {
        logger.error('No token received');
        router.push('/login?error=no_token');
      }
    };

    handleCallback();
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h2 className="text-2xl font-semibold mb-2">Authenticating...</h2>
        <p className="text-gray-600">Please wait while we complete your login.</p>
      </div>
    </div>
  );
}