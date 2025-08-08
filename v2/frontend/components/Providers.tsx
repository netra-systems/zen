'use client';

import { useMemo, type ReactNode } from 'react';
import { AuthProvider } from '@/contexts/AuthContext';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
import { useAuth } from '@/hooks/useAuth';
import { WEBSOCKET_URL } from '@/config';

export function Providers({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const socketUrl = useMemo(() => {
    if (user?.id) {
      return WEBSOCKET_URL.replace('{user_id}', user.id);
    }
    return null;
  }, [user]);

  return (
    <AuthProvider>
      <WebSocketProvider url={socketUrl}>
        {children}
      </WebSocketProvider>
    </AuthProvider>
  );
}
