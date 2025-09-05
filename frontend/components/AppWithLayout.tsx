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
