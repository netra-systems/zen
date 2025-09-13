'use client';

import { useEffect } from 'react';

export function SentryInit() {
  useEffect(() => {
    // Sentry temporarily disabled for demo to avoid multiple instance errors
    console.log('Sentry disabled for demo mode');
  }, []);

  return null;
}