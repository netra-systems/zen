
'use client';

import React, { ReactNode } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import LoginPage from '@/app/login/page';

interface AppWithLayoutProps {
  children: ReactNode;
}

export const AppWithLayout: React.FC<AppWithLayoutProps> = ({ children }) => {
  const { user } = useAuth();

  if (!user) {
    return <LoginPage />;
  }

  return <>{children}</>;
};
