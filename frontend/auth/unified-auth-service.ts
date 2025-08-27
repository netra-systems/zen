/**
 * Unified Auth Service
 * Single source of truth for authentication operations
 * Uses unified configuration for clear environment handling
 */

import { AuthConfigResponse } from './types';
import { authServiceClient } from '@/lib/auth-service-client';
import { unifiedApiConfig } from '@/lib/unified-api-config';
import { logger } from '@/lib/logger';
import { jwtDecode } from 'jwt-decode';

const TOKEN_KEY = 'jwt_token';
const DEV_LOGOUT_FLAG = 'dev_logout_flag';
const REFRESH_THRESHOLD_MS = 5 * 60 * 1000; // Refresh 5 minutes before expiry

interface JWTPayload {
  exp?: number;
  sub?: string;
  email?: string;
  [key: string]: any;
}

export class UnifiedAuthService {
  private readonly environment: string;
  
  constructor() {
    this.environment = unifiedApiConfig.environment;
    logger.info(`Unified Auth Service initialized for ${this.environment}`);
  }

  /**
   * Get auth configuration from auth service with exponential backoff
   */
  async getAuthConfig(retries = 3, delay = 1000): Promise<AuthConfigResponse> {
    for (let i = 0; i < retries; i++) {
      try {
        // Get config from auth service with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const authConfig = await authServiceClient.getAuthConfig();
        clearTimeout(timeoutId);
        
        // Transform to expected format using unified config
        return {
          development_mode: authConfig.development_mode ?? (this.environment === 'development'),
          // TOMBSTONE: NEXT_PUBLIC_GOOGLE_CLIENT_ID superseded by OAuth config from auth service
          google_client_id: authConfig.google_client_id || '',
          endpoints: {
            login: unifiedApiConfig.endpoints.authLogin,
            logout: unifiedApiConfig.endpoints.authLogout,
            callback: unifiedApiConfig.endpoints.authCallback,
            token: unifiedApiConfig.endpoints.authToken,
            user: unifiedApiConfig.endpoints.authMe,
            dev_login: `${unifiedApiConfig.urls.auth}/auth/dev/login`
          },
          authorized_javascript_origins: [unifiedApiConfig.urls.frontend],
          authorized_redirect_uris: [`${unifiedApiConfig.urls.frontend}/auth/callback`]
        };
      } catch (error) {
        if (i < retries - 1) {
          // Exponential backoff with jitter
          const backoffDelay = delay * Math.pow(2, i) + Math.random() * 1000;
          logger.warn(`Auth config fetch error, retrying... (${i + 1}/${retries}) in ${Math.round(backoffDelay)}ms`, {
            component: 'UnifiedAuthService',
            environment: this.environment,
            error: error instanceof Error ? error.message : 'Unknown error'
          });
          await new Promise(resolve => setTimeout(resolve, backoffDelay));
          continue;
        }
        throw error;
      }
    }
    throw new Error('Failed to fetch auth config after retries');
  }

  /**
   * Handle development login (only available in dev/test environments)
   */
  async handleDevLogin(authConfig: AuthConfigResponse): Promise<{ access_token: string; token_type: string } | null> {
    if (this.environment !== 'development' && this.environment !== 'test') {
      logger.warn('Dev login attempted in non-development environment', {
        environment: this.environment
      });
      return null;
    }

    logger.info('Attempting dev login', { 
      component: 'UnifiedAuthService', 
      environment: this.environment 
    });
    
    try {
      const response = await fetch(authConfig.endpoints.dev_login, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: 'dev@example.com' }),
      });
      
      if (response.ok) {
        const data = await response.json();
        logger.info('Dev login successful');
        this.setToken(data.access_token);
        this.clearDevLogoutFlag();
        return data;
      } else {
        logger.error('Dev login failed', undefined, { 
          status: response.status,
          environment: this.environment
        });
        return null;
      }
    } catch (error) {
      logger.error('Error during dev login', error as Error);
      return null;
    }
  }

  /**
   * Handle OAuth login
   */
  handleLogin(authConfig: AuthConfigResponse, provider: string = 'google'): void {
    logger.info('Initiating OAuth login', { 
      provider, 
      environment: this.environment 
    });
    authServiceClient.initiateLogin(provider);
  }

  /**
   * Handle logout
   */
  async handleLogout(authConfig?: AuthConfigResponse): Promise<void> {
    logger.info('Logging out user', { environment: this.environment });
    
    try {
      await authServiceClient.logout();
      this.removeToken();
      this.setDevLogoutFlag();
    } catch (error) {
      logger.error('Logout error', error as Error);
      // Still clear local state even if server logout fails
      this.removeToken();
      this.setDevLogoutFlag();
    }
  }

  /**
   * Refresh access token
   */
  async refreshToken(): Promise<{ access_token: string; refresh_token?: string }> {
    logger.debug('Refreshing token', { environment: this.environment });
    
    try {
      const result = await authServiceClient.refreshToken();
      if (result && result.access_token) {
        this.setToken(result.access_token);
        logger.info('Token refreshed successfully', { environment: this.environment });
        return result;
      } else {
        logger.warn('Token refresh returned empty result', { environment: this.environment });
        throw new Error('Token refresh returned empty result');
      }
    } catch (error) {
      logger.error('Token refresh failed', error as Error, { environment: this.environment });
      
      // In staging/production, don't remove token immediately on refresh failure
      // The user might still be authenticated with the backend
      if (this.environment === 'development' || this.environment === 'test') {
        this.removeToken();
      }
      
      throw error;
    }
  }

  /**
   * Check if token needs refresh
   */
  needsRefresh(token: string): boolean {
    try {
      const decoded = jwtDecode<JWTPayload>(token);
      if (!decoded.exp) {
        return false;
      }
      
      const expiryTime = decoded.exp * 1000;
      const currentTime = Date.now();
      const timeUntilExpiry = expiryTime - currentTime;
      
      const needsRefresh = timeUntilExpiry < REFRESH_THRESHOLD_MS;
      
      logger.debug('Token refresh check', {
        needsRefresh,
        timeUntilExpiry: Math.floor(timeUntilExpiry / 1000),
        environment: this.environment
      });
      
      return needsRefresh;
    } catch (error) {
      logger.error('Error checking token expiry', error as Error);
      return true; // Err on side of caution
    }
  }

  /**
   * Token management
   */
  getToken(): string | null {
    return typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;
  }

  setToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem(TOKEN_KEY, token);
    }
  }

  removeToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(TOKEN_KEY);
    }
  }

  getAuthHeaders(): Record<string, string> {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  /**
   * Development logout flag management
   */
  setDevLogoutFlag(): void {
    if (typeof window !== 'undefined' && this.environment === 'development') {
      localStorage.setItem(DEV_LOGOUT_FLAG, 'true');
    }
  }

  clearDevLogoutFlag(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(DEV_LOGOUT_FLAG);
    }
  }

  getDevLogoutFlag(): boolean {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(DEV_LOGOUT_FLAG) === 'true';
  }

  /**
   * Get current environment
   */
  getEnvironment(): string {
    return this.environment;
  }
}

// Export singleton instance
export const unifiedAuthService = new UnifiedAuthService();

// Export for backward compatibility
export { unifiedAuthService as authService };