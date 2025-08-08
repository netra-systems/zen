'use client';

import { createContext, useContext, useEffect, ReactNode, useState, useCallback } from 'react';
import { User, AuthConfigResponse } from '@/types';
import { Button } from '@/components/ui/button';
import { getAuthConfig, handleLogin as authLogin, handleLogout as authLogout } from '@/services/auth';

interface AuthContextType {
  user: User | null;
  login: () => void;
  logout: () => void;
  loading: boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authConfig, setAuthConfig] = useState<AuthConfigResponse | null>(null);

  const fetchUser = useCallback(async () => {
    try {
      const data = await getAuthConfig();
      setAuthConfig(data);
      if (data.user) {
        setUser(data.user);
      } else if (data.development_mode) {
        authLogin(data);
      }
    } catch (error) { 
      console.error("Failed to fetch auth config:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = () => {
    authLogin(authConfig);
  };

  const logout = () => {
    authLogout(authConfig);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};