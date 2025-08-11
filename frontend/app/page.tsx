'use client';

import { NextPage } from 'next';
import { authService } from '@/auth';
;
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

const HomePage: NextPage = () => {
  const { user, loading } = authService.useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (!user) {
        router.push('/login');
      } else {
        router.push('/enterprise-demo');
      }
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Loading...</p>
      </div>
    );
  }
};

export default HomePage;
