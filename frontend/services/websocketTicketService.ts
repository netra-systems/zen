/**
 * WebSocket Ticket Authentication Service
 * 
 * Handles ticket acquisition, caching, and renewal for WebSocket connections.
 * This service provides a clean separation of concerns for ticket management
 * and integrates with the existing auth infrastructure.
 * 
 * Features:
 * - Automatic ticket caching with TTL management
 * - Retry logic with exponential backoff
 * - Feature flag support for gradual rollout
 * - Error handling with fallback mechanisms
 * - Integration with existing auth service
 */

import { logger } from '@/lib/logger';
import { authService } from '@/auth';
import type {
  WebSocketTicket,
  TicketRequestResult,
  TicketGenerationRequest,
  TicketGenerationResponse,
  TicketError,
  TicketAuthConfig,
  TicketCacheEntry
} from '@/types/websocket-ticket';

/**
 * Default configuration for ticket authentication
 */
const DEFAULT_CONFIG: TicketAuthConfig = {
  enabled: true, // Controlled by feature flag
  defaultTtl: 300, // 5 minutes
  refreshThreshold: 30000, // 30 seconds before expiry
  maxRetries: 3,
  retryDelay: 1000 // 1 second base delay
};

/**
 * WebSocket Ticket Service
 * 
 * Provides secure, time-limited authentication tickets for WebSocket connections.
 * Integrates with the backend AuthTicketManager implementation from Issue #1296.
 */
export class WebSocketTicketService {
  private ticketCache = new Map<string, TicketCacheEntry>();
  private config: TicketAuthConfig;
  private isAcquiring = false; // Prevent concurrent ticket requests

  constructor(config: Partial<TicketAuthConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    
    logger.debug('WebSocketTicketService initialized', {
      component: 'WebSocketTicketService',
      action: 'constructor',
      metadata: {
        enabled: this.config.enabled,
        defaultTtl: this.config.defaultTtl,
        refreshThreshold: this.config.refreshThreshold
      }
    });
  }

  /**
   * Acquire a WebSocket authentication ticket
   * 
   * This method handles the complete ticket acquisition flow:
   * 1. Check cache for valid existing ticket
   * 2. Request new ticket from backend if needed
   * 3. Handle errors with retry logic
   * 4. Cache successful ticket for reuse
   * 
   * @param ttl_seconds - Time to live for the ticket (optional)
   * @returns Promise resolving to ticket result
   */
  async acquireTicket(ttl_seconds: number = this.config.defaultTtl): Promise<TicketRequestResult> {
    try {
      // Check if ticket auth is enabled
      if (!this.isTicketAuthEnabled()) {
        return {
          success: false,
          error: 'Ticket authentication is disabled',
          recoverable: false
        };
      }

      // Check cache first
      const cached = this.getCachedTicket();
      if (cached && this.isTicketValid(cached)) {
        logger.debug('Using cached WebSocket ticket', {
          component: 'WebSocketTicketService',
          action: 'acquireTicket',
          metadata: {
            ticketLength: cached.ticket.length,
            timeUntilExpiry: cached.expires_at - Date.now()
          }
        });
        
        return { success: true, ticket: cached };
      }

      // Prevent concurrent requests
      if (this.isAcquiring) {
        logger.debug('Ticket acquisition already in progress, waiting...', {
          component: 'WebSocketTicketService',
          action: 'acquireTicket'
        });
        
        // Wait for ongoing request (with timeout)
        return this.waitForOngoingRequest();
      }

      // Request new ticket
      this.isAcquiring = true;
      
      try {
        const result = await this.requestTicketFromBackend(ttl_seconds);
        
        if (result.success && result.ticket) {
          // Cache successful ticket
          this.cacheTicket(result.ticket);
          
          logger.info('WebSocket ticket acquired successfully', {
            component: 'WebSocketTicketService',
            action: 'acquireTicket',
            metadata: {
              ticketLength: result.ticket.ticket.length,
              expiresAt: new Date(result.ticket.expires_at).toISOString(),
              ttlSeconds: ttl_seconds
            }
          });
        }
        
        return result;
      } finally {
        this.isAcquiring = false;
      }

    } catch (error) {
      this.isAcquiring = false;
      
      logger.error('Ticket acquisition failed', error as Error, {
        component: 'WebSocketTicketService',
        action: 'acquireTicket',
        metadata: { ttlSeconds: ttl_seconds }
      });
      
      return {
        success: false,
        error: `Ticket acquisition error: ${(error as Error).message}`,
        recoverable: true
      };
    }
  }

  /**
   * Request ticket from backend with retry logic
   */
  private async requestTicketFromBackend(ttl_seconds: number): Promise<TicketRequestResult> {
    const request: TicketGenerationRequest = {
      ttl_seconds,
      single_use: true, // Default to single-use for security
      permissions: ['read', 'chat', 'websocket', 'agent:execute']
    };

    let lastError: TicketError | null = null;

    for (let attempt = 1; attempt <= this.config.maxRetries; attempt++) {
      try {
        logger.debug(`Requesting ticket from backend (attempt ${attempt}/${this.config.maxRetries})`, {
          component: 'WebSocketTicketService',
          action: 'requestTicketFromBackend',
          metadata: { attempt, ttlSeconds: ttl_seconds }
        });

        const result = await this.makeTicketRequest(request);
        
        if (result.success) {
          return result;
        }

        // Handle specific error cases
        lastError = this.categorizeError(result.error || 'Unknown error', attempt);
        
        if (!lastError.recoverable) {
          break; // Don't retry non-recoverable errors
        }

        if (attempt < this.config.maxRetries) {
          const delay = this.calculateRetryDelay(attempt);
          logger.debug(`Retrying ticket request in ${delay}ms`, {
            component: 'WebSocketTicketService',
            action: 'requestTicketFromBackend',
            metadata: { attempt, delay, error: lastError.message }
          });
          
          await this.sleep(delay);
        }

      } catch (error) {
        lastError = this.categorizeError((error as Error).message, attempt);
        
        if (!lastError.recoverable) {
          break;
        }
        
        if (attempt < this.config.maxRetries) {
          const delay = this.calculateRetryDelay(attempt);
          await this.sleep(delay);
        }
      }
    }

    return {
      success: false,
      error: lastError?.message || 'Ticket request failed after all retries',
      recoverable: lastError?.recoverable || false
    };
  }

  /**
   * Make the actual HTTP request to the backend ticket endpoint
   */
  private async makeTicketRequest(request: TicketGenerationRequest): Promise<TicketRequestResult> {
    const token = authService.getToken();
    if (!token) {
      return {
        success: false,
        error: 'No authentication token available',
        recoverable: false
      };
    }

    const endpoint = this.getTicketEndpoint();
    
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const errorText = await response.text();
      
      // Handle specific HTTP status codes
      switch (response.status) {
        case 404:
          return {
            success: false,
            error: 'Ticket endpoint not available - falling back to JWT',
            recoverable: false
          };
        case 401:
          return {
            success: false,
            error: 'Authentication required for ticket request',
            recoverable: false
          };
        case 429:
          return {
            success: false,
            error: 'Rate limited - too many ticket requests',
            recoverable: true
          };
        case 500:
        case 502:
        case 503:
          return {
            success: false,
            error: 'Backend server error',
            recoverable: true
          };
        default:
          return {
            success: false,
            error: `Ticket request failed: ${response.status} ${response.statusText}`,
            recoverable: response.status >= 500
          };
      }
    }

    const ticketData: TicketGenerationResponse = await response.json();
    
    if (!ticketData.ticket_id) {
      return {
        success: false,
        error: 'Invalid ticket response format',
        recoverable: false
      };
    }

    // Convert backend response to frontend ticket format
    const ticket: WebSocketTicket = {
      ticket: ticketData.ticket_id,
      expires_at: ticketData.expires_at * 1000, // Convert to milliseconds
      created_at: ticketData.created_at * 1000, // Convert to milliseconds
      websocket_url: ticketData.websocket_url
    };

    return { success: true, ticket };
  }

  /**
   * Get the correct ticket endpoint based on environment
   */
  private getTicketEndpoint(): string {
    // Use existing auth service endpoint resolution
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      if (hostname.includes('staging') || hostname.includes('netrasystems.ai')) {
        return '/api/websocket/ticket';
      }
    }
    
    // For development, use local endpoint
    return '/api/websocket/ticket';
  }

  /**
   * Check if ticket authentication is enabled
   */
  private isTicketAuthEnabled(): boolean {
    // Check environment variable feature flag
    const envFlag = process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS;
    
    // Default to enabled unless explicitly disabled
    return envFlag !== 'false' && this.config.enabled;
  }

  /**
   * Get cached ticket if available and valid
   */
  private getCachedTicket(): WebSocketTicket | null {
    const cached = this.ticketCache.get('default');
    
    if (!cached) {
      return null;
    }

    // Clean up expired cache entries
    if (!this.isTicketValid(cached.ticket)) {
      this.ticketCache.delete('default');
      return null;
    }

    return cached.ticket;
  }

  /**
   * Check if a ticket is still valid (not expired, with refresh threshold)
   */
  private isTicketValid(ticket: WebSocketTicket): boolean {
    const timeUntilExpiry = ticket.expires_at - Date.now();
    return timeUntilExpiry > this.config.refreshThreshold;
  }

  /**
   * Cache a ticket for reuse
   */
  private cacheTicket(ticket: WebSocketTicket): void {
    const cacheEntry: TicketCacheEntry = {
      ticket,
      cachedAt: Date.now()
    };
    
    this.ticketCache.set('default', cacheEntry);
    
    logger.debug('Ticket cached successfully', {
      component: 'WebSocketTicketService',
      action: 'cacheTicket',
      metadata: {
        expiresAt: new Date(ticket.expires_at).toISOString(),
        cacheSize: this.ticketCache.size
      }
    });
  }

  /**
   * Clear all cached tickets
   */
  clearTicketCache(): void {
    const cacheSize = this.ticketCache.size;
    this.ticketCache.clear();
    
    logger.debug('Ticket cache cleared', {
      component: 'WebSocketTicketService',
      action: 'clearTicketCache',
      metadata: { previousCacheSize: cacheSize }
    });
  }

  /**
   * Categorize errors for retry logic
   */
  private categorizeError(errorMessage: string, attempt: number): TicketError {
    const message = errorMessage.toLowerCase();
    
    // Non-recoverable errors
    if (message.includes('not available') || 
        message.includes('404') ||
        message.includes('authentication required') ||
        message.includes('invalid token')) {
      return {
        message: errorMessage,
        code: 'NON_RECOVERABLE',
        recoverable: false,
        originalError: errorMessage
      };
    }
    
    // Rate limiting
    if (message.includes('rate limited') || message.includes('429')) {
      return {
        message: errorMessage,
        code: 'RATE_LIMITED',
        recoverable: true,
        originalError: errorMessage
      };
    }
    
    // Server errors (recoverable)
    if (message.includes('server error') || 
        message.includes('500') || 
        message.includes('502') || 
        message.includes('503')) {
      return {
        message: errorMessage,
        code: 'SERVER_ERROR',
        recoverable: true,
        originalError: errorMessage
      };
    }
    
    // Network errors (recoverable)
    if (message.includes('network') || message.includes('fetch')) {
      return {
        message: errorMessage,
        code: 'NETWORK_ERROR',
        recoverable: true,
        originalError: errorMessage
      };
    }
    
    // Default to recoverable for unknown errors
    return {
      message: errorMessage,
      code: 'UNKNOWN_ERROR',
      recoverable: attempt < this.config.maxRetries,
      originalError: errorMessage
    };
  }

  /**
   * Calculate retry delay with exponential backoff
   */
  private calculateRetryDelay(attempt: number): number {
    const baseDelay = this.config.retryDelay;
    const exponentialDelay = baseDelay * Math.pow(2, attempt - 1);
    const jitter = Math.random() * 0.1 * exponentialDelay; // Add 10% jitter
    
    return Math.min(exponentialDelay + jitter, 10000); // Cap at 10 seconds
  }

  /**
   * Sleep utility for retry delays
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Wait for ongoing ticket request to complete
   */
  private async waitForOngoingRequest(): Promise<TicketRequestResult> {
    const maxWait = 5000; // 5 seconds max wait
    const checkInterval = 100; // Check every 100ms
    let waited = 0;
    
    while (this.isAcquiring && waited < maxWait) {
      await this.sleep(checkInterval);
      waited += checkInterval;
    }
    
    if (this.isAcquiring) {
      return {
        success: false,
        error: 'Timeout waiting for ongoing ticket request',
        recoverable: true
      };
    }
    
    // Try to get the ticket that should now be cached
    const cached = this.getCachedTicket();
    if (cached) {
      return { success: true, ticket: cached };
    }
    
    return {
      success: false,
      error: 'Ongoing request completed but no ticket available',
      recoverable: true
    };
  }

  /**
   * Get current service configuration
   */
  getConfig(): TicketAuthConfig {
    return { ...this.config };
  }

  /**
   * Update service configuration
   */
  updateConfig(newConfig: Partial<TicketAuthConfig>): void {
    this.config = { ...this.config, ...newConfig };
    
    logger.debug('WebSocketTicketService configuration updated', {
      component: 'WebSocketTicketService',
      action: 'updateConfig',
      metadata: this.config
    });
  }

  /**
   * Get cache statistics for monitoring
   */
  getCacheStats(): { size: number; entries: Array<{ key: string; expiresAt: string; timeUntilExpiry: number }> } {
    const entries = Array.from(this.ticketCache.entries()).map(([key, entry]) => ({
      key,
      expiresAt: new Date(entry.ticket.expires_at).toISOString(),
      timeUntilExpiry: entry.ticket.expires_at - Date.now()
    }));
    
    return {
      size: this.ticketCache.size,
      entries
    };
  }
}

// Export singleton instance for application use
export const websocketTicketService = new WebSocketTicketService();

// Export the class for testing and custom configurations
export { WebSocketTicketService };