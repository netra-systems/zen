'use client';

import { createContext, useEffect, ReactNode, useState, useCallback } from 'react';
import { User } from '@/types';
import { AuthConfigResponse } from '@/auth';
import { Button } from '@/components/ui/button';
import { authService } from '@/auth';
import { jwtDecode } from 'jwt-decode';
export interface AuthContextType {
  user: User | null;
  login: () => void;
  logout: () => void;
  loading: boolean;
  authConfig: AuthConfigResponse | null;
  token: string | null;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authConfig, setAuthConfig] = useState<AuthConfigResponse | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const fetchAuthConfig = useCallback(async () => {
    try {
      const data = await authService.getAuthConfig();
      setAuthConfig(data);

      const storedToken = authService.getToken();
      if (storedToken) {
        setToken(storedToken);
        const decodedUser = jwtDecode(storedToken) as User;
        setUser(decodedUser);
      } else if (data.development_mode) {
        const devLoginResponse = await authService.handleDevLogin(data);
        if (devLoginResponse) {
          setToken(devLoginResponse.access_token);
          const decodedUser = jwtDecode(devLoginResponse.access_token) as User;
          setUser(decodedUser);
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
    <AuthContext.Provider value={{ user, login, logout, loading, authConfig, token }}>
      {children}
    </AuthContext.Provider>
  );
}
