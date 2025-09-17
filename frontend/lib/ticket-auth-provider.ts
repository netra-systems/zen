/**
 * TicketAuthProvider - Frontend WebSocket Ticket Authentication
 * 
 * This provider serves as the bridge between the auth context and WebSocket service,
 * implementing Issue #1295 (Frontend Ticket Authentication Implementation).
 * 
 * Business Impact:
 * - Enables secure WebSocket authentication without browser header limitations
 * - Provides automatic ticket refresh and cache management
 * - Integrates seamlessly with existing auth infrastructure
 * 
 * Technical Implementation:
 * - Uses websocketTicketService for ticket management
 * - Provides getTicket function for WebSocket service integration
 * - Handles ticket lifecycle alongside JWT token management
 */

import { logger } from '@/lib/logger';
import { websocketTicketService } from '@/services/websocketTicketService';
import type { TicketRequestResult, WebSocketTicket } from '@/types/websocket-ticket';

/**
 * Configuration for ticket auth provider
 */
interface TicketAuthProviderConfig {
  /** Whether ticket authentication is enabled */
  enabled: boolean;
  /** Default TTL for tickets in seconds */
  defaultTtl: number;
  /** Whether to clear cache on auth state changes */
  clearOnAuthChange: boolean;
  /** Maximum retry attempts */
  maxRetries: number;
}

/**
 * Default configuration
 */
const DEFAULT_CONFIG: TicketAuthProviderConfig = {
  enabled: true,
  defaultTtl: 300, // 5 minutes
  clearOnAuthChange: true,
  maxRetries: 3
};

/**
 * TicketAuthProvider Class
 * 
 * Provides ticket authentication functionality for WebSocket connections.
 * Designed to integrate with the existing auth context and WebSocket service.
 */
export class TicketAuthProvider {
  private config: TicketAuthProviderConfig;
  private currentToken: string | null = null;

  constructor(config: Partial<TicketAuthProviderConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    
    logger.debug('TicketAuthProvider initialized', {
      component: 'TicketAuthProvider',
      action: 'constructor',
      metadata: {
        enabled: this.config.enabled,
        defaultTtl: this.config.defaultTtl,
        clearOnAuthChange: this.config.clearOnAuthChange
      }
    });
  }

  /**
   * Get authentication ticket for WebSocket connection
   * 
   * This is the main method used by WebSocketService.
   * It handles ticket acquisition with proper error handling and retry logic.
   * 
   * @param ttlSeconds - Optional TTL override
   * @returns Promise resolving to ticket result
   */
  async getTicket(ttlSeconds?: number): Promise<TicketRequestResult> {
    try {
      // Check if ticket auth is enabled
      if (!this.config.enabled) {
        logger.debug('Ticket authentication is disabled', {
          component: 'TicketAuthProvider',
          action: 'getTicket'
        });
        
        return {
          success: false,
          error: 'Ticket authentication is disabled',
          recoverable: false
        };
      }

      // Check if we have an auth token first
      if (!this.hasValidAuthToken()) {
        logger.debug('No valid auth token available for ticket request', {
          component: 'TicketAuthProvider',
          action: 'getTicket'
        });
        
        return {
          success: false,
          error: 'No authentication token available',
          recoverable: false
        };
      }

      logger.debug('Requesting WebSocket authentication ticket', {
        component: 'TicketAuthProvider',
        action: 'getTicket',
        metadata: {
          ttlSeconds: ttlSeconds || this.config.defaultTtl,
          hasAuthToken: !!this.currentToken
        }
      });

      // Use the ticket service to acquire ticket
      const result = await websocketTicketService.acquireTicket(
        ttlSeconds || this.config.defaultTtl
      );

      if (result.success && result.ticket) {
        logger.info('WebSocket ticket acquired successfully', {
          component: 'TicketAuthProvider',
          action: 'getTicket',
          metadata: {
            ticketLength: result.ticket.ticket.length,
            expiresAt: new Date(result.ticket.expires_at).toISOString(),
            ttlSeconds: ttlSeconds || this.config.defaultTtl
          }
        });
      } else {
        logger.warn('Failed to acquire WebSocket ticket', {
          component: 'TicketAuthProvider',
          action: 'getTicket',
          metadata: {
            error: result.error,
            recoverable: result.recoverable
          }
        });
      }

      return result;

    } catch (error) {
      logger.error('Unexpected error acquiring WebSocket ticket', error as Error, {
        component: 'TicketAuthProvider',
        action: 'getTicket'
      });

      return {
        success: false,
        error: `Ticket acquisition error: ${(error as Error).message}`,
        recoverable: true
      };
    }
  }

  /**
   * Clear ticket cache
   * 
   * Used when auth state changes or when tickets become invalid.
   */
  clearTicketCache(): void {
    try {
      logger.debug('Clearing WebSocket ticket cache', {
        component: 'TicketAuthProvider',
        action: 'clearTicketCache'
      });

      websocketTicketService.clearTicketCache();
      
    } catch (error) {
      logger.error('Error clearing ticket cache', error as Error, {
        component: 'TicketAuthProvider',
        action: 'clearTicketCache'
      });
    }
  }

  /**
   * Update authentication token
   * 
   * Called when JWT token changes. This ensures ticket requests
   * use the latest authentication context.
   * 
   * @param token - New JWT token
   */
  updateAuthToken(token: string | null): void {
    const previousToken = this.currentToken;
    this.currentToken = token;
    
    logger.debug('Auth token updated in ticket provider', {
      component: 'TicketAuthProvider',
      action: 'updateAuthToken',
      metadata: {
        hadPreviousToken: !!previousToken,
        hasNewToken: !!token,
        tokenChanged: previousToken !== token
      }
    });

    // Clear ticket cache if token changed and configured to do so
    if (this.config.clearOnAuthChange && previousToken !== token) {
      this.clearTicketCache();
    }
  }

  /**
   * Check if we have a valid authentication token
   */
  private hasValidAuthToken(): boolean {
    // Check if we have a token stored
    if (this.currentToken) {
      return true;
    }

    // Fallback: try to get token from localStorage (for compatibility)
    if (typeof window !== 'undefined') {
      const storedToken = localStorage.getItem('jwt_token');
      if (storedToken) {
        this.currentToken = storedToken;
        return true;
      }
    }

    return false;
  }

  /**
   * Get current configuration
   */
  getConfig(): TicketAuthProviderConfig {
    return { ...this.config };
  }

  /**
   * Update configuration
   */
  updateConfig(newConfig: Partial<TicketAuthProviderConfig>): void {
    this.config = { ...this.config, ...newConfig };
    
    logger.debug('TicketAuthProvider configuration updated', {
      component: 'TicketAuthProvider',
      action: 'updateConfig',
      metadata: this.config
    });
  }

  /**
   * Check if ticket authentication is enabled
   */
  isEnabled(): boolean {
    return this.config.enabled;
  }

  /**
   * Enable/disable ticket authentication
   */
  setEnabled(enabled: boolean): void {
    const wasEnabled = this.config.enabled;
    this.config.enabled = enabled;
    
    logger.info(`Ticket authentication ${enabled ? 'enabled' : 'disabled'}`, {
      component: 'TicketAuthProvider',
      action: 'setEnabled',
      metadata: { 
        wasEnabled, 
        nowEnabled: enabled 
      }
    });

    // Clear cache when disabling
    if (!enabled && wasEnabled) {
      this.clearTicketCache();
    }
  }

  /**
   * Get current status for debugging
   */
  getStatus(): {
    enabled: boolean;
    hasAuthToken: boolean;
    cacheStats: ReturnType<typeof websocketTicketService.getCacheStats>;
    config: TicketAuthProviderConfig;
  } {
    return {
      enabled: this.config.enabled,
      hasAuthToken: this.hasValidAuthToken(),
      cacheStats: websocketTicketService.getCacheStats(),
      config: this.getConfig()
    };
  }

  /**
   * Test ticket acquisition (for debugging)
   */
  async testTicketAcquisition(): Promise<{
    success: boolean;
    ticket?: WebSocketTicket;
    error?: string;
    timing: number;
  }> {
    const startTime = Date.now();
    
    try {
      const result = await this.getTicket();
      const timing = Date.now() - startTime;
      
      return {
        success: result.success,
        ticket: result.ticket,
        error: result.error,
        timing
      };
      
    } catch (error) {
      const timing = Date.now() - startTime;
      
      return {
        success: false,
        error: (error as Error).message,
        timing
      };
    }
  }
}

// Export singleton instance for application use
export const ticketAuthProvider = new TicketAuthProvider();

// Export the class for testing and custom configurations
export default TicketAuthProvider;