/**
 * Tests for ResilientWebSocketService ticket authentication functionality
 */

import { jest } from '@jest/globals';

// Mock dependencies before importing
jest.mock('@/lib/logger');

// Create a mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;

  constructor(public url: string) {
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(data: string) {
    // Mock send implementation
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason, wasClean: true }));
    }
  }
}

// Replace global WebSocket with mock
(global as any).WebSocket = MockWebSocket;

// Now import the service after mocking
import resilientWebSocketService from '@/services/webSocketServiceResilient';

describe('ResilientWebSocketService Ticket Authentication', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    resilientWebSocketService.disconnect();
  });

  afterEach(() => {
    resilientWebSocketService.disconnect();
  });

  describe('URL construction', () => {
    it('should construct URL with ticket parameter', () => {
      const baseUrl = 'ws://localhost:8000/ws';
      const ticket = 'test-ticket-123';
      
      // Test private method via public interface
      const service = resilientWebSocketService as any;
      const result = service.addTicketToUrl(baseUrl, ticket);
      
      expect(result).toBe('ws://localhost:8000/ws?ticket=test-ticket-123');
    });

    it('should construct URL with ticket parameter when URL already has query params', () => {
      const baseUrl = 'ws://localhost:8000/ws?existing=param';
      const ticket = 'test-ticket-456';
      
      const service = resilientWebSocketService as any;
      const result = service.addTicketToUrl(baseUrl, ticket);
      
      expect(result).toBe('ws://localhost:8000/ws?existing=param&ticket=test-ticket-456');
    });

    it('should prefer ticket over JWT in getSecureUrl when ticket is valid', () => {
      const baseUrl = 'ws://localhost:8000/ws';
      
      // Set up service with both token and ticket
      const service = resilientWebSocketService as any;
      service.options = { token: 'jwt-token' };
      service.currentTicket = 'valid-ticket';
      service.ticketExpiry = Date.now() + 300000; // 5 minutes from now
      
      const result = resilientWebSocketService.getSecureUrl(baseUrl);
      
      expect(result).toBe('ws://localhost:8000/ws?ticket=valid-ticket');
    });

    it('should fallback to JWT when ticket is expired', () => {
      const baseUrl = 'ws://localhost:8000/ws';
      
      // Set up service with expired ticket and valid JWT
      const service = resilientWebSocketService as any;
      service.options = { token: 'jwt-token' };
      service.currentTicket = 'expired-ticket';
      service.ticketExpiry = Date.now() - 1000; // 1 second ago (expired)
      
      const result = resilientWebSocketService.getSecureUrl(baseUrl);
      
      expect(result).toBe('ws://localhost:8000/ws?jwt=jwt-token');
    });

    it('should return base URL when no authentication is available', () => {
      const baseUrl = 'ws://localhost:8000/ws';
      
      // Clear any existing auth
      const service = resilientWebSocketService as any;
      service.options = {};
      service.currentTicket = null;
      service.ticketExpiry = null;
      
      const result = resilientWebSocketService.getSecureUrl(baseUrl);
      
      expect(result).toBe('ws://localhost:8000/ws');
    });
  });

  describe('prepareAuthenticatedUrl', () => {
    it('should use ticket authentication when available', async () => {
      const baseUrl = 'ws://localhost:8000/ws';
      const mockTicket = {
        ticket: 'fresh-ticket-789',
        expires_at: Date.now() + 300000
      };

      const mockGetTicket = jest.fn().mockResolvedValue({
        success: true,
        ticket: mockTicket
      });

      const service = resilientWebSocketService as any;
      service.options = {
        useTicketAuth: true,
        getTicket: mockGetTicket,
        token: 'fallback-jwt'
      };

      const result = await service.prepareAuthenticatedUrl(baseUrl);

      expect(mockGetTicket).toHaveBeenCalled();
      expect(result).toBe('ws://localhost:8000/ws?ticket=fresh-ticket-789');
      expect(service.currentTicket).toBe('fresh-ticket-789');
      expect(service.ticketExpiry).toBe(mockTicket.expires_at);
    });

    it('should fallback to JWT when ticket request fails', async () => {
      const baseUrl = 'ws://localhost:8000/ws';

      const mockGetTicket = jest.fn().mockResolvedValue({
        success: false,
        error: 'Ticket endpoint not available'
      });

      const service = resilientWebSocketService as any;
      service.options = {
        useTicketAuth: true,
        getTicket: mockGetTicket,
        token: 'fallback-jwt-token'
      };

      const result = await service.prepareAuthenticatedUrl(baseUrl);

      expect(mockGetTicket).toHaveBeenCalled();
      expect(result).toBe('ws://localhost:8000/ws?jwt=fallback-jwt-token');
    });

    it('should use JWT when ticket auth is disabled', async () => {
      const baseUrl = 'ws://localhost:8000/ws';

      const service = resilientWebSocketService as any;
      service.options = {
        useTicketAuth: false,
        token: 'jwt-only-token'
      };

      const result = await service.prepareAuthenticatedUrl(baseUrl);

      expect(result).toBe('ws://localhost:8000/ws?jwt=jwt-only-token');
    });

    it('should return base URL when no auth is configured', async () => {
      const baseUrl = 'ws://localhost:8000/ws';

      const service = resilientWebSocketService as any;
      service.options = {
        useTicketAuth: false
      };

      const result = await service.prepareAuthenticatedUrl(baseUrl);

      expect(result).toBe('ws://localhost:8000/ws');
    });

    it('should handle ticket request errors gracefully', async () => {
      const baseUrl = 'ws://localhost:8000/ws';

      const mockGetTicket = jest.fn().mockRejectedValue(new Error('Network error'));

      const service = resilientWebSocketService as any;
      service.options = {
        useTicketAuth: true,
        getTicket: mockGetTicket,
        token: 'fallback-jwt'
      };

      const result = await service.prepareAuthenticatedUrl(baseUrl);

      expect(result).toBe('ws://localhost:8000/ws?jwt=fallback-jwt');
    });
  });

  describe('refreshTicketIfNeeded', () => {
    it('should return true if current ticket is still valid', async () => {
      const service = resilientWebSocketService as any;
      service.options = {
        useTicketAuth: true,
        getTicket: jest.fn()
      };
      service.currentTicket = 'valid-ticket';
      service.ticketExpiry = Date.now() + 300000; // 5 minutes from now

      const result = await resilientWebSocketService.refreshTicketIfNeeded();

      expect(result).toBe(true);
      expect(service.options.getTicket).not.toHaveBeenCalled();
    });

    it('should refresh ticket when close to expiry', async () => {
      const newTicket = {
        ticket: 'refreshed-ticket',
        expires_at: Date.now() + 300000
      };

      const mockGetTicket = jest.fn().mockResolvedValue({
        success: true,
        ticket: newTicket
      });

      const service = resilientWebSocketService as any;
      service.options = {
        useTicketAuth: true,
        getTicket: mockGetTicket
      };
      service.currentTicket = 'expiring-ticket';
      service.ticketExpiry = Date.now() + 30000; // 30 seconds (within refresh threshold)

      const result = await resilientWebSocketService.refreshTicketIfNeeded();

      expect(result).toBe(true);
      expect(mockGetTicket).toHaveBeenCalled();
      expect(service.currentTicket).toBe('refreshed-ticket');
      expect(service.ticketExpiry).toBe(newTicket.expires_at);
    });

    it('should return false when ticket refresh fails', async () => {
      const mockGetTicket = jest.fn().mockResolvedValue({
        success: false,
        error: 'Refresh failed'
      });

      const service = resilientWebSocketService as any;
      service.options = {
        useTicketAuth: true,
        getTicket: mockGetTicket
      };
      service.currentTicket = null;

      const result = await resilientWebSocketService.refreshTicketIfNeeded();

      expect(result).toBe(false);
      expect(mockGetTicket).toHaveBeenCalled();
    });

    it('should return false when ticket auth is not enabled', async () => {
      const service = resilientWebSocketService as any;
      service.options = {
        useTicketAuth: false
      };

      const result = await resilientWebSocketService.refreshTicketIfNeeded();

      expect(result).toBe(false);
    });

    it('should prevent concurrent refresh attempts', async () => {
      const mockGetTicket = jest.fn().mockImplementation(() => {
        return new Promise(resolve => {
          setTimeout(() => resolve({
            success: true,
            ticket: { ticket: 'new-ticket', expires_at: Date.now() + 300000 }
          }), 100);
        });
      });

      const service = resilientWebSocketService as any;
      service.options = {
        useTicketAuth: true,
        getTicket: mockGetTicket
      };
      service.currentTicket = null;

      // Start two concurrent refresh attempts
      const [result1, result2] = await Promise.all([
        resilientWebSocketService.refreshTicketIfNeeded(),
        resilientWebSocketService.refreshTicketIfNeeded()
      ]);

      // Only one should succeed, the other should return false due to concurrent refresh
      expect(mockGetTicket).toHaveBeenCalledTimes(1);
      expect([result1, result2]).toContain(true);
      expect([result1, result2]).toContain(false);
    });
  });

  describe('updateToken', () => {
    it('should clear ticket cache when token is updated', async () => {
      const service = resilientWebSocketService as any;
      service.currentTicket = 'old-ticket';
      service.ticketExpiry = Date.now() + 300000;

      await resilientWebSocketService.updateToken('new-jwt-token');

      expect(service.currentTicket).toBeNull();
      expect(service.ticketExpiry).toBeNull();
      expect(service.currentToken).toBe('new-jwt-token');
    });
  });

  describe('connection lifecycle', () => {
    it('should use ticket authentication when connecting', async () => {
      const mockTicket = {
        ticket: 'connection-ticket',
        expires_at: Date.now() + 300000
      };

      const mockGetTicket = jest.fn().mockResolvedValue({
        success: true,
        ticket: mockTicket
      });

      await new Promise<void>((resolve) => {
        resilientWebSocketService.connect('ws://localhost:8000/ws', {
          useTicketAuth: true,
          getTicket: mockGetTicket,
          token: 'fallback-jwt',
          onOpen: () => {
            resolve();
          }
        });
      });

      expect(mockGetTicket).toHaveBeenCalled();
    });
  });
});