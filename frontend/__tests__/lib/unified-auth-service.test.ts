/**
 * Tests for UnifiedAuthService ticket authentication functionality
 */

import { jest } from '@jest/globals';
import { unifiedAuthService } from '@/lib/unified-auth-service';

// Mock dependencies
jest.mock('@/lib/auth-service-config');
jest.mock('@/auth');
jest.mock('@/lib/auth-interceptor');
jest.mock('@/lib/logger');

// Mock fetch globally
global.fetch = jest.fn();

describe('UnifiedAuthService Ticket Authentication', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    unifiedAuthService.clearTicketCache();
  });

  describe('requestWebSocketTicket', () => {
    it('should successfully request a ticket with valid token', async () => {
      // Mock auth service to return a token
      const mockAuthService = require('@/auth');
      mockAuthService.authService.getToken.mockReturnValue('valid-jwt-token');

      // Mock successful fetch response
      const mockTicketResponse = {
        ticket: 'valid-ticket-123',
        expires_at: Date.now() + 300000 // 5 minutes from now
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue(mockTicketResponse)
      });

      const result = await unifiedAuthService.requestWebSocketTicket();

      expect(result.success).toBe(true);
      expect(result.ticket).toEqual(mockTicketResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/auth/websocket-ticket',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer valid-jwt-token',
            'Content-Type': 'application/json'
          })
        })
      );
    });

    it('should handle missing token gracefully', async () => {
      // Mock auth service to return no token
      const mockAuthService = require('@/auth');
      mockAuthService.authService.getToken.mockReturnValue(null);

      const result = await unifiedAuthService.requestWebSocketTicket();

      expect(result.success).toBe(false);
      expect(result.error).toBe('No authentication token available');
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should handle 404 response (endpoint not available)', async () => {
      // Mock auth service to return a token
      const mockAuthService = require('@/auth');
      mockAuthService.authService.getToken.mockReturnValue('valid-jwt-token');

      // Mock 404 response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        text: jest.fn().mockResolvedValue('Endpoint not found')
      });

      const result = await unifiedAuthService.requestWebSocketTicket();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Ticket endpoint not available');
    });

    it('should handle 401 response (unauthorized)', async () => {
      // Mock auth service to return a token
      const mockAuthService = require('@/auth');
      mockAuthService.authService.getToken.mockReturnValue('invalid-jwt-token');

      // Mock 401 response
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        text: jest.fn().mockResolvedValue('Invalid token')
      });

      const result = await unifiedAuthService.requestWebSocketTicket();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Authentication required for ticket request');
    });

    it('should handle network errors', async () => {
      // Mock auth service to return a token
      const mockAuthService = require('@/auth');
      mockAuthService.authService.getToken.mockReturnValue('valid-jwt-token');

      // Mock network error
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      const result = await unifiedAuthService.requestWebSocketTicket();

      expect(result.success).toBe(false);
      expect(result.error).toContain('Network error');
    });
  });

  describe('getWebSocketTicket', () => {
    it('should return cached ticket if still valid', async () => {
      // Mock auth service to return a token
      const mockAuthService = require('@/auth');
      mockAuthService.authService.getToken.mockReturnValue('valid-jwt-token');

      // Mock successful fetch response for initial request
      const mockTicketResponse = {
        ticket: 'cached-ticket-123',
        expires_at: Date.now() + 300000 // 5 minutes from now
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue(mockTicketResponse)
      });

      // First call - should make network request
      const result1 = await unifiedAuthService.getWebSocketTicket();
      expect(result1.success).toBe(true);
      expect(global.fetch).toHaveBeenCalledTimes(1);

      // Second call - should use cached ticket
      const result2 = await unifiedAuthService.getWebSocketTicket();
      expect(result2.success).toBe(true);
      expect(result2.ticket?.ticket).toBe('cached-ticket-123');
      expect(global.fetch).toHaveBeenCalledTimes(1); // No additional network call
    });

    it('should refresh ticket if cached ticket is close to expiry', async () => {
      // Mock auth service to return a token
      const mockAuthService = require('@/auth');
      mockAuthService.authService.getToken.mockReturnValue('valid-jwt-token');

      // Mock first ticket response (expires soon)
      const expiringSoonTicket = {
        ticket: 'expiring-ticket-123',
        expires_at: Date.now() + 10000 // 10 seconds from now (within refresh threshold)
      };

      // Mock second ticket response (fresh)
      const freshTicket = {
        ticket: 'fresh-ticket-456',
        expires_at: Date.now() + 300000 // 5 minutes from now
      };

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: jest.fn().mockResolvedValue(expiringSoonTicket)
        })
        .mockResolvedValueOnce({
          ok: true,
          json: jest.fn().mockResolvedValue(freshTicket)
        });

      // First call - gets expiring ticket
      const result1 = await unifiedAuthService.getWebSocketTicket();
      expect(result1.success).toBe(true);
      expect(result1.ticket?.ticket).toBe('expiring-ticket-123');

      // Second call - should refresh because ticket expires soon
      const result2 = await unifiedAuthService.getWebSocketTicket();
      expect(result2.success).toBe(true);
      expect(result2.ticket?.ticket).toBe('fresh-ticket-456');
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('clearTicketCache', () => {
    it('should clear cached tickets', async () => {
      // Mock auth service to return a token
      const mockAuthService = require('@/auth');
      mockAuthService.authService.getToken.mockReturnValue('valid-jwt-token');

      // Mock successful fetch response
      const mockTicketResponse = {
        ticket: 'cached-ticket-123',
        expires_at: Date.now() + 300000
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockTicketResponse)
      });

      // Get a ticket to populate cache
      await unifiedAuthService.getWebSocketTicket();
      expect(global.fetch).toHaveBeenCalledTimes(1);

      // Clear cache
      unifiedAuthService.clearTicketCache();

      // Next call should make new network request
      await unifiedAuthService.getWebSocketTicket();
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('getWebSocketAuthConfig', () => {
    it('should return config with ticket authentication enabled by default', () => {
      // Mock auth service to return a token
      const mockAuthService = require('@/auth');
      mockAuthService.authService.getToken.mockReturnValue('jwt-token');

      const config = unifiedAuthService.getWebSocketAuthConfig();

      expect(config.token).toBe('jwt-token');
      expect(config.useTicketAuth).toBe(true);
      expect(typeof config.getTicket).toBe('function');
      expect(typeof config.refreshToken).toBe('function');
    });

    it('should disable ticket auth when feature flag is false', () => {
      // Mock environment variable
      const originalEnv = process.env.NEXT_PUBLIC_ENABLE_TICKET_AUTH;
      process.env.NEXT_PUBLIC_ENABLE_TICKET_AUTH = 'false';

      try {
        const config = unifiedAuthService.getWebSocketAuthConfig();
        expect(config.useTicketAuth).toBe(false);
      } finally {
        // Restore original environment
        if (originalEnv === undefined) {
          delete process.env.NEXT_PUBLIC_ENABLE_TICKET_AUTH;
        } else {
          process.env.NEXT_PUBLIC_ENABLE_TICKET_AUTH = originalEnv;
        }
      }
    });
  });

  describe('error handling integration', () => {
    it('should clear ticket cache on auth errors', () => {
      const clearCacheSpy = jest.spyOn(unifiedAuthService, 'clearTicketCache');

      // Simulate auth error
      unifiedAuthService.handleAuthError({ status: 401, message: 'Unauthorized' });

      expect(clearCacheSpy).toHaveBeenCalled();
    });

    it('should clear ticket cache on logout', async () => {
      const clearCacheSpy = jest.spyOn(unifiedAuthService, 'clearTicketCache');

      // Mock auth service methods
      const mockAuthService = require('@/auth');
      mockAuthService.authService.getAuthConfig.mockResolvedValue({});
      mockAuthService.authService.handleLogout.mockResolvedValue(undefined);

      await unifiedAuthService.handleLogout();

      expect(clearCacheSpy).toHaveBeenCalled();
    });
  });
});