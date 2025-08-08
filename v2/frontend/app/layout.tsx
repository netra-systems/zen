'use client';

import './globals.css';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
import { AuthProvider } from '@/contexts/AuthContext';

import { AppWithLayout } from '@/components/AppWithLayout';
import { RootLayoutProps } from '@/types';

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" suppressHydrationWarning={true}>
      <body>
        <AuthProvider>
          <WebSocketProvider>
            <AppWithLayout>{children}</AppWithLayout>
          </WebSocketProvider>
        </AuthProvider>
      </body>
    </html>
  );
}