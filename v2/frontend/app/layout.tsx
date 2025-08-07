
'use client';

import './globals.css';
import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { AuthProvider, useAuth } from '@/providers/auth';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { cn } from '@/lib/utils';

import { RootLayoutProps, AppWithLayoutProps } from './types';

export function AppWithLayout({ children }: AppWithLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const { user } = useAuth();
  const pathname = usePathname();

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const publicPaths = ['/login', '/auth/error', '/auth/callback'];
  const isPublicPath = publicPaths.includes(pathname);

  if (!user && !isPublicPath) {
    return null; // Or a loading spinner
  }

  return (
    <div
      className={cn(
        'grid min-h-screen w-full',
        isSidebarOpen && user && !isPublicPath && 'md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]'
      )}
    >
      {isSidebarOpen && user && !isPublicPath && <Sidebar />}
      <div className="flex flex-col">
        {user && !isPublicPath && <Header toggleSidebar={toggleSidebar} />}
        <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" suppressHydrationWarning={true}>
      <body>
        <AuthProvider>
          <AppWithLayout>{children}</AppWithLayout>
        </AuthProvider>
      </body>
    </html>
  );
}
