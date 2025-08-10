'use client';

import { createContext, useEffect, ReactNode, useState, useCallback } from 'react';
import { User } from '@/types';
import { AuthConfigResponse } from '@/auth';
import { Button } from '@/components/ui/button';
import { authService } from '@/auth';
import { jwtDecode } from 'jwt-decode';
import { useAuthStore } from '@/store/authStore';
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
  const authStore = useAuthStore();

  const syncAuthStore = useCallback((userData: User | null, tokenData: string | null) => {
    if (userData && tokenData) {
      authStore.login({
        id: userData.id || userData.sub || '',
        email: userData.email,
        name: userData.full_name || userData.name,
        role: userData.role
      }, tokenData);
    } else {
      authStore.logout();
    }
  }, []);

  const fetchAuthConfig = useCallback(async () => {
    try {
      const data = await authService.getAuthConfig();
      setAuthConfig(data);

      // Check for existing token first (from OAuth callback or storage)
      const storedToken = authService.getToken();
      
      if (storedToken) {
        // Use existing token
        setToken(storedToken);
        try {
          const decodedUser = jwtDecode(storedToken) as User;
          setUser(decodedUser);
          // Sync with Zustand store
          syncAuthStore(decodedUser, storedToken);
        } catch (e) {
          console.error("Invalid token:", e);
          authService.removeToken();
          syncAuthStore(null, null);
        }
      } else if (data.development_mode) {
        // Check if user explicitly logged out in dev mode
        const hasLoggedOut = authService.getDevLogoutFlag();
        
        if (!hasLoggedOut) {
          // Only auto-login if user hasn't explicitly logged out
          const devLoginResponse = await authService.handleDevLogin(data);
          if (devLoginResponse) {
            setToken(devLoginResponse.access_token);
            const decodedUser = jwtDecode(devLoginResponse.access_token) as User;
            setUser(decodedUser);
            // Sync with Zustand store
            syncAuthStore(decodedUser, devLoginResponse.access_token);
          }
        }
      }
    } catch (error) {
      console.error("Failed to fetch auth config:", error);
    } finally {
      setLoading(false);
    }
  }, [syncAuthStore]);

  useEffect(() => {
    fetchAuthConfig();
  }, [fetchAuthConfig]);

  const login = () => {
    if (authConfig) {
      // Clear dev logout flag when user manually logs in
      authService.clearDevLogoutFlag();
      authService.handleLogin(authConfig);
    }
  };

  const logout = async () => {
    if (authConfig) {
      // Set dev logout flag in development mode
      if (authConfig.development_mode) {
        authService.setDevLogoutFlag();
      }
      await authService.handleLogout(authConfig);
      // Clear Zustand store
      syncAuthStore(null, null);
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
