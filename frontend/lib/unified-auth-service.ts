/**
 * Unified Auth Service Integration
 * Provides a consistent interface for authentication across all frontend components
 */

import { authService as authServiceClient } from '@/lib/auth-service-config';
import { authService } from '@/auth/service';
import { authInterceptor } from '@/lib/auth-interceptor';
import { logger } from '@/lib/logger';

export interface AuthUser {
  id: string;
  email: string;
  name?: string;
  permissions?: string[];
}

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in?: number;
}

export interface AuthValidationResult {
  valid: boolean;
  user?: AuthUser;
  error?: string;
}

/**
 * Unified authentication service that integrates all auth functionality
 */
class UnifiedAuthService {
  
  /**
   * Initialize authentication and validate current session
   */
  async initialize(): Promise<AuthValidationResult> {
    try {
      const token = authService.getToken();
      
      if (!token) {
        return { valid: false, error: 'No token found' };
      }

      // Validate token with auth service
      const isValid = await authInterceptor.validateCurrentToken();
      
      if (!isValid) {
        return { valid: false, error: 'Token validation failed' };
      }

      // Get current user info
      const user = await this.getCurrentUser();
      
      return { 
        valid: true, 
        user: user || undefined 
      };
    } catch (error) {
      logger.error('Auth initialization failed', error as Error, {
        component: 'UnifiedAuthService',
        action: 'initialize'
      });
      return { 
        valid: false, 
        error: (error as Error).message 
      };
    }
  }

  /**
   * Get current authenticated user
   */
  async getCurrentUser(): Promise<AuthUser | null> {
    try {
      const userData = await authServiceClient.getCurrentUser();
      
      if (!userData) {
        return null;
      }

      return {
        id: userData.id,
        email: userData.email,
        name: userData.name || userData.full_name,
        permissions: userData.permissions || []
      };
    } catch (error) {
      logger.error('Failed to get current user', error as Error, {
        component: 'UnifiedAuthService',
        action: 'getCurrentUser'
      });
      return null;
    }
  }

  /**
   * Handle authentication for development mode
   */
  async handleDevAuth(): Promise<AuthTokens | null> {
    try {
      const config = await authService.getAuthConfig();
      
      if (!config.development_mode) {
        throw new Error('Dev auth not available in production mode');
      }

      const tokens = await authService.handleDevLogin(config);
      
      if (tokens) {
        logger.info('Dev authentication successful');
        return {
          access_token: tokens.access_token,
          token_type: tokens.token_type || 'Bearer'
        };
      }

      return null;
    } catch (error) {
      logger.error('Dev authentication failed', error as Error, {
        component: 'UnifiedAuthService',
        action: 'handleDevAuth'
      });
      throw error;
    }
  }

  /**
   * Handle OAuth login (production)
   */
  async handleOAuthLogin(provider: string = 'google'): Promise<void> {
    try {
      const config = await authService.getAuthConfig();
      authService.handleLogin(config);
    } catch (error) {
      logger.error('OAuth login initiation failed', error as Error, {
        component: 'UnifiedAuthService',
        action: 'handleOAuthLogin',
        provider
      });
      throw error;
    }
  }

  /**
   * Handle logout and cleanup
   */
  async handleLogout(): Promise<void> {
    try {
      const config = await authService.getAuthConfig();
      await authService.handleLogout(config);
      
      logger.info('Logout successful');
    } catch (error) {
      logger.error('Logout failed', error as Error, {
        component: 'UnifiedAuthService',
        action: 'handleLogout'
      });
      
      // Fallback: clear local state even if server logout fails
      authService.removeToken();
      authService.setDevLogoutFlag();
      
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
  }

  /**
   * Get authentication headers for manual requests
   */
  getAuthHeaders(): Record<string, string> {
    return authService.getAuthHeaders();
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    const token = authService.getToken();
    return !!token && !authService.getDevLogoutFlag();
  }

  /**
   * Get current auth configuration
   */
  async getAuthConfig() {
    return authService.getAuthConfig();
  }

  /**
   * Validate token and refresh if needed
   */
  async validateAndRefreshToken(): Promise<boolean> {
    try {
      return await authInterceptor.validateCurrentToken();
    } catch (error) {
      logger.error('Token validation failed', error as Error, {
        component: 'UnifiedAuthService',
        action: 'validateAndRefreshToken'
      });
      return false;
    }
  }

  /**
   * Set up authentication for WebSocket connections
   */
  getWebSocketAuthConfig(): { token: string | null; refreshToken: () => Promise<string | null> } {
    return {
      token: authService.getToken(),
      refreshToken: async () => {
        try {
          const refreshResponse = await authServiceClient.refreshToken();
          if (refreshResponse?.access_token) {
            localStorage.setItem('jwt_token', refreshResponse.access_token);
            return refreshResponse.access_token;
          }
          return null;
        } catch (error) {
          logger.error('WebSocket token refresh failed', error as Error);
          return null;
        }
      }
    };
  }

  /**
   * Handle auth errors consistently
   */
  handleAuthError(error: any): void {
    logger.error('Authentication error', error, {
      component: 'UnifiedAuthService',
      action: 'handleAuthError'
    });

    // If it's a 401 error, trigger logout
    if (error?.status === 401 || error?.message?.includes('401')) {
      this.handleLogout();
    }
  }
}

// Export singleton instance
export const unifiedAuthService = new UnifiedAuthService();

// Re-export auth interceptor for convenience
export { authInterceptor } from '@/lib/auth-interceptor';

// Export individual services for direct access if needed
export { authService } from '@/auth/service';
export { authService as authServiceClient } from '@/lib/auth-service-config';