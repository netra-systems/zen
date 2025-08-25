/**
 * Auth Service Client
 * Uses unified configuration for clear environment handling
 * No duplicate methods, no localhost in production/staging
 */

import { unifiedApiConfig, getOAuthRedirectUri } from '@/lib/unified-api-config';
import { logger } from '@/lib/logger';

interface AuthConfig {
  development_mode: boolean;
  google_client_id: string;
  oauth_enabled: boolean;
  offline_mode?: boolean;
}

interface AuthSession {
  user?: {
    id: string;
    email: string;
    name?: string;
  };
  access_token?: string;
  refresh_token?: string;
}

/**
 * Auth Service Client - Single source of truth for auth operations
 */
export class AuthServiceClient {
  private readonly environment: string;
  private readonly baseUrl: string;
  private readonly endpoints: typeof unifiedApiConfig.endpoints;
  
  constructor() {
    const config = unifiedApiConfig;
    this.environment = config.environment;
    this.baseUrl = config.urls.auth;
    this.endpoints = config.endpoints;
    
    logger.info(`Auth Service Client initialized for ${this.environment}`, {
      baseUrl: this.baseUrl,
      environment: this.environment
    });
  }

  /**
   * Get auth service configuration
   */
  async getAuthConfig(): Promise<AuthConfig> {
    try {
      logger.debug(`Fetching auth config from: ${this.endpoints.authConfig}`);
      
      const response = await fetch(this.endpoints.authConfig, {
        signal: AbortSignal.timeout(5000), // Increased timeout for staging
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        // Don't throw immediately for 403 errors in staging - this is expected
        if (response.status === 403 && this.environment === 'staging') {
          logger.info('Auth service returned 403 - authentication required for staging');
        } else {
          throw new Error(`HTTP ${response.status}: Failed to fetch auth configuration`);
        }
      }
      
      const config = await response.json();
      logger.info('Auth configuration fetched successfully', { 
        oauth_enabled: config.oauth_enabled,
        environment: this.environment 
      });
      return config;
    } catch (error) {
      logger.warn('Auth service unavailable, using offline configuration:', error);
      
      // For staging/production, still try to provide a working config
      if (this.environment === 'staging' || this.environment === 'production') {
        return {
          development_mode: false,
          google_client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
          oauth_enabled: true,
          offline_mode: false
        };
      }
      
      // Return offline configuration for development/test
      return {
        development_mode: this.environment === 'development' || this.environment === 'test',
        google_client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
        oauth_enabled: false,
        offline_mode: true
      };
    }
  }
  
  /**
   * Initiate OAuth login
   */
  initiateLogin(provider: string = 'google'): void {
    const loginUrl = `${this.endpoints.authLogin}?provider=${provider}`;
    logger.info(`Initiating OAuth login`, { provider, loginUrl, environment: this.environment });
    window.location.href = loginUrl;
  }
  
  /**
   * Logout user
   */
  async logout(): Promise<void> {
    logger.info(`Logging out user`, { environment: this.environment });
    
    const response = await fetch(this.endpoints.authLogout, {
      method: 'POST',
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Logout failed: ${response.status}`);
    }
    
    logger.info('User logged out successfully');
  }
  
  /**
   * Get current user session
   */
  async getSession(): Promise<AuthSession | null> {
    try {
      const response = await fetch(this.endpoints.authSession, {
        credentials: 'include',
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          logger.debug('No active session found');
          return null;
        }
        throw new Error(`Failed to fetch session: ${response.status}`);
      }
      
      const session = await response.json();
      logger.debug('Session fetched successfully', { 
        hasUser: !!session.user,
        environment: this.environment 
      });
      return session;
    } catch (error) {
      logger.error('Failed to fetch session:', error);
      return null;
    }
  }
  
  /**
   * Get current user details
   */
  async getCurrentUser(): Promise<any | null> {
    try {
      const response = await fetch(this.endpoints.authMe, {
        credentials: 'include',
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          return null;
        }
        throw new Error(`Failed to fetch user: ${response.status}`);
      }
      
      const user = await response.json();
      logger.debug('User details fetched successfully', { 
        userId: user.id,
        environment: this.environment 
      });
      return user;
    } catch (error) {
      logger.error('Failed to fetch user details:', error);
      return null;
    }
  }
  
  /**
   * Validate token
   */
  async validateToken(token: string): Promise<boolean> {
    try {
      const response = await fetch(this.endpoints.authValidate, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });
      
      const isValid = response.ok;
      logger.debug('Token validation result', { 
        isValid, 
        environment: this.environment 
      });
      return isValid;
    } catch (error) {
      logger.error('Token validation failed:', error);
      return false;
    }
  }
  
  /**
   * Refresh access token
   */
  async refreshToken(): Promise<{ access_token: string; refresh_token?: string }> {
    logger.debug('Refreshing access token', { environment: this.environment });
    
    const response = await fetch(this.endpoints.authRefresh, {
      method: 'POST',
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Token refresh failed: ${response.status}`);
    }
    
    const tokens = await response.json();
    logger.info('Token refreshed successfully');
    return tokens;
  }
  
  /**
   * Get OAuth redirect URI for current environment
   */
  getOAuthRedirectUri(): string {
    return getOAuthRedirectUri();
  }
  
  /**
   * Get environment info
   */
  getEnvironment(): string {
    return this.environment;
  }
}

// Export singleton instance
export const authServiceClient = new AuthServiceClient();