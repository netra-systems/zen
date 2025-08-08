import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { AppWithLayout } from '@/components/AppWithLayout';
import { Providers } from '@/components/Providers';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { ChatProvider } from '@/contexts/ChatContext';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Netra',
  description: 'Autonomous AI agents for business process optimization',
};

const App = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  return (
    <WebSocketProvider userId={user?.id || ''}>
      <AppWithLayout>{children}</AppWithLayout>
    </WebSocketProvider>
  );
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          <AuthProvider>
            <ChatProvider>
              <App>{children}</App>
            </ChatProvider>
          </AuthProvider>
        </Providers>
      </body>
    </html>
  );
}