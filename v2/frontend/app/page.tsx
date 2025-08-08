'use client';

import { Fragment } from 'react';
import { NextPage } from 'next';
import { WebSocketTest } from '@/components/WebSocketTest';
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
      <div className="flex flex-col items-center justify-center min-h-screen py-2">
        <main className="flex flex-col items-center justify-center w-full flex-1 px-20 text-center">
          <h1 className="text-6xl font-bold">
            Welcome to <a className="text-blue-600" href="https://netrasystems.ai">Netra!</a>
          </h1>

          <p className="mt-3 text-2xl">
            You are logged in as {user.full_name}.
          </p>

          <WebSocketTest />
        </main>
      </div>
    </Fragment>
  );
};

export default HomePage;