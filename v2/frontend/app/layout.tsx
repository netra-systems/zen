'use client';

import './globals.css';
import { AuthProvider } from '@/hooks/useAuth';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
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