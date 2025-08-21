/**
 * Authentication Interceptor
 * Centralized auth handling for all API calls with automatic token refresh
 */

import { authService as authServiceClient } from '@/lib/auth-service-config';
import { authService } from '@/auth/service';
import { logger } from '@/lib/logger';

export interface RequestConfig extends RequestInit {
  headers?: Record<string, string>;
  skipAuth?: boolean;
  retryCount?: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
  refresh_token?: string;
}

class AuthInterceptor {
  private refreshTokenPromise: Promise<string | null> | null = null;
  private maxRetries = 1;

  /**
   * Apply authentication headers to request
   */
  private applyAuthHeaders(config: RequestConfig): RequestConfig {
    if (config.skipAuth) {
      return config;
    }

    const token = authService.getToken();
    if (token) {
      const headers = {
        ...config.headers,
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };
      return { ...config, headers };
    }

    return {
      ...config,
      headers: {
        ...config.headers,
        'Content-Type': 'application/json',
      }
    };
  }

  /**
   * Handle 401 responses by refreshing token and retrying
   */
  private async handle401Response(
    url: string, 
    config: RequestConfig
  ): Promise<Response> {
    const retryCount = config.retryCount || 0;
    
    if (retryCount >= this.maxRetries) {
      // Max retries exceeded, redirect to login
      this.redirectToLogin();
      throw new Error('Authentication failed after retry');
    }

    try {
      // Attempt token refresh
      const newToken = await this.refreshToken();
      if (!newToken) {
        this.redirectToLogin();
        throw new Error('Token refresh failed');
      }

      // Update headers with new token
      const retryConfig: RequestConfig = {
        ...config,
        retryCount: retryCount + 1,
        headers: {
          ...config.headers,
          'Authorization': `Bearer ${newToken}`,
        }
      };

      // Retry the original request
      logger.info('Retrying request with refreshed token');
      return fetch(url, retryConfig);
    } catch (error) {
      logger.error('Token refresh failed', error as Error);
      this.redirectToLogin();
      throw error;
    }
  }

  /**
   * Refresh access token using auth service
   */
  private async refreshToken(): Promise<string | null> {
    // Prevent multiple simultaneous refresh attempts
    if (this.refreshTokenPromise) {
      return this.refreshTokenPromise;
    }

    this.refreshTokenPromise = this.performTokenRefresh();
    
    try {
      const result = await this.refreshTokenPromise;
      return result;
    } finally {
      this.refreshTokenPromise = null;
    }
  }

  /**
   * Perform the actual token refresh
   */
  private async performTokenRefresh(): Promise<string | null> {
    try {
      // Use auth service to refresh token
      const refreshResponse = await authServiceClient.refreshToken();
      
      if (refreshResponse?.access_token) {
        // Store new token
        localStorage.setItem('jwt_token', refreshResponse.access_token);
        
        logger.info('Token refreshed successfully');
        return refreshResponse.access_token;
      }
      
      return null;
    } catch (error) {
      logger.error('Auth service token refresh failed', error as Error);
      return null;
    }
  }

  /**
   * Redirect to login page
   */
  private redirectToLogin(): void {
    // Clear tokens
    authService.removeToken();
    authService.setDevLogoutFlag();
    
    // Redirect to login
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }

  /**
   * Validate token with auth service
   */
  public async validateCurrentToken(): Promise<boolean> {
    const token = authService.getToken();
    if (!token) {
      return false;
    }

    try {
      return await authServiceClient.validateToken(token);
    } catch (error) {
      logger.error('Token validation failed', error as Error);
      return false;
    }
  }

  /**
   * Main interceptor method - enhances fetch with auth handling
   */
  public async authenticatedFetch(
    url: string, 
    config: RequestConfig = {}
  ): Promise<Response> {
    // Apply auth headers
    const authConfig = this.applyAuthHeaders(config);
    
    try {
      // Make the request
      const response = await fetch(url, authConfig);
      
      // Handle 401 Unauthorized
      if (response.status === 401 && !config.skipAuth) {
        logger.warn('Received 401, attempting token refresh');
        return this.handle401Response(url, authConfig);
      }
      
      return response;
    } catch (error) {
      logger.error('Request failed', error as Error, {
        component: 'AuthInterceptor',
        url,
        method: config.method || 'GET'
      });
      throw error;
    }
  }

  /**
   * Convenience methods for different HTTP verbs
   */
  public async get(url: string, config: RequestConfig = {}): Promise<Response> {
    return this.authenticatedFetch(url, { ...config, method: 'GET' });
  }

  public async post(url: string, data?: any, config: RequestConfig = {}): Promise<Response> {
    const body = data ? JSON.stringify(data) : undefined;
    return this.authenticatedFetch(url, { ...config, method: 'POST', body });
  }

  public async put(url: string, data?: any, config: RequestConfig = {}): Promise<Response> {
    const body = data ? JSON.stringify(data) : undefined;
    return this.authenticatedFetch(url, { ...config, method: 'PUT', body });
  }

  public async patch(url: string, data?: any, config: RequestConfig = {}): Promise<Response> {
    const body = data ? JSON.stringify(data) : undefined;
    return this.authenticatedFetch(url, { ...config, method: 'PATCH', body });
  }

  public async delete(url: string, config: RequestConfig = {}): Promise<Response> {
    return this.authenticatedFetch(url, { ...config, method: 'DELETE' });
  }
}

// Export singleton instance
export const authInterceptor = new AuthInterceptor();

// Helper function for backward compatibility
export const authenticatedFetch = (url: string, config?: RequestConfig) => 
  authInterceptor.authenticatedFetch(url, config);