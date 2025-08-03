"use client";

import React, { useEffect } from 'react';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Dashboard } from '@/components/Dashboard';
import { useAppStore } from '@/store';

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
