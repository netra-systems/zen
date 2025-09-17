/**
 * Unit tests for WebSocket Ticket Service
 * Tests the core ticket acquisition, caching, and error handling functionality
 */

import { WebSocketTicketService, websocketTicketService } from '@/services/websocketTicketService';
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
    getToken: jest.fn(() => 'test-jwt-token')
  }
}));

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('WebSocketTicketService', () => {
  let ticketService: WebSocketTicketService;

  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    mockFetch.mockClear();
    
    // Create fresh instance for each test
    ticketService = new WebSocketTicketService();
    
    // Clear any cached tickets
    ticketService.clearTicketCache();
  });

  describe('Ticket Authentication Feature Flag', () => {
    it('should be enabled by default when environment variable is not set', () => {
      const config = ticketService.getConfig();
      expect(config.enabled).toBe(true);
    });

    it('should respect environment variable when disabled', () => {
      // Mock environment variable
      const originalEnv = process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS;
      process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS = 'false';
      
      const disabledService = new WebSocketTicketService();
      const result = disabledService.acquireTicket();
      
      expect(result).resolves.toEqual({
        success: false,
        error: 'Ticket authentication is disabled',
        recoverable: false
      });
      
      // Restore environment variable
      process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET_TICKETS = originalEnv;
    });
  });

  describe('Ticket Acquisition', () => {
    it('should successfully acquire a ticket from backend', async () => {
      // Mock successful ticket response
      const mockTicketResponse = {
        ticket_id: 'test-ticket-123',
        expires_at: Math.floor(Date.now() / 1000) + 300, // 5 minutes from now
        created_at: Math.floor(Date.now() / 1000),
        ttl_seconds: 300,
        single_use: true,
        websocket_url: 'wss://api.example.com/ws?ticket=test-ticket-123'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue(mockTicketResponse)
      });

      const result = await ticketService.acquireTicket(300);

      expect(result.success).toBe(true);
      expect(result.ticket).toBeDefined();
      expect(result.ticket?.ticket).toBe('test-ticket-123');
      expect(result.ticket?.websocket_url).toBe(mockTicketResponse.websocket_url);
      expect(result.error).toBeUndefined();

      // Verify fetch was called with correct parameters
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/websocket/ticket',
        {
          method: 'POST',
          headers: {
            'Authorization': 'Bearer test-jwt-token',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            ttl_seconds: 300,
            single_use: true,
            permissions: ['read', 'chat', 'websocket', 'agent:execute']
          })
        }
      );
    });

    it('should use cached ticket when available and valid', async () => {
      // First request - mock successful response
      const mockTicketResponse = {
        ticket_id: 'cached-ticket-456',
        expires_at: Math.floor(Date.now() / 1000) + 300,
        created_at: Math.floor(Date.now() / 1000),
        ttl_seconds: 300,
        single_use: true,
        websocket_url: 'wss://api.example.com/ws?ticket=cached-ticket-456'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue(mockTicketResponse)
      });

      // First call should hit the backend
      const firstResult = await ticketService.acquireTicket();
      expect(firstResult.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Second call should use cache (no additional fetch)
      const secondResult = await ticketService.acquireTicket();
      expect(secondResult.success).toBe(true);
      expect(secondResult.ticket?.ticket).toBe('cached-ticket-456');
      expect(mockFetch).toHaveBeenCalledTimes(1); // Still only one call
    });

    it('should refresh expired tickets', async () => {
      // First request - ticket that expires soon
      const expiredTicketResponse = {
        ticket_id: 'expired-ticket-789',
        expires_at: Math.floor(Date.now() / 1000) + 10, // Expires in 10 seconds (within refresh threshold)
        created_at: Math.floor(Date.now() / 1000),
        ttl_seconds: 300,
        single_use: true,
        websocket_url: 'wss://api.example.com/ws?ticket=expired-ticket-789'
      };

      // Second request - fresh ticket
      const freshTicketResponse = {
        ticket_id: 'fresh-ticket-999',
        expires_at: Math.floor(Date.now() / 1000) + 300,
        created_at: Math.floor(Date.now() / 1000),
        ttl_seconds: 300,
        single_use: true,
        websocket_url: 'wss://api.example.com/ws?ticket=fresh-ticket-999'
      };

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: jest.fn().mockResolvedValue(expiredTicketResponse)
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: jest.fn().mockResolvedValue(freshTicketResponse)
        });

      // First call gets the soon-to-expire ticket
      const firstResult = await ticketService.acquireTicket();
      expect(firstResult.success).toBe(true);
      expect(firstResult.ticket?.ticket).toBe('expired-ticket-789');

      // Second call should detect expiration and get fresh ticket
      const secondResult = await ticketService.acquireTicket();
      expect(secondResult.success).toBe(true);
      expect(secondResult.ticket?.ticket).toBe('fresh-ticket-999');
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('Error Handling', () => {
    it('should handle 404 error (endpoint not available)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        text: jest.fn().mockResolvedValue('Endpoint not found')
      });

      const result = await ticketService.acquireTicket();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Ticket endpoint not available - falling back to JWT');
      expect(result.recoverable).toBe(false);
    });

    it('should handle 401 error (authentication required)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        text: jest.fn().mockResolvedValue('Authentication required')
      });

      const result = await ticketService.acquireTicket();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Authentication required for ticket request');
      expect(result.recoverable).toBe(false);
    });

    it('should handle 429 error (rate limited) as recoverable', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        text: jest.fn().mockResolvedValue('Rate limited')
      });

      const result = await ticketService.acquireTicket();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Rate limited - too many ticket requests');
      expect(result.recoverable).toBe(true);
    });

    it('should handle 500 error (server error) as recoverable', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: jest.fn().mockResolvedValue('Server error')
      });

      const result = await ticketService.acquireTicket();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Backend server error');
      expect(result.recoverable).toBe(true);
    });

    it('should retry recoverable errors with exponential backoff', async () => {
      // Mock 3 server errors followed by success
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
          text: jest.fn().mockResolvedValue('Server error')
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
          text: jest.fn().mockResolvedValue('Server error')
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: jest.fn().mockResolvedValue({
            ticket_id: 'retry-success-ticket',
            expires_at: Math.floor(Date.now() / 1000) + 300,
            created_at: Math.floor(Date.now() / 1000),
            ttl_seconds: 300,
            single_use: true,
            websocket_url: 'wss://api.example.com/ws?ticket=retry-success-ticket'
          })
        });

      const result = await ticketService.acquireTicket();

      expect(result.success).toBe(true);
      expect(result.ticket?.ticket).toBe('retry-success-ticket');
      expect(mockFetch).toHaveBeenCalledTimes(3); // 2 failures + 1 success
    });

    it('should fail after maximum retries', async () => {
      // Mock all retries failing
      mockFetch
        .mockResolvedValue({
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
          text: jest.fn().mockResolvedValue('Persistent server error')
        });

      const result = await ticketService.acquireTicket();

      expect(result.success).toBe(false);
      expect(result.error).toContain('Backend server error');
      expect(result.recoverable).toBe(false);
      expect(mockFetch).toHaveBeenCalledTimes(3); // Default max retries
    });
  });

  describe('Cache Management', () => {
    it('should clear ticket cache', () => {
      // Add a ticket to cache first
      const cacheStatsBefore = ticketService.getCacheStats();
      
      ticketService.clearTicketCache();
      
      const cacheStatsAfter = ticketService.getCacheStats();
      expect(cacheStatsAfter.size).toBe(0);
      expect(cacheStatsAfter.entries).toHaveLength(0);
    });

    it('should provide cache statistics', async () => {
      // Add a ticket to cache
      const mockTicketResponse = {
        ticket_id: 'cache-stats-ticket',
        expires_at: Math.floor(Date.now() / 1000) + 300,
        created_at: Math.floor(Date.now() / 1000),
        ttl_seconds: 300,
        single_use: true,
        websocket_url: 'wss://api.example.com/ws?ticket=cache-stats-ticket'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue(mockTicketResponse)
      });

      await ticketService.acquireTicket();

      const stats = ticketService.getCacheStats();
      expect(stats.size).toBe(1);
      expect(stats.entries).toHaveLength(1);
      expect(stats.entries[0].key).toBe('default');
      expect(stats.entries[0].timeUntilExpiry).toBeGreaterThan(0);
    });
  });

  describe('Configuration Management', () => {
    it('should allow configuration updates', () => {
      const newConfig = {
        defaultTtl: 600,
        refreshThreshold: 60000,
        maxRetries: 5
      };

      ticketService.updateConfig(newConfig);
      const updatedConfig = ticketService.getConfig();

      expect(updatedConfig.defaultTtl).toBe(600);
      expect(updatedConfig.refreshThreshold).toBe(60000);
      expect(updatedConfig.maxRetries).toBe(5);
    });

    it('should maintain enabled state in config', () => {
      const config = ticketService.getConfig();
      expect(typeof config.enabled).toBe('boolean');
    });
  });
});

describe('Singleton Export', () => {
  it('should export a singleton instance', () => {
    expect(websocketTicketService).toBeInstanceOf(WebSocketTicketService);
  });

  it('should maintain state across imports', async () => {
    // Test that the singleton maintains state
    const config1 = websocketTicketService.getConfig();
    websocketTicketService.updateConfig({ defaultTtl: 999 });
    const config2 = websocketTicketService.getConfig();
    
    expect(config1.defaultTtl).not.toBe(999);
    expect(config2.defaultTtl).toBe(999);
  });
});