'use client';

import { Fragment } from 'react';
import { NextPage } from 'next';
import { ChatWindow } from '@/components/chat/ChatWindow';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

const HomePage: NextPage = () => {
  const { user, loading } = useAuth();
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

  return (
    <Fragment>
      <div className="flex flex-col h-screen">
        <ChatWindow />
      </div>
    </Fragment>
  );
};

export default HomePage;
