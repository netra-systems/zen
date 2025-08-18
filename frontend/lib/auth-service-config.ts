/**
 * Auth Service Configuration
 * Centralized configuration for auth service endpoints
 */

interface AuthServiceConfig {
  baseUrl: string;
  endpoints: {
    login: string;
    logout: string;
    callback: string;
    token: string;
    refresh: string;
    validate: string;
    config: string;
    session: string;
    me: string;
  };
  oauth: {
    googleClientId?: string;
    redirectUri: string;
    javascriptOrigins: string[];
  };
}

/**
 * Get auth service configuration based on environment
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
      validate: `${baseUrl}/auth/validate`,
      config: `${baseUrl}/auth/config`,
      session: `${baseUrl}/auth/session`,
      me: `${baseUrl}/auth/me`,
    },
    oauth: {
      googleClientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
      redirectUri: env === 'staging' || process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging' 
        ? 'https://staging.netrasystems.ai/auth/callback'
        : `${typeof window !== 'undefined' ? window.location.origin : baseUrl}/auth/callback`,
      javascriptOrigins: [
        baseUrl,
        typeof window !== 'undefined' ? window.location.origin : '',
        env === 'staging' || process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging' ? 'https://staging.netrasystems.ai' : '',
      ].filter(Boolean),
    },
  };
  
  return config;
}

/**
 * Auth service API client
 */
export class AuthServiceClient {
  private config: AuthServiceConfig;
  
  constructor() {
    this.config = getAuthServiceConfig();
  }
  
  /**
   * Get auth configuration from service
   */
  async getConfig() {
    const response = await fetch(this.config.endpoints.config);
    if (!response.ok) {
      throw new Error('Failed to fetch auth configuration');
    }
    return response.json();
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
    const response = await fetch(this.config.endpoints.validate, {
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