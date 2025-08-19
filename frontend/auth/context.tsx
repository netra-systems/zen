'use client';

import { createContext, useEffect, ReactNode, useState, useCallback } from 'react';
import { User } from '@/types';
import { AuthConfigResponse } from '@/auth';
import { Button } from '@/components/ui/button';
import { authService } from '@/auth';
import { jwtDecode } from 'jwt-decode';
import { useAuthStore } from '@/store/authStore';
import { logger } from '@/lib/logger';
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
        id: userData.id || (userData as any).sub || '',
        email: userData.email,
        full_name: userData.full_name || (userData as any).name,
        role: (userData as any).role
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
          logger.error('Invalid token detected', e as Error, {
            component: 'AuthContext',
            action: 'token_validation_failed'
          });
          authService.removeToken();
          syncAuthStore(null, null);
        }
      } else if (data.development_mode) {
        // Check if user explicitly logged out in dev mode
        const hasLoggedOut = authService.getDevLogoutFlag();
        logger.debug('Development mode detected', {
          component: 'AuthContext',
          action: 'dev_mode_check',
          metadata: { hasLoggedOut }
        });
        
        if (!hasLoggedOut) {
          // Only auto-login if user hasn't explicitly logged out
          logger.info('Attempting auto dev login', {
            component: 'AuthContext',
            action: 'auto_dev_login_attempt'
          });
          const devLoginResponse = await authService.handleDevLogin(data);
          if (devLoginResponse) {
            setToken(devLoginResponse.access_token);
            const decodedUser = jwtDecode(devLoginResponse.access_token) as User;
            setUser(decodedUser);
            // Sync with Zustand store
            syncAuthStore(decodedUser, devLoginResponse.access_token);
          }
        } else {
          logger.info('Skipping auto dev login - user has logged out', {
            component: 'AuthContext',
            action: 'auto_dev_login_skipped'
          });
        }
      }
    } catch (error) {
      logger.error('Failed to fetch auth config - backend may be offline', error as Error, {
        component: 'AuthContext',
        action: 'fetch_auth_config_failed'
      });
      
      // Graceful degradation - create offline auth config
      const offlineConfig: AuthConfigResponse = {
        development_mode: process.env.NODE_ENV === 'development',
        google_client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
        endpoints: {
          login: '/auth/login',
          logout: '/auth/logout',
          callback: '/auth/callback',
          token: '/auth/token',
          user: '/auth/me',
          ...(process.env.NODE_ENV === 'development' && { dev_login: '/auth/dev/login' })
        },
        authorized_javascript_origins: ['http://localhost:3000'],
        authorized_redirect_uris: ['http://localhost:3000/auth/callback']
      };
      
      setAuthConfig(offlineConfig);
      
      // In development mode with backend offline, allow proceeding without auth
      if (process.env.NODE_ENV === 'development') {
        logger.info('Backend offline - running in development mode without authentication', {
          component: 'AuthContext',
          action: 'offline_development_mode'
        });
      }
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
