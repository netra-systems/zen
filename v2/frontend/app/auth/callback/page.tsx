'use client';

import { useEffect } from 'react';
import { useAuth } from '@/providers/auth';

export default function AuthCallbackPage() {
  const { handleAuthCallback } = useAuth();

  useEffect(() => {
    handleAuthCallback();
  }, [handleAuthCallback]);

  return <div>Loading...</div>;
}
