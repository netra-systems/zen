/**
 * Integration tests for WebSocket Ticket Authentication
 * Tests the complete flow from unified auth service to WebSocket connection
 */

import { unifiedAuthService } from '@/lib/unified-auth-service';
import { websocketTicketService } from '@/services/websocketTicketService';
import type { TicketRequestResult } from '@/types/websocket-ticket';

// Mock dependencies
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn()
  }
}));

jest.mock('@/auth', () => ({
  authService: {
    getToken: jest.fn(() => 'integration-test-token')
  }
}));

jest.mock('@/lib/auth-service-config', () => ({
  authService: {
    refreshToken: jest.fn()
  }
}));

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('WebSocket Ticket Authentication Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockClear();
    
    // Clear any cached tickets
    websocketTicketService.clearTicketCache();
    
    // Reset environment variable to enabled state
    process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS = 'true';
  });

  afterEach(() => {
    // Clean up environment variables
    delete process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS;
  });

  describe('Unified Auth Service Integration', () => {
    it('should provide WebSocket auth config with ticket support enabled', () => {
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();

      expect(authConfig).toHaveProperty('token');
      expect(authConfig).toHaveProperty('refreshToken');
      expect(authConfig).toHaveProperty('getTicket');
      expect(authConfig).toHaveProperty('useTicketAuth');
      
      expect(typeof authConfig.getTicket).toBe('function');
      expect(typeof authConfig.refreshToken).toBe('function');
      expect(authConfig.useTicketAuth).toBe(true);
    });

    it('should disable ticket auth when feature flag is false', () => {
      process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS = 'false';
      
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      
      expect(authConfig.useTicketAuth).toBe(false);
    });

    it('should acquire tickets through auth config interface', async () => {
      // Mock successful ticket response
      const mockTicketResponse = {
        ticket_id: 'integration-test-ticket',
        expires_at: Math.floor(Date.now() / 1000) + 300,
        created_at: Math.floor(Date.now() / 1000),
        ttl_seconds: 300,
        single_use: true,
        websocket_url: 'wss://api.example.com/ws?ticket=integration-test-ticket'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue(mockTicketResponse)
      });

      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      const ticketResult = await authConfig.getTicket();

      expect(ticketResult.success).toBe(true);
      expect(ticketResult.ticket?.ticket).toBe('integration-test-ticket');
      expect(ticketResult.ticket?.websocket_url).toBe(mockTicketResponse.websocket_url);
    });

    it('should handle auth errors and clear ticket cache', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      // Mock error with status
      const mockError = {
        status: 401,
        message: 'Authentication failed'
      };

      unifiedAuthService.handleAuthError(mockError);
      
      // Verify cache was cleared (cache should be empty)
      const cacheStats = websocketTicketService.getCacheStats();
      expect(cacheStats.size).toBe(0);
      
      consoleSpy.mockRestore();
    });
  });

  describe('End-to-End Ticket Flow', () => {
    it('should complete full ticket acquisition and caching flow', async () => {
      // Mock successful ticket response
      const mockTicketResponse = {
        ticket_id: 'e2e-test-ticket-123',
        expires_at: Math.floor(Date.now() / 1000) + 300,
        created_at: Math.floor(Date.now() / 1000),
        ttl_seconds: 300,
        single_use: true,
        websocket_url: 'wss://api.example.com/ws?ticket=e2e-test-ticket-123'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue(mockTicketResponse)
      });

      // Step 1: Get auth config from unified service
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      expect(authConfig.useTicketAuth).toBe(true);

      // Step 2: Acquire ticket through auth config
      const ticketResult = await authConfig.getTicket();
      expect(ticketResult.success).toBe(true);
      expect(ticketResult.ticket).toBeDefined();

      // Step 3: Verify ticket is cached for subsequent use
      const cachedTicketResult = await authConfig.getTicket();
      expect(cachedTicketResult.success).toBe(true);
      expect(cachedTicketResult.ticket?.ticket).toBe(ticketResult.ticket?.ticket);
      
      // Should only have made one HTTP request (second used cache)
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Step 4: Verify cache statistics
      const cacheStats = websocketTicketService.getCacheStats();
      expect(cacheStats.size).toBe(1);
      expect(cacheStats.entries[0].timeUntilExpiry).toBeGreaterThan(0);
    });

    it('should handle graceful fallback when ticket acquisition fails', async () => {
      // Mock ticket endpoint failure
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        text: jest.fn().mockResolvedValue('Endpoint not found')
      });

      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      const ticketResult = await authConfig.getTicket();

      expect(ticketResult.success).toBe(false);
      expect(ticketResult.error).toContain('Ticket endpoint not available');
      expect(ticketResult.recoverable).toBe(false);

      // Auth config should still provide JWT token for fallback
      expect(authConfig.token).toBe('integration-test-token');
    });

    it('should handle token refresh through auth config', async () => {
      const mockRefreshResponse = {
        access_token: 'refreshed-integration-token',
        token_type: 'Bearer',
        expires_in: 3600
      };

      // Mock the auth service client refresh
      const { authService: authServiceClient } = require('@/lib/auth-service-config');
      authServiceClient.refreshToken.mockResolvedValueOnce(mockRefreshResponse);

      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      const refreshedToken = await authConfig.refreshToken();

      expect(refreshedToken).toBe('refreshed-integration-token');
      expect(authServiceClient.refreshToken).toHaveBeenCalled();
    });
  });

  describe('Error Scenarios and Recovery', () => {
    it('should handle network errors during ticket acquisition', async () => {
      // Mock network error
      mockFetch.mockRejectedValueOnce(new Error('Network error: Failed to fetch'));

      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      const ticketResult = await authConfig.getTicket();

      expect(ticketResult.success).toBe(false);
      expect(ticketResult.error).toContain('Ticket acquisition error');
      expect(ticketResult.recoverable).toBe(true);
    });

    it('should handle invalid ticket responses', async () => {
      // Mock response with missing ticket_id
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue({
          expires_at: Math.floor(Date.now() / 1000) + 300,
          // Missing ticket_id field
        })
      });

      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      const ticketResult = await authConfig.getTicket();

      expect(ticketResult.success).toBe(false);
      expect(ticketResult.error).toBe('Invalid ticket response format');
      expect(ticketResult.recoverable).toBe(false);
    });

    it('should clear ticket cache on authentication errors', () => {
      // Add a ticket to cache first
      const mockTicketResponse = {
        ticket_id: 'cache-clear-test-ticket',
        expires_at: Math.floor(Date.now() / 1000) + 300,
        created_at: Math.floor(Date.now() / 1000),
        ttl_seconds: 300,
        single_use: true,
        websocket_url: 'wss://api.example.com/ws?ticket=cache-clear-test-ticket'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue(mockTicketResponse)
      });

      // Get auth config and acquire a ticket
      return unifiedAuthService.getWebSocketAuthConfig().getTicket().then(() => {
        // Verify ticket is cached
        const statsBefore = websocketTicketService.getCacheStats();
        expect(statsBefore.size).toBe(1);

        // Trigger auth error
        unifiedAuthService.handleAuthError({ status: 401, message: 'Unauthorized' });

        // Verify cache was cleared
        const statsAfter = websocketTicketService.getCacheStats();
        expect(statsAfter.size).toBe(0);
      });
    });
  });

  describe('Feature Flag Behavior', () => {
    it('should enable ticket auth by default', () => {
      // No environment variable set
      delete process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS;
      
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      expect(authConfig.useTicketAuth).toBe(true);
    });

    it('should enable ticket auth when explicitly set to true', () => {
      process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS = 'true';
      
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      expect(authConfig.useTicketAuth).toBe(true);
    });

    it('should disable ticket auth when set to false', () => {
      process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS = 'false';
      
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      expect(authConfig.useTicketAuth).toBe(false);
    });

    it('should enable ticket auth for any value other than false', () => {
      process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS = 'development';
      
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      expect(authConfig.useTicketAuth).toBe(true);
    });
  });
});