'use client';

import { createContext, useContext, ReactNode, useState, useEffect, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import useAppStore from '@/store';
import config from '@/config';

interface User {
  email: string;
  // Add other user properties here
}

interface AuthContextType {
  user: User | null;
  login: () => void;
  logout: () => Promise<void>;
  handleAuthCallback: () => Promise<void>;
  fetchUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { setUser, user } = useAppStore();

  const login = () => {
    window.location.href = `${config.apiBaseUrl}/api/v3/auth/login`;
  };

  const logout = async () => {
    await fetch(`${config.apiBaseUrl}/api/v3/auth/logout`);
    setUser(null);
    router.push('/login');
  };

  const handleAuthCallback = async () => {
    try {
      const response = await fetch(`${config.apiBaseUrl}/api/v3/auth/get_user`);
      if (response.ok) {
        const user = await response.json();
        if (user && user.email) {
          setUser(user);
        }
        router.push('/');
      } else {
        router.push('/auth/error?message=Authentication failed');
      }
    } catch (error) {
      console.error('Authentication callback failed:', error);
      router.push('/auth/error?message=Authentication failed');
    }
  };

  const fetchUser = useCallback(async () => {
    if (user) return;
    try {
      const response = await fetch(`${config.apiBaseUrl}/api/v3/auth/get_user`);
      if (response.ok) {
        const userJson = await response.json();
        if (userJson && userJson.email) {
          setUser(userJson);
        }
      }
    } catch (error) {
      console.error('Failed to fetch user:', error);
    }
  }, [user, setUser]);

  useEffect(() => {
    const publicPaths = ['/login', '/auth/error', '/auth/callback'];
    if (!user && !publicPaths.includes(pathname)) {
      fetchUser();
    }
  }, [user, pathname, fetchUser]);

  const value = {
    user,
    login,
    logout,
    handleAuthCallback,
    fetchUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
