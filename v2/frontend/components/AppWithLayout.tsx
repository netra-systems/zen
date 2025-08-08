'use client';

import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { cn } from '@/lib/utils';
import { AppWithLayoutProps } from '@/types';
import { useAppStore } from '@/store';

export function AppWithLayout({ children }: AppWithLayoutProps) {
  const { isSidebarCollapsed, toggleSidebar } = useAppStore();

  return (
    <div
      className={cn(
        'grid min-h-screen w-full',
        !isSidebarCollapsed && 'md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]'
      )}
    >
      {!isSidebarCollapsed && <Sidebar />}
      <div className="flex flex-col">
        <Header toggleSidebar={toggleSidebar} />
        <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
