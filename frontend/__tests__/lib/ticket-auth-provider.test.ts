/**
 * Test Suite for TicketAuthProvider - Issue #1295
 * 
 * Comprehensive tests for frontend WebSocket ticket authentication implementation.
 * Tests the integration between auth context, ticket provider, and WebSocket service.
 */

import { TicketAuthProvider, ticketAuthProvider } from '@/lib/ticket-auth-provider';
import { websocketTicketService } from '@/services/websocketTicketService';
import type { TicketRequestResult, WebSocketTicket } from '@/types/websocket-ticket';

// Mock the dependencies
jest.mock('@/services/websocketTicketService');
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn()
  }
}));

// Mock localStorage
const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; }
  };
})();

Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

describe('TicketAuthProvider', () => {
  const mockWebsocketTicketService = websocketTicketService as jest.Mocked<typeof websocketTicketService>;
  
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.clear();
    
    // Default mock implementations
    mockWebsocketTicketService.acquireTicket.mockResolvedValue({
      success: true,
      ticket: {
        ticket: 'test-ticket-123',
        expires_at: Date.now() + 300000, // 5 minutes from now
        created_at: Date.now(),
        websocket_url: 'wss://api-staging.netrasystems.ai/ws?ticket=test-ticket-123'
      }
    });
    
    mockWebsocketTicketService.clearTicketCache.mockImplementation(() => {});
    mockWebsocketTicketService.getCacheStats.mockReturnValue({
      size: 0,
      entries: []
    });
  });

  describe('Constructor and Configuration', () => {
    it('should initialize with default configuration', () => {
      const provider = new TicketAuthProvider();
      const config = provider.getConfig();
      
      expect(config).toEqual({
        enabled: true,
        defaultTtl: 300,
        clearOnAuthChange: true,
        maxRetries: 3
      });
    });

    it('should accept custom configuration', () => {
      const customConfig = {
        enabled: false,
        defaultTtl: 600,
        clearOnAuthChange: false,
        maxRetries: 5
      };
      
      const provider = new TicketAuthProvider(customConfig);
      const config = provider.getConfig();
      
      expect(config).toEqual(customConfig);
    });

    it('should allow configuration updates', () => {
      const provider = new TicketAuthProvider();
      
      provider.updateConfig({
        enabled: false,
        defaultTtl: 600
      });
      
      const config = provider.getConfig();
      expect(config.enabled).toBe(false);
      expect(config.defaultTtl).toBe(600);
      expect(config.clearOnAuthChange).toBe(true); // Should preserve other values
    });
  });

  describe('Ticket Acquisition', () => {
    it('should successfully acquire a ticket when enabled and authenticated', async () => {
      const provider = new TicketAuthProvider();
      provider.updateAuthToken('valid-jwt-token');
      
      const result = await provider.getTicket();
      
      expect(result.success).toBe(true);
      expect(result.ticket).toBeDefined();
      expect(result.ticket?.ticket).toBe('test-ticket-123');
      expect(mockWebsocketTicketService.acquireTicket).toHaveBeenCalledWith(300);
    });

    it('should use custom TTL when provided', async () => {
      const provider = new TicketAuthProvider();
      provider.updateAuthToken('valid-jwt-token');
      
      const result = await provider.getTicket(600);
      
      expect(result.success).toBe(true);
      expect(mockWebsocketTicketService.acquireTicket).toHaveBeenCalledWith(600);
    });

    it('should fail when ticket authentication is disabled', async () => {
      const provider = new TicketAuthProvider({ enabled: false });
      provider.updateAuthToken('valid-jwt-token');
      
      const result = await provider.getTicket();
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('Ticket authentication is disabled');
      expect(result.recoverable).toBe(false);
      expect(mockWebsocketTicketService.acquireTicket).not.toHaveBeenCalled();
    });

    it('should fail when no auth token is available', async () => {
      const provider = new TicketAuthProvider();
      // No auth token set
      
      const result = await provider.getTicket();
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('No authentication token available');
      expect(result.recoverable).toBe(false);
      expect(mockWebsocketTicketService.acquireTicket).not.toHaveBeenCalled();
    });

    it('should fallback to localStorage token when no token set directly', async () => {
      mockLocalStorage.setItem('jwt_token', 'stored-jwt-token');
      
      const provider = new TicketAuthProvider();
      
      const result = await provider.getTicket();
      
      expect(result.success).toBe(true);
      expect(mockWebsocketTicketService.acquireTicket).toHaveBeenCalled();
    });

    it('should handle ticket service errors gracefully', async () => {
      const provider = new TicketAuthProvider();
      provider.updateAuthToken('valid-jwt-token');
      
      mockWebsocketTicketService.acquireTicket.mockResolvedValue({
        success: false,
        error: 'Backend unavailable',
        recoverable: true
      });
      
      const result = await provider.getTicket();
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('Backend unavailable');
      expect(result.recoverable).toBe(true);
    });

    it('should handle unexpected errors during ticket acquisition', async () => {
      const provider = new TicketAuthProvider();
      provider.updateAuthToken('valid-jwt-token');
      
      mockWebsocketTicketService.acquireTicket.mockRejectedValue(new Error('Network failure'));
      
      const result = await provider.getTicket();
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('Ticket acquisition error: Network failure');
      expect(result.recoverable).toBe(true);
    });
  });

  describe('Cache Management', () => {
    it('should clear ticket cache when requested', () => {
      const provider = new TicketAuthProvider();
      
      provider.clearTicketCache();
      
      expect(mockWebsocketTicketService.clearTicketCache).toHaveBeenCalled();
    });

    it('should clear cache when auth token changes and configured to do so', () => {
      const provider = new TicketAuthProvider({ clearOnAuthChange: true });
      
      provider.updateAuthToken('initial-token');
      jest.clearAllMocks();
      
      provider.updateAuthToken('new-token');
      
      expect(mockWebsocketTicketService.clearTicketCache).toHaveBeenCalled();
    });

    it('should not clear cache when auth token changes if configured not to', () => {
      const provider = new TicketAuthProvider({ clearOnAuthChange: false });
      
      provider.updateAuthToken('initial-token');
      jest.clearAllMocks();
      
      provider.updateAuthToken('new-token');
      
      expect(mockWebsocketTicketService.clearTicketCache).not.toHaveBeenCalled();
    });

    it('should not clear cache when same token is set again', () => {
      const provider = new TicketAuthProvider({ clearOnAuthChange: true });
      
      provider.updateAuthToken('same-token');
      jest.clearAllMocks();
      
      provider.updateAuthToken('same-token');
      
      expect(mockWebsocketTicketService.clearTicketCache).not.toHaveBeenCalled();
    });
  });

  describe('Feature Flag Control', () => {
    it('should enable/disable ticket authentication', () => {
      const provider = new TicketAuthProvider();
      
      expect(provider.isEnabled()).toBe(true);
      
      provider.setEnabled(false);
      expect(provider.isEnabled()).toBe(false);
      
      provider.setEnabled(true);
      expect(provider.isEnabled()).toBe(true);
    });

    it('should clear cache when disabling ticket authentication', () => {
      const provider = new TicketAuthProvider();
      
      provider.setEnabled(false);
      
      expect(mockWebsocketTicketService.clearTicketCache).toHaveBeenCalled();
    });

    it('should not clear cache when enabling ticket authentication', () => {
      const provider = new TicketAuthProvider({ enabled: false });
      jest.clearAllMocks();
      
      provider.setEnabled(true);
      
      expect(mockWebsocketTicketService.clearTicketCache).not.toHaveBeenCalled();
    });
  });

  describe('Status and Debugging', () => {
    it('should provide comprehensive status information', () => {
      const provider = new TicketAuthProvider();
      provider.updateAuthToken('test-token');
      
      mockWebsocketTicketService.getCacheStats.mockReturnValue({
        size: 1,
        entries: [{
          key: 'default',
          expiresAt: new Date(Date.now() + 300000).toISOString(),
          timeUntilExpiry: 300000
        }]
      });
      
      const status = provider.getStatus();
      
      expect(status.enabled).toBe(true);
      expect(status.hasAuthToken).toBe(true);
      expect(status.cacheStats.size).toBe(1);
      expect(status.config).toBeDefined();
    });

    it('should test ticket acquisition with timing information', async () => {
      const provider = new TicketAuthProvider();
      provider.updateAuthToken('test-token');
      
      const testResult = await provider.testTicketAcquisition();
      
      expect(testResult.success).toBe(true);
      expect(testResult.ticket).toBeDefined();
      expect(testResult.timing).toBeGreaterThan(0);
      expect(testResult.error).toBeUndefined();
    });

    it('should handle test ticket acquisition errors', async () => {
      const provider = new TicketAuthProvider();
      provider.updateAuthToken('test-token');
      
      mockWebsocketTicketService.acquireTicket.mockRejectedValue(new Error('Test error'));
      
      const testResult = await provider.testTicketAcquisition();
      
      expect(testResult.success).toBe(false);
      expect(testResult.error).toBe('Test error');
      expect(testResult.timing).toBeGreaterThan(0);
      expect(testResult.ticket).toBeUndefined();
    });
  });

  describe('Singleton Instance', () => {
    it('should provide a singleton instance', () => {
      expect(ticketAuthProvider).toBeInstanceOf(TicketAuthProvider);
    });

    it('should maintain state across singleton accesses', () => {
      ticketAuthProvider.updateAuthToken('singleton-token');
      
      const status = ticketAuthProvider.getStatus();
      expect(status.hasAuthToken).toBe(true);
    });
  });

  describe('Integration Scenarios', () => {
    it('should handle complete auth lifecycle', async () => {
      const provider = new TicketAuthProvider();
      
      // Initial state - no auth
      expect(provider.getStatus().hasAuthToken).toBe(false);
      
      // Login
      provider.updateAuthToken('jwt-token');
      expect(provider.getStatus().hasAuthToken).toBe(true);
      
      // Get ticket
      const result = await provider.getTicket();
      expect(result.success).toBe(true);
      
      // Token refresh
      provider.updateAuthToken('refreshed-jwt-token');
      expect(mockWebsocketTicketService.clearTicketCache).toHaveBeenCalled();
      
      // Logout
      provider.updateAuthToken(null);
      expect(provider.getStatus().hasAuthToken).toBe(false);
    });

    it('should handle feature flag changes during operation', async () => {
      const provider = new TicketAuthProvider();
      provider.updateAuthToken('jwt-token');
      
      // Enabled - should work
      let result = await provider.getTicket();
      expect(result.success).toBe(true);
      
      // Disabled - should fail
      provider.setEnabled(false);
      result = await provider.getTicket();
      expect(result.success).toBe(false);
      expect(result.error).toBe('Ticket authentication is disabled');
      
      // Re-enabled - should work again
      provider.setEnabled(true);
      result = await provider.getTicket();
      expect(result.success).toBe(true);
    });

    it('should handle backend service failures gracefully', async () => {
      const provider = new TicketAuthProvider();
      provider.updateAuthToken('jwt-token');
      
      // Simulate various backend failures
      const failures = [
        { error: 'Network timeout', recoverable: true },
        { error: 'Rate limited', recoverable: true },
        { error: 'Service unavailable', recoverable: true },
        { error: 'Invalid token', recoverable: false }
      ];
      
      for (const failure of failures) {
        mockWebsocketTicketService.acquireTicket.mockResolvedValue({
          success: false,
          error: failure.error,
          recoverable: failure.recoverable
        });
        
        const result = await provider.getTicket();
        
        expect(result.success).toBe(false);
        expect(result.error).toBe(failure.error);
        expect(result.recoverable).toBe(failure.recoverable);
      }
    });
  });

  describe('Error Handling', () => {
    it('should handle cache clearing errors gracefully', () => {
      const provider = new TicketAuthProvider();
      
      mockWebsocketTicketService.clearTicketCache.mockImplementation(() => {
        throw new Error('Cache error');
      });
      
      // Should not throw
      expect(() => provider.clearTicketCache()).not.toThrow();
    });

    it('should handle missing localStorage gracefully', async () => {
      // Mock window.localStorage to be undefined
      const originalLocalStorage = Object.getOwnPropertyDescriptor(window, 'localStorage');
      
      // @ts-ignore
      delete window.localStorage;
      
      const provider = new TicketAuthProvider();
      
      const result = await provider.getTicket();
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('No authentication token available');
      
      // Restore localStorage
      if (originalLocalStorage) {
        Object.defineProperty(window, 'localStorage', originalLocalStorage);
      }
    });
  });
});