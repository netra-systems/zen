'use client';

import './globals.css';
import { AuthProvider } from '@/contexts/AuthContext';

import { AppWithLayout } from '@/app/components/AppWithLayout';
import { RootLayoutProps } from '@/types';

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" suppressHydrationWarning={true}>
      <body>
        <AuthProvider>
          <AppWithLayout>{children}</AppWithLayout>
        </AuthProvider>
      </body>
    </html>
  );
}