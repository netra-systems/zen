
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
  authConfig: AuthConfigResponse | null;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authConfig, setAuthConfig] = useState<AuthConfigResponse | null>(null);

  const fetchAuthConfig = useCallback(async () => {
    try {
      const data = await getAuthConfig();
      setAuthConfig(data);
      if (data.user) {
        setUser(data.user);
      } else if (data.development_mode) {
        // In development mode, if there's no user, we can try to log in automatically.
        // The backend will create a dev user if one doesn't exist.
        authLogin(data);
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
      authLogin(authConfig);
    }
  };

  const logout = () => {
    if (authConfig) {
      authLogout(authConfig);
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

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
