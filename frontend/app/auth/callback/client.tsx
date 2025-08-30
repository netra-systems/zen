'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { logger } from '@/utils/debug-logger';

export default function AuthCallbackClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [criticalError, setCriticalError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      const token = searchParams.get('token');
      const refreshToken = searchParams.get('refresh');
      const error = searchParams.get('message');
      const errorCode = searchParams.get('error');

      // CRITICAL: Check for OAuth configuration errors
      if (error && (error.includes('OAUTH_CONFIGURATION') || error.includes('OAuth Configuration'))) {
        logger.error('CRITICAL OAuth configuration error:', error);
        setCriticalError('OAuth Configuration Broken - Authentication system is not properly configured. Please contact the system administrator.');
        return;
      }

      // CRITICAL: Check for missing credentials errors
      if (errorCode === 'oauth_config_error' || error?.includes('OAuth not configured')) {
        logger.error('CRITICAL OAuth credentials missing:', error);
        setCriticalError('OAuth Configuration Error - Google authentication credentials are missing. Please contact the system administrator.');
        return;
      }

      // CRITICAL: Check for auth service unavailable
      if (error?.includes('AUTH_CONFIG_FAILURE') || error?.includes('auth service unavailable')) {
        logger.error('CRITICAL Auth service failure:', error);
        setCriticalError('Authentication Service Unavailable - The authentication system is currently down. Please try again later or contact support.');
        return;
      }

      if (error) {
        logger.error('OAuth error:', error);
        
        // Enhanced error messages for better user experience
        let userFriendlyError = error;
        if (error.includes('state parameter')) {
          userFriendlyError = 'Authentication security validation failed. Please try logging in again.';
        } else if (error.includes('code')) {
          userFriendlyError = 'Authentication code exchange failed. Please try logging in again.';
        }
        
        // Add a delay to prevent immediate redirect loops
        setTimeout(() => {
          router.push('/login?error=' + encodeURIComponent(userFriendlyError));
        }, 500);
        return;
      }

      if (token) {
        // Store both tokens
        localStorage.setItem('jwt_token', token);
        if (refreshToken) {
          localStorage.setItem('refresh_token', refreshToken);
        }
        
        logger.info('OAuth authentication successful, redirecting to chat');
        
        // Dispatch a storage event to notify other components immediately
        // This helps AuthContext detect the token faster
        try {
          window.dispatchEvent(new StorageEvent('storage', {
            key: 'jwt_token',
            newValue: token,
            url: window.location.href,
            storageArea: typeof window !== 'undefined' ? localStorage : null
          }));
        } catch (error) {
          // Fallback for test environments where StorageEvent constructor may not work
          const event = new Event('storage') as StorageEvent;
          Object.defineProperties(event, {
            key: { value: 'jwt_token', writable: false },
            newValue: { value: token, writable: false },
            url: { value: window.location.href, writable: false },
            storageArea: { value: localStorage, writable: false }
          });
          window.dispatchEvent(event);
        }
        
        // Small delay to ensure storage event is processed
        setTimeout(() => {
          router.push('/chat');
        }, 50);
      } else {
        logger.error('No token received in OAuth callback');
        setCriticalError('Authentication Failed - No authentication token received. This may indicate an OAuth configuration problem.');
      }
    };

    handleCallback();
  }, [searchParams, router]);

  // CRITICAL ERROR BANNER
  if (criticalError) {
    return (
      <div className="min-h-screen bg-red-50 flex items-center justify-center p-4">
        <div className="max-w-2xl w-full bg-white border-l-4 border-red-500 shadow-lg rounded-lg">
          <div className="p-6">
            <div className="flex items-center mb-4">
              <div className="flex-shrink-0">
                <svg className="h-8 w-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.732 15.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <div className="ml-3">
                <h1 className="text-xl font-bold text-red-900">
                  🚨 CRITICAL AUTHENTICATION ERROR
                </h1>
              </div>
            </div>
            
            <div className="mb-6">
              <p className="text-red-800 text-lg font-medium mb-3">
                {criticalError}
              </p>
              
              <div className="bg-red-100 border border-red-300 rounded-lg p-4">
                <h3 className="font-semibold text-red-900 mb-2">Technical Details:</h3>
                <ul className="text-red-800 text-sm space-y-1">
                  <li>• OAuth authentication system is not properly configured</li>
                  <li>• This prevents all user login functionality</li>
                  <li>• Administrator intervention is required</li>
                  <li>• Error occurred during authentication callback</li>
                </ul>
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => router.push('/login')}
                className="flex-1 bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                Return to Login
              </button>
              <button
                onClick={() => window.location.reload()}
                className="flex-1 bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Retry Authentication
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <h2 className="text-2xl font-semibold mb-2">Authenticating...</h2>
        <p className="text-gray-600">Please wait while we complete your login.</p>
      </div>
    </div>
  );
}