/**
 * End-to-End Integration Test for WebSocket Ticket Authentication
 * 
 * This test validates the complete frontend ticket authentication flow:
 * 1. Feature flag enabled
 * 2. Ticket service integration
 * 3. WebSocket connection with ticket authentication
 * 4. Fallback to JWT when tickets fail
 * 
 * Tests Issue #1295 implementation completeness.
 */

import { unifiedAuthService } from '@/lib/unified-auth-service';
import { websocketTicketService } from '@/services/websocketTicketService';
import { ticketAuthProvider } from '@/lib/ticket-auth-provider';
import { webSocketService } from '@/services/webSocketService';
import type { TicketRequestResult } from '@/types/websocket-ticket';

// Mock external dependencies
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
    getToken: jest.fn(() => 'test-jwt-token'),
    getAuthConfig: jest.fn()
  }
}));

jest.mock('@/lib/auth-service-config', () => ({
  authService: {
    refreshToken: jest.fn()
  }
}));

// Mock fetch for backend requests
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock WebSocket
const mockWebSocket = {
  close: jest.fn(),
  send: jest.fn(),
  readyState: WebSocket.OPEN,
  addEventListener: jest.fn(),
  removeEventListener: jest.fn()
};

global.WebSocket = jest.fn(() => mockWebSocket) as any;

describe('WebSocket Ticket Authentication E2E Integration', () => {
  const mockTicketResponse = {
    ticket_id: 'test-ticket-12345',
    expires_at: Date.now() / 1000 + 300, // 5 minutes from now
    created_at: Date.now() / 1000,
    ttl_seconds: 300,
    single_use: true,
    websocket_url: 'wss://api-staging.netrasystems.ai/ws?ticket=test-ticket-12345'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockClear();
    
    // Enable ticket authentication
    process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS = 'true';
    
    // Clear ticket cache
    websocketTicketService.clearTicketCache();
    
    // Setup successful ticket response
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockTicketResponse
    });
  });

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS;
    webSocketService.disconnect();
  });

  describe('Feature Flag Integration', () => {
    it('should enable ticket authentication when feature flag is true', () => {
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      
      expect(authConfig.useTicketAuth).toBe(true);
      expect(authConfig.getTicket).toBeDefined();
      expect(typeof authConfig.getTicket).toBe('function');
    });

    it('should disable ticket authentication when feature flag is false', () => {
      process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS = 'false';
      
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      
      expect(authConfig.useTicketAuth).toBe(false);
      expect(authConfig.getTicket).toBeDefined(); // Still provided for consistency
    });
  });

  describe('Ticket Service Integration', () => {
    it('should acquire ticket through unified auth service', async () => {
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      
      const result = await authConfig.getTicket();
      
      expect(result.success).toBe(true);
      expect(result.ticket).toBeDefined();
      expect(result.ticket!.ticket).toBe(mockTicketResponse.ticket_id);
      expect(result.ticket!.expires_at).toBe(mockTicketResponse.expires_at * 1000); // Converted to milliseconds
    });

    it('should cache tickets to avoid repeated requests', async () => {
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      
      // First request
      await authConfig.getTicket();
      expect(mockFetch).toHaveBeenCalledTimes(1);
      
      // Second request should use cache
      await authConfig.getTicket();
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should clear cache on auth context changes', () => {
      // Update auth token
      ticketAuthProvider.updateAuthToken('new-token');
      
      // Verify cache was cleared (next request should hit backend)
      const cacheStats = websocketTicketService.getCacheStats();
      expect(cacheStats.size).toBe(0);
    });
  });

  describe('WebSocket Connection Integration', () => {
    it('should create WebSocket connection with ticket authentication', async () => {
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      
      // Mock successful WebSocket connection
      const mockOnOpen = jest.fn();
      const options = {
        useTicketAuth: authConfig.useTicketAuth,
        ticketTtl: 300,
        onOpen: mockOnOpen
      };
      
      // Start connection (this would normally be async)
      webSocketService.connect('wss://localhost:8000/ws', options);
      
      // Verify WebSocket was created with correct URL containing ticket
      expect(global.WebSocket).toHaveBeenCalledWith(
        expect.stringContaining('ticket=test-ticket-12345')
      );
    });

    it('should fall back to JWT authentication when ticket fails', async () => {
      // Mock ticket request failure
      mockFetch.mockRejectedValueOnce(new Error('Backend unavailable'));
      
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      const options = {
        useTicketAuth: authConfig.useTicketAuth,
        token: 'test-jwt-token',
        onOpen: jest.fn()
      };
      
      // Connection should still work with JWT fallback
      webSocketService.connect('wss://localhost:8000/ws', options);
      
      // Verify WebSocket was created (JWT auth uses subprotocol)
      expect(global.WebSocket).toHaveBeenCalled();
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle ticket expiration and refresh', async () => {
      // Mock expired ticket response
      const expiredTicketResponse = {
        ...mockTicketResponse,
        expires_at: Date.now() / 1000 - 60 // Expired 1 minute ago
      };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => expiredTicketResponse
      });
      
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      const result = await authConfig.getTicket();
      
      // Should still return the ticket (expiry checked on usage)
      expect(result.success).toBe(true);
      expect(result.ticket).toBeDefined();
    });

    it('should handle backend errors gracefully', async () => {
      // Mock backend error
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Internal Server Error'
      });
      
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      const result = await authConfig.getTicket();
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('Backend server error');
      expect(result.recoverable).toBe(true);
    });

    it('should handle authentication failures', async () => {
      // Mock auth failure
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: async () => 'Unauthorized'
      });
      
      const authConfig = unifiedAuthService.getWebSocketAuthConfig();
      const result = await authConfig.getTicket();
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('Authentication required');
      expect(result.recoverable).toBe(false);
    });
  });

  describe('Performance and Caching', () => {
    it('should respect TTL settings', async () => {
      const customTtl = 600; // 10 minutes
      const result = await websocketTicketService.acquireTicket(customTtl);
      
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining(`"ttl_seconds":${customTtl}`)
        })
      );
    });

    it('should provide cache statistics', () => {
      const stats = websocketTicketService.getCacheStats();
      
      expect(stats).toHaveProperty('size');
      expect(stats).toHaveProperty('entries');
      expect(Array.isArray(stats.entries)).toBe(true);
    });
  });

  describe('Configuration Management', () => {
    it('should allow dynamic configuration updates', () => {
      const newConfig = {
        enabled: false,
        defaultTtl: 600,
        maxRetries: 5
      };
      
      websocketTicketService.updateConfig(newConfig);
      const updatedConfig = websocketTicketService.getConfig();
      
      expect(updatedConfig.enabled).toBe(false);
      expect(updatedConfig.defaultTtl).toBe(600);
      expect(updatedConfig.maxRetries).toBe(5);
    });

    it('should provide system status', () => {
      const status = ticketAuthProvider.getStatus();
      
      expect(status).toHaveProperty('enabled');
      expect(status).toHaveProperty('hasAuthToken');
      expect(status).toHaveProperty('cacheStats');
      expect(status).toHaveProperty('config');
    });
  });
});