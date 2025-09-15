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
// Dynamic refresh threshold based on environment and token expiry
// For short tokens (< 5 minutes), refresh at 25% of lifetime
// For normal tokens (>= 5 minutes), refresh 5 minutes before expiry

interface JWTPayload {
  exp?: number;
  iat?: number;
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
   * Handle E2E test authentication for staging environment
   * This method bypasses OAuth for automated testing on staging
   */
  async handleE2ETestAuth(bypassKey: string, testUser?: { email?: string; name?: string; permissions?: string[] }): Promise<{ access_token: string; token_type: string } | null> {
    if (this.environment !== 'staging') {
      logger.warn('E2E test auth attempted in non-staging environment', {
        environment: this.environment
      });
      return null;
    }

    logger.info('Attempting E2E test authentication', {
      component: 'UnifiedAuthService',
      environment: this.environment
    });

    try {
      const response = await fetch(`${unifiedApiConfig.urls.auth}/auth/e2e/test-auth`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-E2E-Bypass-Key': bypassKey
        },
        body: JSON.stringify(testUser || {
          email: 'e2e-test@staging.netrasystems.ai',
          name: 'E2E Test User',
          permissions: ['read', 'write']
        })
      });

      if (response.ok) {
        const data = await response.json();
        logger.info('E2E test authentication successful');
        this.setToken(data.access_token);
        if (data.refresh_token) {
          localStorage.setItem('refresh_token', data.refresh_token);
        }
        return data;
      } else {
        const errorText = await response.text();
        logger.error('E2E test authentication failed', {
          status: response.status,
          error: errorText
        });
        return null;
      }
    } catch (error) {
      logger.error('E2E test authentication error', {
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      return null;
    }
  }

  /**
   * Handle development login (only available in dev/test environments)
   * Uses exponential backoff for retries to handle backend startup delays
   */
  async handleDevLogin(authConfig: AuthConfigResponse, retries = 5, initialDelay = 1000): Promise<{ access_token: string; token_type: string } | null> {
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
    
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout per attempt
        
        const response = await fetch(authConfig.endpoints.dev_login, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ 
            email: 'dev@example.com',
            password: 'dev'  // Add password for dev login
          }),
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
          const data = await response.json();
          logger.info('Dev login successful', {
            attempt: attempt + 1,
            totalAttempts: retries + 1
          });
          this.setToken(data.access_token);
          this.clearDevLogoutFlag();
          return data;
        } else {
          logger.warn('Dev login failed', { 
            status: response.status,
            environment: this.environment,
            attempt: attempt + 1,
            willRetry: attempt < retries
          });
          if (attempt < retries) {
            // Exponential backoff with jitter
            const backoffDelay = initialDelay * Math.pow(2, attempt) + Math.random() * 1000;
            logger.debug(`Retrying dev login in ${Math.round(backoffDelay)}ms`, {
              attempt: attempt + 1,
              nextDelay: backoffDelay
            });
            await new Promise(resolve => setTimeout(resolve, backoffDelay));
            continue;
          }
          return null;
        }
      } catch (error) {
        const isAborted = error instanceof Error && error.name === 'AbortError';
        const isNetworkError = error instanceof Error && 
          (error.message.includes('ECONNREFUSED') || 
           error.message.includes('Failed to fetch') ||
           error.message.includes('NetworkError'));
        
        logger.warn('Error during dev login', {
          error: error instanceof Error ? error.message : 'Unknown error',
          attempt: attempt + 1,
          willRetry: attempt < retries,
          isAborted,
          isNetworkError
        });
        
        if (attempt < retries) {
          // Exponential backoff with jitter
          const backoffDelay = initialDelay * Math.pow(2, attempt) + Math.random() * 1000;
          logger.debug(`Retrying dev login after error in ${Math.round(backoffDelay)}ms`, {
            attempt: attempt + 1,
            nextDelay: backoffDelay
          });
          await new Promise(resolve => setTimeout(resolve, backoffDelay));
          continue;
        }
        return null;
      }
    }
    return null;
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
   * Check if token needs refresh - environment-aware for short-lived tokens
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
      
      // Handle cases where token is already expired or will expire very soon
      if (timeUntilExpiry <= 0) {
        return true; // Token is expired or about to expire
      }
      
      // Calculate total token lifetime for dynamic threshold
      const issuedTime = decoded.iat ? decoded.iat * 1000 : (currentTime - 15 * 60 * 1000);
      const totalLifetime = expiryTime - issuedTime;
      
      // Dynamic refresh threshold based on token lifetime
      let refreshThreshold;
      if (totalLifetime < 5 * 60 * 1000) { // Tokens < 5 minutes
        // For short tokens (like 30s tokens), refresh when 75% of lifetime has passed
        // (i.e., when 25% of lifetime remains)
        refreshThreshold = totalLifetime * 0.25;
      } else {
        // For normal tokens (>= 5 minutes), refresh 5 minutes before expiry
        refreshThreshold = 5 * 60 * 1000;
      }
      
      const needsRefresh = timeUntilExpiry <= refreshThreshold;
      
      logger.debug('Token refresh check', {
        needsRefresh,
        timeUntilExpiry: Math.floor(timeUntilExpiry / 1000),
        totalLifetime: Math.floor(totalLifetime / 1000),
        refreshThreshold: Math.floor(refreshThreshold / 1000),
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
   * Validate token and get user data in single operation
   * This is the missing method that the Golden Path authentication requires.
   *
   * Business Value Justification:
   * - Segment: All (Platform/Security)
   * - Business Goal: Restore $500K+ ARR Golden Path authentication functionality
   * - Value Impact: Single API call combines token validation with user lookup for efficient auth
   * - Strategic Impact: Eliminates authentication system blocking and enables complete user flow
   */
  async validateTokenAndGetUser(token: string): Promise<{valid: boolean, user?: any, error?: string}> {
    logger.debug('Validating token and getting user data', {
      environment: this.environment,
      hasToken: !!token
    });

    try {
      const response = await fetch(unifiedApiConfig.endpoints.authValidateTokenAndGetUser, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          token: token
        }),
      });

      if (!response.ok) {
        logger.error('validateTokenAndGetUser API call failed', {
          status: response.status,
          statusText: response.statusText,
          environment: this.environment
        });
        return {
          valid: false,
          error: `API call failed: ${response.status} ${response.statusText}`
        };
      }

      const result = await response.json();

      if (result.valid) {
        logger.info('Token validation and user lookup successful', {
          userId: result.user_id,
          environment: this.environment
        });
        return {
          valid: true,
          user: result.user || {
            id: result.user_id,
            email: result.token_data?.email,
            ...result.token_data
          }
        };
      } else {
        logger.warn('Token validation failed', {
          error: result.error,
          environment: this.environment
        });
        return {
          valid: false,
          error: result.error || 'Token validation failed'
        };
      }

    } catch (error) {
      logger.error('validateTokenAndGetUser request failed', error as Error, {
        environment: this.environment
      });
      return {
        valid: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
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