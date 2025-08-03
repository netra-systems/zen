"use client";

import React, { useEffect } from 'react';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Dashboard } from '@/components/Dashboard';
import { useStore } from '@/store';
import { Sidebar } from '@/components/Sidebar';
import useAppStore from '@/store';

export default function AppClient() {
  const { fetchUser, setToken, setIsLoading } = useAppStore();
  const isLoading = useStore((state) => state.isLoading);

  useEffect(() => {
    const storedToken = localStorage.getItem('authToken');
    if (storedToken) {
      setToken(storedToken);
      fetchUser(storedToken);
    } else {
      setIsLoading(false);
    }
  }, [fetchUser, setToken, setIsLoading]);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="grid min-h-screen w-full md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]">
      <Sidebar />
      <div className="flex flex-col">
        <Header />
        <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
          <Dashboard />
        </main>
        <Footer />
      </div>
    </div>
  );
}
