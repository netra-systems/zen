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
  private lastConfigAttempt?: number;
  private cachedConfig?: AuthConfig;
  
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
    // Prevent excessive retries by tracking last attempt
    const now = Date.now();
    if (this.lastConfigAttempt && now - this.lastConfigAttempt < 10000) { // 10 second cooldown
      logger.debug('Auth config fetch on cooldown, returning cached or fallback');
      if (this.cachedConfig) {
        return this.cachedConfig;
      }
    }
    this.lastConfigAttempt = now;
    
    try {
      logger.debug(`Fetching auth config from: ${this.endpoints.authConfig}`);
      
      const response = await fetch(this.endpoints.authConfig, {
        signal: AbortSignal.timeout(5000), // Increased timeout for staging
        // No credentials needed for public config endpoint
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        // Check for OAuth configuration errors
        let errorDetail: any;
        try {
          errorDetail = await response.json();
        } catch {
          errorDetail = { message: `HTTP ${response.status}: Failed to fetch auth configuration` };
        }
        
        // CRITICAL: Log OAuth configuration failures loudly
        if (errorDetail.error === 'AUTH_CONFIG_FAILURE' || errorDetail.error === 'OAUTH_CONFIGURATION_BROKEN') {
          logger.error('🚨🚨🚨 CRITICAL OAUTH CONFIGURATION ERROR IN FRONTEND 🚨🚨🚨');
          logger.error(`Environment: ${this.environment}`);
          logger.error(`Auth service returned OAuth configuration error:`, errorDetail);
          
          // Throw specific error that can be caught by UI components
          throw new Error(`OAUTH_CONFIG_ERROR: ${errorDetail.user_message || errorDetail.message}`);
        }
        
        // Don't throw immediately for 403 errors in staging - this is expected
        if (response.status === 403 && this.environment === 'staging') {
          logger.info('Auth service returned 403 - authentication required for staging');
        } else {
          throw new Error(errorDetail.message || `HTTP ${response.status}: Failed to fetch auth configuration`);
        }
      }
      
      const config = await response.json();
      
      // CRITICAL: Validate OAuth configuration received from auth service
      if (!config.google_client_id && this.environment !== 'development') {
        logger.error('🚨🚨🚨 CRITICAL: Auth service returned empty Google Client ID 🚨🚨🚨');
        logger.error(`Environment: ${this.environment}`);
        logger.error(`This will cause OAuth login to fail completely`);
        
        // Don't fail silently - throw an error
        throw new Error('OAUTH_CONFIG_ERROR: Google Client ID is missing from auth service configuration');
      }
      
      // Check for placeholder values
      if (config.google_client_id && (config.google_client_id.startsWith('REPLACE_') || config.google_client_id.length < 50)) {
        logger.error('🚨🚨🚨 CRITICAL: Auth service returned placeholder Google Client ID 🚨🚨🚨');
        logger.error(`Environment: ${this.environment}`);
        logger.error(`Client ID: ${config.google_client_id.substring(0, 20)}...`);
        logger.error(`This will cause OAuth login to fail completely`);
        
        throw new Error('OAUTH_CONFIG_ERROR: Google Client ID appears to be a placeholder value');
      }
      
      logger.info('Auth configuration fetched successfully', { 
        oauth_enabled: config.oauth_enabled,
        environment: this.environment,
        has_client_id: !!config.google_client_id
      });
      this.cachedConfig = config; // Cache successful config
      return config;
    } catch (error) {
      // CRITICAL: Check if this is an OAuth configuration error
      if (error instanceof Error && error.message.includes('OAUTH_CONFIG_ERROR')) {
        logger.error('🚨🚨🚨 OAUTH CONFIGURATION ERROR - NOT FALLING BACK 🚨🚨🚨');
        throw error; // Don't fall back for OAuth config errors, let the UI handle it
      }
      
      logger.warn('Auth service unavailable, using offline configuration:', error);
      
      // For staging/production, still try to provide a working config
      if (this.environment === 'staging' || this.environment === 'production') {
        // TOMBSTONE: NEXT_PUBLIC_GOOGLE_CLIENT_ID superseded by OAuth config from auth service
        const fallbackClientId = '';
        
        // CRITICAL: Warn about fallback configuration
        if (!fallbackClientId) {
          logger.error('🚨🚨🚨 CRITICAL: No fallback Google Client ID available 🚨🚨🚨');
          logger.error(`Environment: ${this.environment}`);
          logger.error(`Auth service OAuth configuration is unavailable`);
        }
        
        return {
          development_mode: false,
          google_client_id: fallbackClientId,
          oauth_enabled: !!fallbackClientId,
          offline_mode: false
        };
      }
      
      // Return offline configuration for development/test
      return {
        development_mode: this.environment === 'development' || this.environment === 'test',
        // TOMBSTONE: NEXT_PUBLIC_GOOGLE_CLIENT_ID superseded by OAuth config from auth service
        google_client_id: '',
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
    
    // Get token from localStorage to send in Authorization header
    const token = typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : null;
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(this.endpoints.authLogout, {
      method: 'POST',
      credentials: 'include', // Needed for session cookie
      headers,
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
        credentials: 'include', // Needed for session cookie
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
        credentials: 'include', // Needed for session cookie
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
    
    // Get refresh token from localStorage
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }
    
    const response = await fetch(this.endpoints.authRefresh, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Needed for cookies if any
      body: JSON.stringify({ 
        refresh_token: refreshToken 
      }),
    });
    
    if (!response.ok) {
      // If refresh fails, clear tokens
      if (response.status === 401 || response.status === 422) {
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('jwt_token');
      }
      throw new Error(`Token refresh failed: ${response.status}`);
    }
    
    const tokens = await response.json();
    
    // Update stored refresh token if a new one was provided
    if (tokens.refresh_token) {
      localStorage.setItem('refresh_token', tokens.refresh_token);
    }
    
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