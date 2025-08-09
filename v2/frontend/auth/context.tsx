'use client';

import { createContext, useEffect, ReactNode, useState, useCallback } from 'react';
import { User } from '@/types/User';
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
        // In development mode, if there's no user, we can try to log in automatically.
        // The backend will create a dev user if one doesn't exist.
        authService.handleLogin(data);
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
