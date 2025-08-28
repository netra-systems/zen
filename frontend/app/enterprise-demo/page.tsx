'use client';

import { NextPage } from 'next';
import { AuthGuard } from '@/components/AuthGuard';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

const EnterpriseDemoPage: NextPage = () => {
  const router = useRouter();

  useEffect(() => {
    // Redirect straight to chat for enterprise demo
    router.push('/chat');
  }, [router]);

  // Show loading while redirecting, wrapped in auth guard
  return (
    <AuthGuard>
      <div className="flex items-center justify-center h-screen">
        <p>Loading...</p>
      </div>
    </AuthGuard>
  );
};

export default EnterpriseDemoPage;