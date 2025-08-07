
'use client';

import './globals.css';
import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { AuthProvider, useAuth } from '@/hooks/useAuth';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { cn } from '@/lib/utils';

export function AppWithLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const pathname = usePathname();
  const { isAuthenticated, isAuthReady } = useAuth(); // Get isAuthReady

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const isLoginPage = pathname === '/login';

  // Wait for auth to be ready before rendering auth-dependent UI
  if (!isAuthReady) {
    return null; // Or a loading spinner
  }

  if (!isAuthenticated && !isLoginPage) {
    return <>{children}</>;
  }

  if (isLoginPage) {
    return <>{children}</>;
  }

  return (
    <div
      className={cn(
        'grid min-h-screen w-full',
        isSidebarOpen && 'md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]'
      )}
    >
      {isSidebarOpen && <Sidebar />}
      <div className="flex flex-col">
        <Header toggleSidebar={toggleSidebar} />
        <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <AppWithLayout>{children}</AppWithLayout>
        </AuthProvider>
      </body>
    </html>
  );
}
