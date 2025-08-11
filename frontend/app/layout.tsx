
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { AppWithLayout } from '@/components/AppWithLayout';
import { AuthProvider } from '@/auth';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Netra',
  description: 'Autonomous AI agents for business process optimization',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <AuthProvider>
          <WebSocketProvider>
            <AppWithLayout>{children}</AppWithLayout>
          </WebSocketProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
