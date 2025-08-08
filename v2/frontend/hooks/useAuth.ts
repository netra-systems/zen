'use client';

import { createContext, useContext, ReactNode, useState, useEffect, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import useAppStore from '@/store';
import config from '@/config';

interface User {
  email: string;
  full_name: string;
  picture: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: () => void;
  logout: () => Promise<void>;
  fetchUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { setUser, user, setToken, token } = useAppStore();
  const [authConfig, setAuthConfig] = useState(null);

  useEffect(() => {
    const fetchAuthConfig = async () => {
      try {
        const response = await fetch(`${config.apiBaseUrl}/api/v3/auth/config`);
        const data = await response.json();
        setAuthConfig(data);
        if (data.development_mode) {
          setUser(data.dev_user);
          setToken(data.dev_token);
        }
      } catch (error) {
        console.error('Failed to fetch auth config:', error);
      }
    };
    fetchAuthConfig();
  }, [setUser, setToken]);

  const login = () => {
    if (authConfig) {
      window.location.href = authConfig.endpoints.login_url;
    }
  };

  const logout = async () => {
    if (authConfig) {
      await fetch(authConfig.endpoints.logout_url);
      setUser(null);
      setToken(null);
      router.push('/login');
    }
  };

  const fetchUser = useCallback(async () => {
    if (user || !authConfig) return;
    try {
      const response = await fetch(authConfig.endpoints.user_info_url);
      if (response.ok) {
        const userJson = await response.json();
        if (userJson && userJson.email) {
          setUser(userJson);
        }
      }
    } catch (error) {
      console.error('Failed to fetch user:', error);
    }
  }, [user, setUser, authConfig]);

  useEffect(() => {
    const publicPaths = ['/login', '/auth/error', '/auth/callback'];
    if (!user && !publicPaths.includes(pathname)) {
      fetchUser();
    }
  }, [user, pathname, fetchUser]);

  const value = {
    user,
    token,
    login,
    logout,
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