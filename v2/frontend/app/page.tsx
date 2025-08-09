'use client';

import { Fragment } from 'react';
import { NextPage } from 'next';
import { authService } from '@/auth';
import { ChatWindow } from '@/components/chat/ChatWindow';
;
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

const HomePage: NextPage = () => {
  const { user, loading } = authService.useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
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
