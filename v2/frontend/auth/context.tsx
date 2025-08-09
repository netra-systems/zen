'use client';

import { createContext, useEffect, ReactNode, useState, useCallback } from 'react';
import { User } from '@/types';
import { AuthConfigResponse } from '@/auth';
import { Button } from '@/components/ui/button';
import { authService } from '@/auth';

export interface AuthContextType {
  user: User | null;
  login: () => void;
  logout: () => void;
  loading: boolean;
  authConfig: AuthConfigResponse | null;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authConfig, setAuthConfig] = useState<AuthConfigResponse | null>(null);

  const fetchAuthConfig = useCallback(async () => {
    try {
      const data = await authService.getAuthConfig();
      setAuthConfig(data);
      if (data.user) {
        setUser(data.user);
      } else if (data.development_mode) {
        const devUser = await authService.handleDevLogin(data);
        if (devUser) {
          setUser(devUser);
        }
      }
    } catch (error) {
      console.error("Failed to fetch auth config:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAuthConfig();
  }, [fetchAuthConfig]);

  const login = () => {
    if (authConfig) {
      authService.handleLogin(authConfig);
    }
  };

  const logout = () => {
    if (authConfig) {
      authService.handleLogout(authConfig);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, authConfig }}>
      {children}
    </AuthContext.Provider>
  );
}
