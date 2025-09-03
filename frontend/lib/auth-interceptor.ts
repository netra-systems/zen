/**
 * Authentication Interceptor
 * Centralized auth handling for all API calls with automatic token refresh
 */

import { authService as authServiceClient } from '@/lib/auth-service-config';
import { authService } from '@/auth';
import { logger } from '@/lib/logger';
import { unifiedApiConfig } from '@/lib/unified-api-config';

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
  private environment: string;
  private refreshAttempts = new Map<string, { count: number; timestamp: number }>();
  private readonly MAX_REFRESH_ATTEMPTS_PER_URL = 2;
  private readonly REFRESH_ATTEMPT_WINDOW_MS = 30000; // 30 seconds

  constructor() {
    this.environment = unifiedApiConfig.environment;
  }

  /**
   * Get environment-specific request timeout
   */
  private getRequestTimeout(): number {
    switch (this.environment) {
      case 'staging':
        return 30000; // 30s for staging (higher latency)
      case 'production':
        return 20000; // 20s for production
      case 'development':
      default:
        return 10000; // 10s for development
    }
  }

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
   * Clean up old refresh attempts from tracking map
   */
  private cleanupRefreshAttempts(): void {
    const now = Date.now();
    for (const [key, attempt] of this.refreshAttempts.entries()) {
      if (now - attempt.timestamp > this.REFRESH_ATTEMPT_WINDOW_MS) {
        this.refreshAttempts.delete(key);
      }
    }
  }

  /**
   * Check if we're in a refresh loop for this URL
   */
  private isInRefreshLoop(url: string): boolean {
    this.cleanupRefreshAttempts();
    
    const attempt = this.refreshAttempts.get(url);
    if (!attempt) return false;
    
    const now = Date.now();
    // If we've tried recently and hit the max attempts, we're in a loop
    return (
      attempt.count >= this.MAX_REFRESH_ATTEMPTS_PER_URL &&
      (now - attempt.timestamp) < this.REFRESH_ATTEMPT_WINDOW_MS
    );
  }

  /**
   * Track refresh attempt for loop detection
   */
  private trackRefreshAttempt(url: string): void {
    const existing = this.refreshAttempts.get(url);
    const now = Date.now();
    
    if (existing && (now - existing.timestamp) < this.REFRESH_ATTEMPT_WINDOW_MS) {
      // Increment existing attempt count
      this.refreshAttempts.set(url, {
        count: existing.count + 1,
        timestamp: now
      });
    } else {
      // Start new tracking
      this.refreshAttempts.set(url, {
        count: 1,
        timestamp: now
      });
    }
  }

  /**
   * Handle 401 responses by refreshing token and retrying
   */
  private async handle401Response(
    url: string, 
    config: RequestConfig
  ): Promise<Response> {
    // Check for refresh loop first
    if (this.isInRefreshLoop(url)) {
      logger.error('Detected auth refresh loop, breaking cycle', {
        url,
        environment: this.environment
      });
      this.refreshAttempts.delete(url);
      this.redirectToLogin();
      throw new Error('Authentication loop detected - please login again');
    }

    // Track this refresh attempt
    this.trackRefreshAttempt(url);

    const retryCount = config.retryCount || 0;
    
    if (retryCount >= this.maxRetries) {
      // Max retries exceeded, redirect to login
      logger.warn('Max auth retries exceeded', {
        url,
        retryCount,
        environment: this.environment
      });
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
      const response = await fetch(url, retryConfig);
      
      // If successful, clear the refresh attempts for this URL
      if (response.ok || response.status !== 401) {
        this.refreshAttempts.delete(url);
      }
      
      return response;
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
        // Store new token using UnifiedAuthService (SSOT)
        authService.setToken(refreshResponse.access_token);
        
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
    
    // Add timeout if not already set
    if (!authConfig.signal) {
      const controller = new AbortController();
      const timeout = setTimeout(() => {
        controller.abort();
        logger.warn('Auth request timed out', {
          url,
          timeout: this.getRequestTimeout(),
          environment: this.environment
        });
      }, this.getRequestTimeout());
      
      authConfig.signal = controller.signal;
      
      // Clean up timeout
      authConfig.signal.addEventListener('abort', () => {
        clearTimeout(timeout);
      });
    }
    
    try {
      // Make the request
      const response = await fetch(url, authConfig);
      
      // Handle 401 Unauthorized
      if (response.status === 401 && !config.skipAuth) {
        logger.warn('Received 401, attempting token refresh', {
          environment: this.environment
        });
        return this.handle401Response(url, authConfig);
      }
      
      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      logger.error('Request failed', error as Error, {
        component: 'AuthInterceptor',
        url,
        method: config.method || 'GET',
        environment: this.environment,
        isTimeout: errorMessage.includes('abort') || errorMessage.includes('timeout')
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

  public async post(url: string, data?: unknown, config: RequestConfig = {}): Promise<Response> {
    const body = data ? JSON.stringify(data) : undefined;
    return this.authenticatedFetch(url, { ...config, method: 'POST', body });
  }

  public async put(url: string, data?: unknown, config: RequestConfig = {}): Promise<Response> {
    const body = data ? JSON.stringify(data) : undefined;
    return this.authenticatedFetch(url, { ...config, method: 'PUT', body });
  }

  public async patch(url: string, data?: unknown, config: RequestConfig = {}): Promise<Response> {
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