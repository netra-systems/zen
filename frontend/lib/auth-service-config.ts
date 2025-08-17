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
  
  // Determine base URL
  let baseUrl: string;
  if (authServiceUrl) {
    baseUrl = authServiceUrl;
  } else if (env === 'production') {
    baseUrl = 'https://auth.netrasystems.ai';
  } else if (env === 'staging' || process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging') {
    baseUrl = 'https://auth.staging.netrasystems.ai';
  } else {
    // Development
    baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || 'http://localhost:8080';
  }
  
  // Build configuration
  const config: AuthServiceConfig = {
    baseUrl,
    endpoints: {
      login: `${baseUrl}/api/auth/login`,
      logout: `${baseUrl}/api/auth/logout`,
      callback: `${baseUrl}/api/auth/callback`,
      token: `${baseUrl}/api/auth/token`,
      refresh: `${baseUrl}/api/auth/refresh`,
      validate: `${baseUrl}/api/auth/validate`,
      config: `${baseUrl}/api/auth/config`,
      session: `${baseUrl}/api/auth/session`,
      me: `${baseUrl}/api/auth/me`,
    },
    oauth: {
      googleClientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
      redirectUri: `${baseUrl}/api/auth/callback`,
      javascriptOrigins: [
        baseUrl,
        typeof window !== 'undefined' ? window.location.origin : '',
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