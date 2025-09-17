/**
 * Unified Auth Service Integration
 * Provides a consistent interface for authentication across all frontend components
 */

import { authService as authServiceClient } from '@/lib/auth-service-config';
import { authService } from '@/auth';
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

export interface WebSocketTicket {
  ticket: string;
  expires_at: number;
}

export interface TicketRequestResult {
  success: boolean;
  ticket?: WebSocketTicket;
  error?: string;
}

/**
 * Unified authentication service that integrates all auth functionality
 */
class UnifiedAuthService {
  private ticketCache = new Map<string, WebSocketTicket>();
  private readonly TICKET_REFRESH_THRESHOLD = 30000; // Refresh tickets 30s before expiry
  
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
      // Clear ticket cache before logout
      this.clearTicketCache();
      
      const config = await authService.getAuthConfig();
      await authService.handleLogout(config);
      
      logger.info('Logout successful');
    } catch (error) {
      logger.error('Logout failed', error as Error, {
        component: 'UnifiedAuthService',
        action: 'handleLogout'
      });
      
      // Fallback: clear local state even if server logout fails
      this.clearTicketCache();
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
   * Request a WebSocket authentication ticket
   */
  async requestWebSocketTicket(): Promise<TicketRequestResult> {
    try {
      const token = authService.getToken();
      if (!token) {
        return { 
          success: false, 
          error: 'No authentication token available' 
        };
      }

      const response = await fetch('/api/auth/websocket-ticket', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        logger.warn('WebSocket ticket request failed', {
          component: 'UnifiedAuthService',
          action: 'requestWebSocketTicket',
          metadata: {
            status: response.status,
            statusText: response.statusText,
            error: errorText
          }
        });
        
        return { 
          success: false, 
          error: `Ticket request failed: ${response.status} ${response.statusText}` 
        };
      }

      const ticketData = await response.json();
      
      if (!ticketData.ticket) {
        return { 
          success: false, 
          error: 'Invalid ticket response format' 
        };
      }

      const ticket: WebSocketTicket = {
        ticket: ticketData.ticket,
        expires_at: ticketData.expires_at || (Date.now() + 300000) // Default 5min TTL
      };

      // Cache the ticket
      this.ticketCache.set('default', ticket);

      logger.debug('WebSocket ticket generated successfully', {
        component: 'UnifiedAuthService',
        action: 'requestWebSocketTicket',
        metadata: {
          ticketLength: ticket.ticket.length,
          expiresAt: new Date(ticket.expires_at).toISOString()
        }
      });

      return { success: true, ticket };

    } catch (error) {
      logger.error('WebSocket ticket request failed', error as Error, {
        component: 'UnifiedAuthService',
        action: 'requestWebSocketTicket'
      });
      
      return { 
        success: false, 
        error: `Ticket request error: ${(error as Error).message}` 
      };
    }
  }

  /**
   * Get cached WebSocket ticket or request a new one
   */
  async getWebSocketTicket(): Promise<TicketRequestResult> {
    const cached = this.ticketCache.get('default');
    
    // Check if cached ticket is still valid with threshold buffer
    if (cached && (cached.expires_at - Date.now()) > this.TICKET_REFRESH_THRESHOLD) {
      logger.debug('Using cached WebSocket ticket', {
        component: 'UnifiedAuthService',
        action: 'getWebSocketTicket',
        metadata: {
          timeUntilExpiry: cached.expires_at - Date.now()
        }
      });
      
      return { success: true, ticket: cached };
    }

    // Request new ticket
    logger.debug('Requesting fresh WebSocket ticket', {
      component: 'UnifiedAuthService',
      action: 'getWebSocketTicket',
      metadata: {
        hadCachedTicket: !!cached,
        cacheExpired: cached ? (cached.expires_at - Date.now()) <= this.TICKET_REFRESH_THRESHOLD : false
      }
    });

    return await this.requestWebSocketTicket();
  }

  /**
   * Clear ticket cache (useful for logout/auth errors)
   */
  clearTicketCache(): void {
    this.ticketCache.clear();
    logger.debug('WebSocket ticket cache cleared', {
      component: 'UnifiedAuthService',
      action: 'clearTicketCache'
    });
  }

  /**
   * Set up authentication for WebSocket connections (updated for ticket support)
   */
  getWebSocketAuthConfig(): { 
    token: string | null; 
    refreshToken: () => Promise<string | null>;
    getTicket: () => Promise<TicketRequestResult>;
    useTicketAuth: boolean;
  } {
    return {
      // Maintain JWT token for backward compatibility
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
      },
      // Add ticket-based authentication
      getTicket: () => this.getWebSocketTicket(),
      useTicketAuth: true // Feature flag for ticket authentication
    };
  }

  /**
   * Handle auth errors consistently
   */
  handleAuthError(error: unknown): void {
    logger.error('Authentication error', error, {
      component: 'UnifiedAuthService',
      action: 'handleAuthError'
    });

    // Clear ticket cache on auth errors
    this.clearTicketCache();

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
export { authService } from '@/auth';
export { authService as authServiceClient } from '@/lib/auth-service-config';