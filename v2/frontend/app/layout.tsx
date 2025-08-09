
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { AppWithLayout } from '@/components/AppWithLayout';
import { Providers } from '@/components/Providers';
import { AuthProvider } from '@/auth';
import { ChatProvider } from '@/contexts/ChatContext';
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
          <Providers>
            <ChatProvider>
              <AppWithLayout>{children}</AppWithLayout>
            </ChatProvider>
          </Providers>
        </AuthProvider>
      </body>
    </html>
  );
}
