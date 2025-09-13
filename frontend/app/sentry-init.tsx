'use client';

import { useEffect, useRef } from 'react';
import * as Sentry from '@sentry/react';

// Multiple instance prevention - track initialization across the app
let isSentryInitialized = false;

export function SentryInit() {
  const initAttempted = useRef(false);

  useEffect(() => {
    // Prevent multiple initialization attempts
    if (initAttempted.current || isSentryInitialized) {
      return;
    }

    initAttempted.current = true;

    // Environment-aware Sentry configuration
    const environment = process.env.NEXT_PUBLIC_ENVIRONMENT || process.env.NODE_ENV;
    const sentryDsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
    const isProduction = environment === 'production';
    const isStaging = environment === 'staging';

    // Only initialize in staging and production environments with valid DSN
    if (!sentryDsn || (!isProduction && !isStaging)) {
      console.log(`Sentry disabled in ${environment} environment`);
      return;
    }

    try {
      // Validate DSN format
      if (!sentryDsn.startsWith('https://') || !sentryDsn.includes('@sentry.io')) {
        console.warn('Invalid Sentry DSN format detected');
        return;
      }

      // Initialize Sentry with environment-specific configuration
      Sentry.init({
        dsn: sentryDsn,
        environment: environment,
        
        // Performance monitoring
        tracesSampleRate: isProduction ? 0.1 : 0.5, // Lower in production
        
        // Error sampling - capture all errors in staging, sample in production
        sampleRate: isProduction ? 0.8 : 1.0,
        
        // Session replay (disabled for performance and privacy)
        // Note: Replay requires additional setup and configuration
        
        // Security and privacy
        beforeSend: (event, hint) => {
          // Filter out sensitive information
          if (event.exception) {
            const error = hint.originalException;
            if (error instanceof Error && error.message.includes('password')) {
              return null; // Don't send password-related errors
            }
          }
          
          // Add environment context
          event.tags = {
            ...event.tags,
            component: 'frontend',
            deployment: environment,
          };
          
          return event;
        },
        
        // Performance optimizations
        maxBreadcrumbs: isProduction ? 50 : 100,
        attachStacktrace: true,
        
        // Integration configuration - use available integrations
        integrations: [
          // Browser tracing and replay will be configured automatically based on version
        ],
        
        // Release information
        release: process.env.NEXT_PUBLIC_VERSION || 'unknown',
      });

      // Mark as initialized to prevent multiple instances
      isSentryInitialized = true;
      
      // Set user context from authentication
      const setUserContext = () => {
        try {
          const userStr = localStorage.getItem('user');
          if (userStr) {
            const user = JSON.parse(userStr);
            Sentry.setUser({
              id: user.id || user.userId,
              email: user.email,
              username: user.name || user.username,
            });
          }
        } catch (e) {
          // Silent fail - don't break app if user context fails
          console.debug('Could not set Sentry user context:', e);
        }
      };

      // Set initial user context
      setUserContext();
      
      // Listen for authentication changes
      window.addEventListener('storage', (e) => {
        if (e.key === 'user') {
          setUserContext();
        }
      });

      console.log(`Sentry initialized in ${environment} environment`);
      
    } catch (error) {
      console.warn('Failed to initialize Sentry:', error);
      // Reset initialization flag on failure
      isSentryInitialized = false;
    }
  }, []);

  return null;
}