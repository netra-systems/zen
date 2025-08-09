'use client';

import { useMemo, type ReactNode } from 'react';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
;
import { config } from '@/config';
import { authService } from '@/services/auth';

export function Providers({ children }: { children: ReactNode }) {
  const { user } = authService.useAuth();
  const socketUrl = useMemo(() => {
    if (user?.id) {
      return config.wsUrl.replace('{user_id}', user.id);
    }
    return null;
  }, [user]);

  return (
      <WebSocketProvider url={socketUrl}>
        {children}
      </WebSocketProvider>
  );
}