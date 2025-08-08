import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { AppWithLayout } from '@/components/AppWithLayout';
import { AuthProvider } from '@/contexts/AuthContext';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
import { useAuth } from '@/hooks/useAuth';
import { WEBSOCKET_URL } from '@/config';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Netra',
  description: 'Autonomous AI agents for business process optimization',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const socketUrl = useMemo(() => {
    if (user?.id) {
      return WEBSOCKET_URL.replace('{user_id}', user.id);
    }
    return null;
  }, [user]);

  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <AuthProvider>
          <WebSocketProvider url={socketUrl}>
            <AppWithLayout>{children}</AppWithLayout>
          </WebSocketProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
