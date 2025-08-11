'use client';

import { useEffect, useState } from 'react';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import { Header } from '@/components/Header';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/store';

interface AppWithLayoutProps {
  children: React.ReactNode;
}

export function AppWithLayout({ children }: AppWithLayoutProps) {
  const { isSidebarCollapsed, toggleSidebar } = useAppStore();
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  const showSidebar = isHydrated ? !isSidebarCollapsed : true;

  return (
    <div
      className={cn(
        'grid min-h-screen w-full',
        showSidebar && 'md:grid-cols-[320px_1fr]'
      )}
    >
      {showSidebar && <ChatSidebar />}
      <div className="flex flex-col">
        <Header toggleSidebar={toggleSidebar} />
        <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
