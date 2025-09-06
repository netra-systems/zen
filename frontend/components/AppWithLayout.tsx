'use client';

import { useEffect, useState } from 'react';
import { StatsigProvider, useClientAsyncInit } from '@statsig/react-bindings';
import { StatsigAutoCapturePlugin } from '@statsig/web-analytics';
import { StatsigSessionReplayPlugin } from '@statsig/session-replay';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import { Header } from '@/components/Header';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/store';
import { useAuth } from '@/auth/context';

interface AppWithLayoutProps {
  children: React.ReactNode;
}

function AppWithLayoutContent({ children }: AppWithLayoutProps) {
  const { isSidebarCollapsed, toggleSidebar } = useAppStore();
  // Initialize hydration state immediately to prevent flicker
  const [isHydrated, setIsHydrated] = useState(true);

  // Use the actual sidebar state without hydration check to prevent jumping
  const showSidebar = !isSidebarCollapsed;

  return (
    <div
      className={cn(
        'grid h-screen w-full overflow-hidden',
        showSidebar && 'md:grid-cols-[320px_1fr]'
      )}
    >
      {showSidebar && <ChatSidebar />}
      <div className="flex flex-col h-full overflow-hidden">
        <Header toggleSidebar={toggleSidebar} />
        <main className="flex flex-1 flex-col overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}

function AppWithStatsig({ children }: AppWithLayoutProps) {
  const { user } = useAuth();
  const id = user?.id || 'a-user';
  const { client } = useClientAsyncInit(
    'client-d2wo3z15FpMFpF3UWspyfq3XDRZ3cOvETBtm9RJHeo5',
    { userID: id },
    { plugins: [new StatsigAutoCapturePlugin(), new StatsigSessionReplayPlugin()] }
  );

  return (
    <StatsigProvider client={client} loadingComponent={<div>Loading...</div>}>
      <AppWithLayoutContent>{children}</AppWithLayoutContent>
    </StatsigProvider>
  );
}

export function AppWithLayout({ children }: AppWithLayoutProps) {
  return <AppWithStatsig>{children}</AppWithStatsig>;
}
