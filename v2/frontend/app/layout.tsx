'use client';

import './globals.css';
import { AuthProvider } from '@/hooks/useAuth';
import { AppLayout } from '@/components/AppLayout';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <AppLayout>{children}</AppLayout>
        </AuthProvider>
      </body>
    </html>
  );
}