'use client';

import { Fragment } from 'react';
import { NextPage } from 'next';
import { authService } from '@/auth';
import { ChatWindow } from '@/chat/ChatWindow';
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

  const handleSendMessage = (message: string) => {
    console.log(message);
  };

  return (
    <Fragment>
      <div className="flex flex-col h-screen">
        <ChatWindow onSendMessage={handleSendMessage} />
      </div>
    </Fragment>
  );
};

export default HomePage;
