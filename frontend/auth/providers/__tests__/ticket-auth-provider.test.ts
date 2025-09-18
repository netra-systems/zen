import { renderHook, act, waitFor } from '@testing-library/react';
import { ReactNode } from 'react';
import { TicketAuthProvider, useTicketAuth, TicketAuthData } from '../ticket-auth-provider';

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('TicketAuthProvider', () => {
  const defaultProps = {
    apiBaseUrl: 'http://localhost:8000',
    enableAutoRefresh: false, // Disable for testing
  };

  const wrapper = ({ children }: { children: ReactNode }) => (
    <TicketAuthProvider {...defaultProps}>{children}</TicketAuthProvider>
  );

  beforeEach(() => {
    jest.clearAllMocks();
    jest.clearAllTimers();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('useTicketAuth hook', () => {
    it('should throw error when used outside provider', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      expect(() => {
        renderHook(() => useTicketAuth());
      }).toThrow('useTicketAuth must be used within a TicketAuthProvider');
      
      consoleSpy.mockRestore();
    });

    it('should provide initial state', () => {
      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      expect(result.current.currentTicket).toBeNull();
      expect(result.current.isTicketValid).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });

  describe('generateTicket', () => {
    it('should successfully generate a ticket', async () => {
      const mockTicketData = {
        ticketId: 'test-ticket-123',
        userId: 'user-123',
        expires: '2024-12-31T23:59:59Z',
        permissions: ['websocket']
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTicketData
      });

      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      let generatedTicket: TicketAuthData | null = null;

      await act(async () => {
        generatedTicket = await result.current.generateTicket('user-123', ['websocket']);
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/tickets/generate',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ userId: 'user-123', permissions: ['websocket'] })
        }
      );

      expect(generatedTicket).toEqual({
        ticketId: 'test-ticket-123',
        userId: 'user-123',
        expires: new Date('2024-12-31T23:59:59Z'),
        permissions: ['websocket']
      });

      expect(result.current.currentTicket).toEqual(generatedTicket);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should handle generation failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      });

      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      let generatedTicket: TicketAuthData | null = null;

      await act(async () => {
        generatedTicket = await result.current.generateTicket('user-123');
      });

      expect(generatedTicket).toBeNull();
      expect(result.current.currentTicket).toBeNull();
      expect(result.current.error).toEqual({
        code: 'GENERATION_FAILED',
        message: 'HTTP 500: Internal Server Error',
        timestamp: expect.any(Date)
      });
    });

    it('should validate user ID', async () => {
      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      let generatedTicket: TicketAuthData | null = null;

      await act(async () => {
        generatedTicket = await result.current.generateTicket('');
      });

      expect(generatedTicket).toBeNull();
      expect(result.current.error).toEqual({
        code: 'INVALID_USER_ID',
        message: 'User ID is required',
        timestamp: expect.any(Date)
      });
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      let generatedTicket: TicketAuthData | null = null;

      await act(async () => {
        generatedTicket = await result.current.generateTicket('user-123');
      });

      expect(generatedTicket).toBeNull();
      expect(result.current.error).toEqual({
        code: 'GENERATION_FAILED',
        message: 'Network error',
        timestamp: expect.any(Date)
      });
    });
  });

  describe('validateTicket', () => {
    it('should successfully validate a ticket', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ valid: true })
      });

      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      let isValid = false;

      await act(async () => {
        isValid = await result.current.validateTicket('test-ticket-123');
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/tickets/validate',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticketId: 'test-ticket-123' })
        }
      );

      expect(isValid).toBe(true);
      expect(result.current.error).toBeNull();
    });

    it('should handle invalid ticket', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ valid: false })
      });

      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      let isValid = true;

      await act(async () => {
        isValid = await result.current.validateTicket('invalid-ticket');
      });

      expect(isValid).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should validate ticket ID', async () => {
      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      let isValid = true;

      await act(async () => {
        isValid = await result.current.validateTicket('');
      });

      expect(isValid).toBe(false);
      expect(result.current.error).toEqual({
        code: 'INVALID_TICKET_ID',
        message: 'Ticket ID is required',
        timestamp: expect.any(Date)
      });
      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe('refreshTicket', () => {
    it('should successfully refresh a ticket', async () => {
      const mockRefreshedData = {
        ticketId: 'refreshed-ticket-123',
        userId: 'user-123',
        expires: '2024-12-31T23:59:59Z',
        permissions: ['websocket']
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockRefreshedData
      });

      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      let refreshedTicket: TicketAuthData | null = null;

      await act(async () => {
        refreshedTicket = await result.current.refreshTicket('old-ticket-123');
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/tickets/refresh',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticketId: 'old-ticket-123' })
        }
      );

      expect(refreshedTicket).toEqual({
        ticketId: 'refreshed-ticket-123',
        userId: 'user-123',
        expires: new Date('2024-12-31T23:59:59Z'),
        permissions: ['websocket']
      });

      expect(result.current.currentTicket).toEqual(refreshedTicket);
    });

    it('should handle refresh failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found'
      });

      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      let refreshedTicket: TicketAuthData | null = null;

      await act(async () => {
        refreshedTicket = await result.current.refreshTicket('nonexistent-ticket');
      });

      expect(refreshedTicket).toBeNull();
      expect(result.current.error).toEqual({
        code: 'REFRESH_FAILED',
        message: 'HTTP 404: Not Found',
        timestamp: expect.any(Date)
      });
    });
  });

  describe('revokeTicket', () => {
    it('should successfully revoke a ticket', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ revoked: true })
      });

      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      let isRevoked = false;

      await act(async () => {
        isRevoked = await result.current.revokeTicket('test-ticket-123');
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/tickets/revoke',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticketId: 'test-ticket-123' })
        }
      );

      expect(isRevoked).toBe(true);
      expect(result.current.error).toBeNull();
    });

    it('should clear current ticket if revoked ticket matches', async () => {
      const mockTicketData = {
        ticketId: 'test-ticket-123',
        userId: 'user-123',
        expires: '2024-12-31T23:59:59Z',
        permissions: ['websocket']
      };

      // First generate a ticket
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTicketData
      });

      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      await act(async () => {
        await result.current.generateTicket('user-123');
      });

      expect(result.current.currentTicket).toBeTruthy();

      // Then revoke it
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ revoked: true })
      });

      await act(async () => {
        await result.current.revokeTicket('test-ticket-123');
      });

      expect(result.current.currentTicket).toBeNull();
    });
  });

  describe('isTicketValid calculation', () => {
    it('should return true for valid future ticket', () => {
      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      act(() => {
        // Manually set a future ticket for testing
        (result.current as any).setCurrentTicket({
          ticketId: 'test',
          userId: 'user',
          expires: new Date(Date.now() + 60000), // 1 minute in future
          permissions: []
        });
      });

      expect(result.current.isTicketValid).toBe(true);
    });

    it('should return false for expired ticket', () => {
      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      act(() => {
        // Manually set an expired ticket for testing
        (result.current as any).setCurrentTicket({
          ticketId: 'test',
          userId: 'user',
          expires: new Date(Date.now() - 60000), // 1 minute in past
          permissions: []
        });
      });

      expect(result.current.isTicketValid).toBe(false);
    });

    it('should return false for null ticket', () => {
      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      expect(result.current.isTicketValid).toBe(false);
    });
  });

  describe('utility functions', () => {
    it('should clear error', () => {
      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      // Set an error first
      act(() => {
        (result.current as any).setError({
          code: 'TEST_ERROR',
          message: 'Test error',
          timestamp: new Date()
        });
      });

      expect(result.current.error).toBeTruthy();

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });

    it('should clear ticket', () => {
      const { result } = renderHook(() => useTicketAuth(), { wrapper });

      // Set a ticket first
      act(() => {
        (result.current as any).setCurrentTicket({
          ticketId: 'test',
          userId: 'user',
          expires: new Date(),
          permissions: []
        });
      });

      expect(result.current.currentTicket).toBeTruthy();

      act(() => {
        result.current.clearTicket();
      });

      expect(result.current.currentTicket).toBeNull();
      expect(result.current.error).toBeNull();
    });
  });

  describe('auto-refresh', () => {
    it('should auto-refresh ticket when enabled and near expiry', async () => {
      const autoRefreshWrapper = ({ children }: { children: ReactNode }) => (
        <TicketAuthProvider 
          {...defaultProps} 
          enableAutoRefresh={true}
          refreshThreshold={1} // 1 minute threshold
        >
          {children}
        </TicketAuthProvider>
      );

      const { result } = renderHook(() => useTicketAuth(), { wrapper: autoRefreshWrapper });

      // Set up a ticket that expires in 30 seconds
      const nearExpiryTicket = {
        ticketId: 'expiring-ticket',
        userId: 'user-123',
        expires: new Date(Date.now() + 30000), // 30 seconds
        permissions: ['websocket']
      };

      // Mock refresh response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ticketId: 'refreshed-ticket',
          userId: 'user-123',
          expires: new Date(Date.now() + 3600000).toISOString(), // 1 hour
          permissions: ['websocket']
        })
      });

      act(() => {
        (result.current as any).setCurrentTicket(nearExpiryTicket);
      });

      // Fast-forward past the threshold check
      act(() => {
        jest.advanceTimersByTime(60000); // 1 minute
      });

      // Wait for the refresh to complete
      await waitFor(() => {
        expect(result.current.currentTicket?.ticketId).toBe('refreshed-ticket');
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/tickets/refresh',
        expect.any(Object)
      );
    });
  });
});