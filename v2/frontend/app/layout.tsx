'use client';

import './globals.css';
import { AuthProvider } from '@/contexts/AuthContext';
import { WebSocketProvider } from '@/app/providers/WebSocketProvider';
import { AppWithLayout } from '@/app/components/AppWithLayout';
import { RootLayoutProps } from '@/types/index';

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