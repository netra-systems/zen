'use client';

import { createContext, useContext, useEffect, ReactNode, useState, useCallback, useRef } from 'react';
import { User } from '@/types';
import { AuthConfigResponse } from '@/auth';
import { Button } from '@/components/ui/button';
import { unifiedAuthService } from '@/auth/unified-auth-service';
import { jwtDecode } from 'jwt-decode';
import { useAuthStore } from '@/store/authStore';
import { logger } from '@/lib/logger';
import { useGTMEvent } from '@/hooks/useGTMEvent';
import { monitorAuthState, createAtomicAuthUpdate, applyAtomicAuthUpdate, attemptEnhancedAuthRecovery } from '@/lib/auth-validation';
import { useUnifiedChatStore } from '@/store/unified-chat';
export interface AuthContextType {
  user: User | null;
  login: (forceOAuth?: boolean) => Promise<void> | void;
  logout: () => Promise<void>;
  loading: boolean;
  authConfig: AuthConfigResponse | null;
  token: string | null;
  initialized: boolean; // Track if auth initialization is complete
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
  // GTM event tracking
  const { trackLogin, trackLogout, trackOAuthComplete, trackError } = useGTMEvent();
  
  // Initialize token from localStorage immediately on mount
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false); // Track initialization completion
  
  // Initialization state machine - prevents race conditions during startup
  const initStateRef = useRef<'idle' | 'starting' | 'processing_token' | 'dev_login' | 'completed' | 'failed'>('idle');
  const initAttemptsRef = useRef(0);
  const MAX_INIT_ATTEMPTS = 3;
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
  const lastRefreshAttemptRef = useRef<number>(0);
  const refreshFailureCountRef = useRef<number>(0);
  const MAX_REFRESH_FAILURES = 3;
  const REFRESH_COOLDOWN_MS = 30000; // 30 seconds cooldown between refresh attempts

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
   * State machine helper for robust initialization
   */
  const transitionInitState = useCallback((
    newState: typeof initStateRef.current, 
    context?: string
  ) => {
    const oldState = initStateRef.current;
    initStateRef.current = newState;
    
    logger.debug('[INIT STATE] Transition', {
      component: 'AuthContext',
      action: 'init_state_transition',
      from: oldState,
      to: newState,
      context,
      attempt: initAttemptsRef.current + 1
    });
  }, []);

  /**
   * Check if we can proceed with initialization step
   */
  const canProceedWithInit = useCallback(() => {
    if (initAttemptsRef.current >= MAX_INIT_ATTEMPTS) {
      logger.error('[INIT STATE] Max initialization attempts reached', {
        attempts: initAttemptsRef.current,
        state: initStateRef.current
      });
      return false;
    }
    return initStateRef.current !== 'completed';
  }, []);

  /**
   * Automatically refresh token if needed with loop prevention
   */
  const handleTokenRefresh = useCallback(async (currentToken: string) => {
    // Check if we're already refreshing
    if (isRefreshingRef.current) {
      logger.debug('Token refresh already in progress, skipping', {
        component: 'AuthContext',
        action: 'refresh_skipped'
      });
      return;
    }

    // Check if we've hit the max failure limit
    if (refreshFailureCountRef.current >= MAX_REFRESH_FAILURES) {
      logger.error('Max refresh failures reached, stopping refresh attempts', {
        component: 'AuthContext',
        failures: refreshFailureCountRef.current
      });
      // Clear token and redirect to login
      unifiedAuthService.removeToken();
      setToken(null);
      setUser(null);
      // Explicitly pass null values to ensure consistency
      syncAuthStore(null, null);
      return;
    }

    // Check cooldown period
    const now = Date.now();
    const timeSinceLastAttempt = now - lastRefreshAttemptRef.current;
    if (timeSinceLastAttempt < REFRESH_COOLDOWN_MS) {
      logger.debug('Refresh cooldown active, skipping', {
        component: 'AuthContext',
        cooldownRemaining: REFRESH_COOLDOWN_MS - timeSinceLastAttempt
      });
      return;
    }

    if (!unifiedAuthService.needsRefresh(currentToken)) {
      return;
    }

    isRefreshingRef.current = true;
    lastRefreshAttemptRef.current = now;
    logger.info('Attempting automatic token refresh', {
      component: 'AuthContext',
      action: 'auto_refresh_start',
      attempt: refreshFailureCountRef.current + 1
    });

    try {
      const refreshResult = await unifiedAuthService.refreshToken();
      if (refreshResult) {
        const newToken = refreshResult.access_token;
        
        // Check if we got a different token (prevent same-token loop)
        if (newToken === currentToken) {
          logger.warn('Refresh returned same token, potential loop detected', {
            component: 'AuthContext',
            action: 'same_token_refresh'
          });
          refreshFailureCountRef.current++;
        } else {
          // Reset failure count on successful refresh with new token
          refreshFailureCountRef.current = 0;
          
          const decodedUser = jwtDecode(newToken) as User;
          
          // Update all auth state atomically using atomic helper
          const atomicUpdate = createAtomicAuthUpdate(newToken, decodedUser);
          const updateSuccess = applyAtomicAuthUpdate(
            atomicUpdate, 
            setToken, 
            setUser, 
            syncAuthStore
          );
          
          if (!updateSuccess) {
            logger.error('Failed to apply atomic auth update during refresh');
            refreshFailureCountRef.current++;
            return;
          }
          
          logger.info('Automatic token refresh successful', {
            component: 'AuthContext',
            action: 'auto_refresh_success'
          });
        }
      } else {
        logger.warn('Token refresh returned null response', {
          component: 'AuthContext',
          action: 'auto_refresh_null_response'
        });
        refreshFailureCountRef.current++;
      }
    } catch (error) {
      logger.error('Automatic token refresh failed', error as Error, {
        component: 'AuthContext',
        action: 'auto_refresh_failed'
      });
      refreshFailureCountRef.current++;
      // Don't logout immediately - let the user continue with potentially expired token
    } finally {
      isRefreshingRef.current = false;
    }
  }, [syncAuthStore]);

  /**
   * Schedule automatic token refresh check - environment-aware timing
   */
  const scheduleTokenRefreshCheck = useCallback((tokenToCheck: string) => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
    }

    // Dynamic check interval based on token lifetime
    let checkInterval;
    try {
      const decoded = jwtDecode(tokenToCheck) as any;
      if (decoded.exp && decoded.iat) {
        const tokenLifetime = (decoded.exp - decoded.iat) * 1000;
        if (tokenLifetime < 5 * 60 * 1000) { // Short tokens (< 5 minutes)
          // Check every 10 seconds for short tokens
          checkInterval = 10 * 1000;
        } else {
          // Check every 2 minutes for normal tokens
          checkInterval = 2 * 60 * 1000;
        }
      } else {
        // Default to 2 minutes if can't determine token lifetime
        checkInterval = 2 * 60 * 1000;
      }
    } catch (error) {
      // Default to 2 minutes if token parsing fails
      checkInterval = 2 * 60 * 1000;
      logger.debug('Failed to parse token for refresh scheduling', error as Error);
    }

    refreshTimeoutRef.current = setTimeout(() => {
      handleTokenRefresh(tokenToCheck);
      scheduleTokenRefreshCheck(tokenToCheck);
    }, checkInterval);
    
    logger.debug('Scheduled token refresh check', {
      checkInterval: Math.floor(checkInterval / 1000),
      component: 'AuthContext',
      action: 'schedule_refresh_check'
    });
  }, [handleTokenRefresh]);

  const fetchAuthConfig = useCallback(async () => {
    // Check if we can proceed with initialization
    if (!canProceedWithInit()) {
      return;
    }

    // Start initialization
    transitionInitState('starting', 'fetchAuthConfig_begin');
    initAttemptsRef.current += 1;

    // Track the actual user that will be set for monitoring
    let actualUser: User | null = null;
    let actualToken: string | null = token;
    
    try {
      const data = await unifiedAuthService.getAuthConfig();
      setAuthConfig(data);

      // Check for existing token first (from OAuth callback or storage)
      // But prefer the token already in state if it exists (from initialization)
      const currentToken = token;
      const storedToken = currentToken || unifiedAuthService.getToken();
      actualToken = storedToken;
      
      if (storedToken) {
        // Process the token if we have one
        transitionInitState('processing_token', 'stored_token_found');
        
        // Update token if different from state
        if (storedToken !== currentToken) {
          setToken(storedToken);
        }
        
        // CRITICAL FIX: Always process the token to restore user state
        // This ensures user is set on page refresh when token exists in localStorage
        // Process token regardless of whether it was already in state
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
              actualUser = null;
              actualToken = null;
            }
          } else {
            // CRITICAL: Always set user even if token was already in state
            // This fixes the page refresh logout issue
            setUser(decodedUser);
            actualUser = decodedUser; // Track the user we're setting
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
          actualUser = null;
          actualToken = null;
        }
      } else if (data.development_mode && !data.oauth_enabled) {
        // Only auto-login with dev credentials if OAuth is NOT configured
        // If OAuth is configured, let the user choose to login manually
        const hasLoggedOut = unifiedAuthService.getDevLogoutFlag();
        logger.debug('Development mode detected (OAuth not configured)', {
          component: 'AuthContext',
          action: 'dev_mode_check',
          metadata: { hasLoggedOut, oauth_enabled: data.oauth_enabled }
        });
        
        if (!hasLoggedOut) {
          // Only auto-login if user hasn't explicitly logged out AND OAuth is not available
          transitionInitState('dev_login', 'auto_dev_login_attempt');
          
          logger.info('Attempting auto dev login (OAuth not available)', {
            component: 'AuthContext',
            action: 'auto_dev_login_attempt'
          });
          
          try {
            // Wrap dev login with timeout to prevent hanging
            const devLoginPromise = unifiedAuthService.handleDevLogin(data);
            const timeoutPromise = new Promise<null>((_, reject) => {
              setTimeout(() => reject(new Error('Dev login timeout')), 8000); // 8 second timeout
            });
            
            const devLoginResponse = await Promise.race([devLoginPromise, timeoutPromise]);
            if (devLoginResponse) {
              setToken(devLoginResponse.access_token);
              actualToken = devLoginResponse.access_token;
              const decodedUser = jwtDecode(devLoginResponse.access_token) as User;
              setUser(decodedUser);
              actualUser = decodedUser; // Track the user we're setting
              // Sync with Zustand store
              syncAuthStore(decodedUser, devLoginResponse.access_token);
              // Start automatic token refresh cycle
              scheduleTokenRefreshCheck(devLoginResponse.access_token);
              // Track successful auto-login
              trackLogin('email', false);
            }
          } catch (devLoginError) {
            logger.warn('Auto dev login failed or timed out', devLoginError as Error, {
              component: 'AuthContext',
              action: 'auto_dev_login_timeout'
            });
            // Continue with initialization even if dev login fails
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
      transitionInitState('failed', 'auth_config_fetch_error');
      
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
      // Mark as completed regardless of success/failure
      if (initStateRef.current !== 'failed' || initAttemptsRef.current >= MAX_INIT_ATTEMPTS) {
        transitionInitState('completed', 'auth_init_finally');
        setLoading(false);
        setInitialized(true); // Mark initialization as complete
      }
      
      logger.info('[AUTH INIT] Auth context initialization finished', {
        component: 'AuthContext',
        action: 'init_finished',
        hasUser: !!actualUser,
        hasToken: !!actualToken,
        initialized: true,
        initState: initStateRef.current,
        attempt: initAttemptsRef.current,
        timestamp: new Date().toISOString()
      });
      
      // Monitor auth state for consistency - use actual values that were set
      monitorAuthState(actualToken, actualUser, true, 'auth_init_complete');
    }
  }, [syncAuthStore, scheduleTokenRefreshCheck, handleTokenRefresh, token, canProceedWithInit, transitionInitState]);

  const hasMountedRef = useRef(false);

  useEffect(() => {
    // Prevent multiple initialization calls
    if (hasMountedRef.current) {
      return;
    }
    hasMountedRef.current = true;

    // Only fetch auth config once on mount
    fetchAuthConfig();
    
    // Listen for storage events to detect token changes from OAuth callback
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'jwt_token' && e.newValue) {
        logger.info('Detected token change via storage event', {
          component: 'AuthContext',
          action: 'storage_token_detected'
        });
        
        // Update token immediately when detected via storage event
        try {
          const decodedUser = jwtDecode(e.newValue) as User;
          
          // Update state atomically using atomic helper
          const atomicUpdate = createAtomicAuthUpdate(e.newValue, decodedUser);
          const updateSuccess = applyAtomicAuthUpdate(
            atomicUpdate, 
            setToken, 
            setUser, 
            syncAuthStore
          );
          
          if (updateSuccess) {
            scheduleTokenRefreshCheck(e.newValue);
          } else {
            logger.error('Failed to apply atomic auth update from storage event');
          }
        } catch (error) {
          logger.error('Failed to decode token from storage event', error as Error);
        }
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    
    // Cleanup on unmount
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
      hasMountedRef.current = false;
    };
  }, []); // Remove dependencies to prevent re-runs

  const login = async (forceOAuth: boolean = false) => {
    try {
      if (authConfig) {
        // Clear dev logout flag when user manually logs in
        unifiedAuthService.clearDevLogoutFlag();
        
        // In development mode, prefer OAuth when it's configured
        // Only use dev login when OAuth is explicitly disabled or not configured
        if (authConfig.development_mode && !authConfig.oauth_enabled && !forceOAuth) {
          logger.info('Using dev login in development mode (OAuth not configured)');
          const result = await unifiedAuthService.handleDevLogin(authConfig);
          if (result) {
            // Dev login successful, token is already set by handleDevLogin
            // Trigger a re-fetch of user data
            const userResponse = await fetch(authConfig.endpoints.user, {
              headers: {
                'Authorization': `Bearer ${result.access_token}`,
                'Accept': 'application/json',
              },
            });
            
            if (userResponse.ok) {
              const userData = await userResponse.json();
              setUser(userData);
              syncAuthStore(userData, result.access_token);
              trackLogin('dev', true);
              // Force a re-initialization to ensure all components get updated
              setInitialized(true);
            }
          } else {
            logger.error('Dev login failed');
            trackError('auth_dev_login_error', 'Dev login failed', 'AuthContext', false);
          }
        } else {
          // Use OAuth for:
          // 1. Production/staging mode
          // 2. Development mode when OAuth is configured and enabled
          // 3. When explicitly requested via forceOAuth parameter
          logger.info('Using OAuth login', { 
            environment: authConfig.development_mode ? 'development' : 'production',
            oauth_enabled: authConfig.oauth_enabled,
            forceOAuth
          });
          unifiedAuthService.handleLogin(authConfig);
          // Track login attempt (OAuth flow will be tracked separately)
          trackLogin('oauth', false);
        }
      }
    } catch (error) {
      logger.error('Login error in AuthContext', error as Error, {
        component: 'AuthContext',
        action: 'login_error'
      });
      // Track login error
      trackError('auth_login_error', error instanceof Error ? error.message : 'Login failed', 'AuthContext', false);
      throw error; // Re-throw so components can catch it
    }
  };

  const logout = async () => {
    logger.info('[LOGOUT] Starting comprehensive logout process', {
      component: 'AuthContext',
      hasAuthConfig: !!authConfig
    });

    try {
      // Track logout event
      trackLogout();
      
      // Set dev logout flag in development mode
      if (authConfig?.development_mode) {
        unifiedAuthService.setDevLogoutFlag();
      }

      // Clear all chat-related state with comprehensive reset
      const chatStore = useUnifiedChatStore.getState();
      chatStore.resetStore(); // Complete reset of all chat state

      // Clear additional localStorage items
      if (typeof window !== 'undefined') {
        // Clear all auth and chat related items
        const itemsToRemove = [
          'jwt_token',
          'refresh_token',
          'user_data',
          'user_preferences',
          'active_thread_id',
          'chat_history',
          'session_id',
          'dev_logout_performed'
        ];
        
        itemsToRemove.forEach(item => {
          try {
            localStorage.removeItem(item);
          } catch (e) {
            logger.warn(`Failed to remove ${item} from localStorage`, e as Error);
          }
        });

        // Clear sessionStorage
        try {
          sessionStorage.clear();
        } catch (e) {
          logger.warn('Failed to clear sessionStorage', e as Error);
        }
      }

      // Attempt backend logout (but don't fail if it errors)
      if (authConfig) {
        try {
          await unifiedAuthService.handleLogout(authConfig);
        } catch (error) {
          logger.error('[LOGOUT] Backend logout failed, continuing with local cleanup', error as Error);
        }
      }
      
      // Clear auth state in context
      setUser(null);
      setToken(null);
      
      // Clear Zustand auth store
      syncAuthStore(null, null);
      
      // Cancel any pending token refresh
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
        refreshTimeoutRef.current = null;
      }

      logger.info('[LOGOUT] Logout process completed successfully', {
        component: 'AuthContext'
      });
      
      // Navigate to login page
      if (typeof window !== 'undefined') {
        // Use window.location for a full page refresh to ensure clean state
        window.location.href = '/login';
      }
    } catch (error) {
      logger.error('[LOGOUT] Error during logout process', error as Error, {
        component: 'AuthContext'
      });
      
      // Even on error, ensure we clear local state and redirect
      setUser(null);
      setToken(null);
      syncAuthStore(null, null);
      
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, authConfig, token, initialized }}>
      {children}
    </AuthContext.Provider>
  );
}
