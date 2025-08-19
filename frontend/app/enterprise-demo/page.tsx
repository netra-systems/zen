'use client';

import { NextPage } from 'next';
import { authService } from '@/auth';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

const EnterpriseDemoPage: NextPage = () => {
  const { user, loading } = authService.useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    } else if (!loading && user) {
      // Redirect straight to chat for enterprise demo
      router.push('/chat');
    }
  }, [loading, user, router]);

  // Show loading while redirecting
  return (
    <div className="flex items-center justify-center h-screen">
      <p>Loading...</p>
    </div>
  );
};

export default EnterpriseDemoPage;