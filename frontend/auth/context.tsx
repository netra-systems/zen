'use client';

import { createContext, useContext, useEffect, ReactNode, useState, useCallback, useRef } from 'react';
import { User } from '@/types';
import { AuthConfigResponse } from '@/auth';
import { Button } from '@/components/ui/button';
import { unifiedAuthService } from '@/auth/unified-auth-service';
import { jwtDecode } from 'jwt-decode';
import { useAuthStore } from '@/store/authStore';
import { logger } from '@/lib/logger';
export interface AuthContextType {
  user: User | null;
  login: () => Promise<void> | void;
  logout: () => Promise<void>;
  loading: boolean;
  authConfig: AuthConfigResponse | null;
  token: string | null;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Hook to access auth context
 * This is the primary way components should access authentication state
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // Initialize token from localStorage immediately on mount
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authConfig, setAuthConfig] = useState<AuthConfigResponse | null>(null);
  const [token, setToken] = useState<string | null>(() => {
    // Check for token in localStorage during initial state creation
    if (typeof window !== 'undefined') {
      const storedToken = localStorage.getItem('jwt_token');
      if (storedToken) {
        logger.debug('Found token in localStorage during AuthProvider initialization', {
          component: 'AuthContext',
          action: 'init_token_from_storage'
        });
        return storedToken;
      }
    }
    return null;
  });
  const authStore = useAuthStore();
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isRefreshingRef = useRef(false);

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
  }, [authStore]);

  /**
   * Automatically refresh token if needed
   */
  const handleTokenRefresh = useCallback(async (currentToken: string) => {
    if (isRefreshingRef.current) {
      logger.debug('Token refresh already in progress, skipping', {
        component: 'AuthContext',
        action: 'refresh_skipped'
      });
      return;
    }

    if (!unifiedAuthService.needsRefresh(currentToken)) {
      return;
    }

    isRefreshingRef.current = true;
    logger.info('Attempting automatic token refresh', {
      component: 'AuthContext',
      action: 'auto_refresh_start'
    });

    try {
      const refreshResult = await unifiedAuthService.refreshToken();
      if (refreshResult) {
        const newToken = refreshResult.access_token;
        setToken(newToken);
        
        const decodedUser = jwtDecode(newToken) as User;
        setUser(decodedUser);
        syncAuthStore(decodedUser, newToken);
        
        logger.info('Automatic token refresh successful', {
          component: 'AuthContext',
          action: 'auto_refresh_success'
        });
      } else {
        logger.warn('Token refresh returned null response', {
          component: 'AuthContext',
          action: 'auto_refresh_null_response'
        });
      }
    } catch (error) {
      logger.error('Automatic token refresh failed', error as Error, {
        component: 'AuthContext',
        action: 'auto_refresh_failed'
      });
      // Don't logout immediately - let the user continue with potentially expired token
    } finally {
      isRefreshingRef.current = false;
    }
  }, [syncAuthStore]);

  /**
   * Schedule automatic token refresh check
   */
  const scheduleTokenRefreshCheck = useCallback((tokenToCheck: string) => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
    }

    // Check every 2 minutes for token refresh needs
    refreshTimeoutRef.current = setTimeout(() => {
      handleTokenRefresh(tokenToCheck);
      scheduleTokenRefreshCheck(tokenToCheck);
    }, 2 * 60 * 1000);
  }, [handleTokenRefresh]);

  const fetchAuthConfig = useCallback(async () => {
    try {
      const data = await unifiedAuthService.getAuthConfig();
      setAuthConfig(data);

      // Check for existing token first (from OAuth callback or storage)
      // But prefer the token already in state if it exists (from initialization)
      const currentToken = token;
      const storedToken = currentToken || unifiedAuthService.getToken();
      
      if (storedToken && storedToken !== currentToken) {
        // Update token if different from state
        setToken(storedToken);
        try {
          const decodedUser = jwtDecode(storedToken) as User;
          
          // Check if token is expired
          const now = Date.now() / 1000;
          if (decodedUser.exp && decodedUser.exp < now) {
            logger.warn('Stored token is expired', {
              component: 'AuthContext',
              action: 'expired_token_detected',
              expiry: decodedUser.exp,
              now
            });
            
            // Try to refresh token if possible
            try {
              await handleTokenRefresh(storedToken);
            } catch (refreshError) {
              logger.warn('Could not refresh expired token', refreshError as Error);
              unifiedAuthService.removeToken();
              syncAuthStore(null, null);
            }
          } else {
            setUser(decodedUser);
            // Sync with Zustand store
            syncAuthStore(decodedUser, storedToken);
            // Start automatic token refresh cycle
            scheduleTokenRefreshCheck(storedToken);
          }
        } catch (e) {
          logger.error('Invalid token detected', e as Error, {
            component: 'AuthContext',
            action: 'token_validation_failed'
          });
          unifiedAuthService.removeToken();
          syncAuthStore(null, null);
        }
      } else if (data.development_mode) {
        // Check if user explicitly logged out in dev mode
        const hasLoggedOut = unifiedAuthService.getDevLogoutFlag();
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
          const devLoginResponse = await unifiedAuthService.handleDevLogin(data);
          if (devLoginResponse) {
            setToken(devLoginResponse.access_token);
            const decodedUser = jwtDecode(devLoginResponse.access_token) as User;
            setUser(decodedUser);
            // Sync with Zustand store
            syncAuthStore(decodedUser, devLoginResponse.access_token);
            // Start automatic token refresh cycle
            scheduleTokenRefreshCheck(devLoginResponse.access_token);
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
  }, [syncAuthStore, scheduleTokenRefreshCheck, handleTokenRefresh]);

  useEffect(() => {
    // Only fetch auth config once on mount, not when dependencies change
    fetchAuthConfig();
    
    // Cleanup timeout on unmount
    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, []); // Empty dependency array to prevent re-fetching on dependency changes

  const login = async () => {
    try {
      if (authConfig) {
        // Clear dev logout flag when user manually logs in
        unifiedAuthService.clearDevLogoutFlag();
        unifiedAuthService.handleLogin(authConfig);
      }
    } catch (error) {
      logger.error('Login error in AuthContext', error as Error, {
        component: 'AuthContext',
        action: 'login_error'
      });
      throw error; // Re-throw so components can catch it
    }
  };

  const logout = async () => {
    if (authConfig) {
      // Set dev logout flag in development mode
      if (authConfig.development_mode) {
        unifiedAuthService.setDevLogoutFlag();
      }
      await unifiedAuthService.handleLogout(authConfig);
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
