'use client';

import './globals.css';
import { AuthProvider } from '@/hooks/useAuth';
import { AppLayout } from '@/app/components/AppLayout';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <AppLayout>{children}</AppLayout>
    </AuthProvider>
  );
}