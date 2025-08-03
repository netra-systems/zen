"use client";

import React, { useEffect } from 'react';
import { Header } from '@/app/components/Header';
import { Footer } from '@/app/components/Footer';
import { Dashboard } from '@/app/components/Dashboard';
import { useAppStore } from '@/app/store';

export default function App() {
  const { fetchUser } = useAppStore();

  useEffect(() => {
    const token = localStorage.getItem('authToken');
    if (token) {
      fetchUser(token);
    }
  }, [fetchUser]);

  return (
    <div className="flex flex-col h-screen">
      <Header />
      <main className="flex-grow container mx-auto p-6">
        <Dashboard />
      </main>
      <Footer />
    </div>
  );
}
