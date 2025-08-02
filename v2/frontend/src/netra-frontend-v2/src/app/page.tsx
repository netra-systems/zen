"use client";

import React from 'react';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Dashboard } from '@/components/Dashboard';

export default function App() {
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
