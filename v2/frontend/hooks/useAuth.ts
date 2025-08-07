'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import useAppStore from '@/store';
import { getToken } from '@/lib/user';

export function useAuth() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, fetchUser, devLogin, isLoading } = useAppStore();

  useEffect(() => {
    const token = getToken();
    if (token && !user) {
      fetchUser(token);
    } else if (!token && !user && process.env.NODE_ENV === 'development') {
      devLogin();
    }
  }, [user, fetchUser, devLogin]);

  useEffect(() => {
    if (!isLoading && !user && pathname !== '/login') {
      router.push('/login');
    }
  }, [user, isLoading, pathname, router]);

  return { user, isLoading };
}
