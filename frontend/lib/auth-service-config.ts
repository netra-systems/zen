/**
 * Auth Service Configuration
 * Centralized configuration for auth service endpoints
 * Now supports dynamic port discovery in development environments
 */

import { logger } from '@/lib/logger';
import { serviceDiscovery } from './service-discovery';

interface AuthServiceConfig {
  baseUrl: string;
  endpoints: {
    login: string;
    logout: string;
    callback: string;
    token: string;
    refresh: string;
    validate_token: string;
    config: string;
    session: string;
    me: string;
  };
  oauth: {
    googleClientId?: string;
    redirectUri: string;
    javascriptOrigins: string[];
  };
  dynamic?: boolean; // Whether URL was discovered dynamically
}

/**
 * Get auth service configuration based on environment (synchronous)
 */
export function getAuthServiceConfig(): AuthServiceConfig {
  const env = process.env.NODE_ENV;
  const authServiceUrl = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL;
  
  // Determine base URL for standalone auth service
  let baseUrl: string;
  if (authServiceUrl) {
    baseUrl = authServiceUrl;
  } else if (process.env.NEXT_PUBLIC_ENVIRONMENT === 'production') {
    baseUrl = 'https://auth.netrasystems.ai';
  } else if (process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging') {
    baseUrl = 'https://auth.staging.netrasystems.ai'; // Staging auth service URL
  } else if (env === 'production' && !process.env.NEXT_PUBLIC_ENVIRONMENT) {
    // Fallback: if NODE_ENV is production but NEXT_PUBLIC_ENVIRONMENT not set, assume staging
    baseUrl = 'https://auth.staging.netrasystems.ai';
  } else {
    // Development - auth service runs on port 8081
    baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || 'http://localhost:8081';
  }
  
  // Build configuration
  const config: AuthServiceConfig = {
    baseUrl,
    endpoints: {
      login: `${baseUrl}/auth/login`,
      logout: `${baseUrl}/auth/logout`,
      callback: `${baseUrl}/auth/callback`,
      token: `${baseUrl}/auth/token`,
      refresh: `${baseUrl}/auth/refresh`,
      validate_token: `${baseUrl}/auth/validate`,
      config: `${baseUrl}/auth/config`,
      session: `${baseUrl}/auth/session`,
      me: `${baseUrl}/auth/me`,
    },
    oauth: {
      googleClientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
      redirectUri: env === 'staging' || process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging' 
        ? 'https://app.staging.netrasystems.ai/auth/callback'
        : `${typeof window !== 'undefined' ? window.location.origin : baseUrl}/auth/callback`,
      javascriptOrigins: [
        baseUrl,
        typeof window !== 'undefined' ? window.location.origin : '',
        env === 'staging' || process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging' ? 'https://app.staging.netrasystems.ai' : '',
      ].filter(Boolean),
    },
  };
  
  return config;
}

/**
 * Get auth service configuration with dynamic discovery (async)
 */
export async function getAuthServiceConfigAsync(): Promise<AuthServiceConfig> {
  const env = process.env.NODE_ENV;
  const authServiceUrl = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL;
  
  try {
    // Only use service discovery in development
    if ((process.env.NEXT_PUBLIC_ENVIRONMENT || 'development') === 'development' && !authServiceUrl) {
      logger.debug('Attempting dynamic auth service discovery');
      
      const authUrl = await serviceDiscovery.getAuthUrl();
      
      const config: AuthServiceConfig = {
        baseUrl: authUrl,
        endpoints: {
          login: `${authUrl}/auth/login`,
          logout: `${authUrl}/auth/logout`,
          callback: `${authUrl}/auth/callback`,
          token: `${authUrl}/auth/token`,
          refresh: `${authUrl}/auth/refresh`,
          validate_token: `${authUrl}/auth/validate`,
          config: `${authUrl}/auth/config`,
          session: `${authUrl}/auth/session`,
          me: `${authUrl}/auth/me`,
        },
        oauth: {
          googleClientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
          redirectUri: env === 'staging' || process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging' 
            ? 'https://app.staging.netrasystems.ai/auth/callback'
            : `${typeof window !== 'undefined' ? window.location.origin : authUrl}/auth/callback`,
          javascriptOrigins: [
            authUrl,
            typeof window !== 'undefined' ? window.location.origin : '',
            env === 'staging' || process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging' ? 'https://app.staging.netrasystems.ai' : '',
          ].filter(Boolean),
        },
        dynamic: true,
      };

      logger.info('Dynamic auth service discovery successful:', { authUrl });
      return config;
    }
  } catch (error) {
    logger.warn('Auth service discovery failed, falling back to static config:', error);
  }

  // Fall back to static config
  return getAuthServiceConfig();
}

/**
 * Auth service API client
 */
export class AuthServiceClient {
  private config: AuthServiceConfig;
  private dynamicConfig: Promise<AuthServiceConfig> | null = null;
  
  constructor() {
    this.config = getAuthServiceConfig();
  }

  /**
   * Initialize with dynamic configuration (call this in development)
   */
  async initWithDynamicConfig(): Promise<void> {
    try {
      this.config = await getAuthServiceConfigAsync();
      logger.debug('Auth service client initialized with dynamic config');
    } catch (error) {
      logger.warn('Failed to initialize with dynamic config, using static config:', error);
    }
  }

  /**
   * Get current configuration (sync)
   */
  getConfig(): AuthServiceConfig {
    return this.config;
  }

  /**
   * Get dynamic configuration (async)
   */
  async getDynamicConfig(): Promise<AuthServiceConfig> {
    if (!this.dynamicConfig) {
      this.dynamicConfig = getAuthServiceConfigAsync();
    }
    return this.dynamicConfig;
  }
  
  /**
   * Get auth configuration from service
   */
  async getConfig() {
    try {
      const response = await fetch(this.config.endpoints.config, {
        signal: AbortSignal.timeout(3000) // 3 second timeout
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: Failed to fetch auth configuration`);
      }
      return response.json();
    } catch (error) {
      logger.warn('Auth service unavailable, using offline configuration:', error);
      
      // Return offline configuration for development
      return {
        development_mode: process.env.NODE_ENV === 'development',
        google_client_id: this.config.oauth.googleClientId || '',
        oauth_enabled: false,
        offline_mode: true
      };
    }
  }
  
  /**
   * Initiate OAuth login
   */
  initiateLogin(provider: string = 'google') {
    window.location.href = `${this.config.endpoints.login}?provider=${provider}`;
  }
  
  /**
   * Logout user
   */
  async logout() {
    const response = await fetch(this.config.endpoints.logout, {
      method: 'POST',
      credentials: 'include',
    });
    if (!response.ok) {
      throw new Error('Failed to logout');
    }
    return response.json();
  }
  
  /**
   * Get current user session
   */
  async getSession() {
    const response = await fetch(this.config.endpoints.session, {
      credentials: 'include',
    });
    if (!response.ok) {
      if (response.status === 401) {
        return null;
      }
      throw new Error('Failed to fetch session');
    }
    return response.json();
  }
  
  /**
   * Get current user details
   */
  async getCurrentUser() {
    const response = await fetch(this.config.endpoints.me, {
      credentials: 'include',
    });
    if (!response.ok) {
      if (response.status === 401) {
        return null;
      }
      throw new Error('Failed to fetch user');
    }
    return response.json();
  }
  
  /**
   * Validate token
   */
  async validateToken(token: string) {
    const response = await fetch(this.config.endpoints.validate_token, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      return false;
    }
    return true;
  }
  
  /**
   * Refresh access token
   */
  async refreshToken() {
    const response = await fetch(this.config.endpoints.refresh, {
      method: 'POST',
      credentials: 'include',
    });
    if (!response.ok) {
      throw new Error('Failed to refresh token');
    }
    return response.json();
  }
}

// Export singleton instance
export const authService = new AuthServiceClient();