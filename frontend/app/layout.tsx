
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { AppWithLayout } from '@/components/AppWithLayout';
import { AuthProvider } from '@/auth';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { GTMProvider } from '@/providers/GTMProvider';
// import { SentryInit } from './sentry-init'; // Temporarily disabled for demo
import './globals.css';
import '@/styles/glassmorphism.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Netra Beta',
  description: 'Autonomous AI agents for business process optimization - Beta Program',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className}`}>
        {/* <SentryInit /> Temporarily disabled for demo */}
        <GTMProvider enabled={process.env.NEXT_PUBLIC_GTM_ENABLED !== 'false' && process.env.NODE_ENV !== 'test'}>
          <AuthProvider>
            <WebSocketProvider>
              <AppWithLayout>{children}</AppWithLayout>
            </WebSocketProvider>
          </AuthProvider>
        </GTMProvider>
      </body>
    </html>
  );
}
