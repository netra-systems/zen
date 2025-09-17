import {
  validateTicketLocally,
  checkTicketPermissions,
  formatTimeUntilExpiry,
  shouldRefreshTicket,
  createTicketStorageKey,
  storeTicketSecurely,
  retrieveStoredTicket,
  clearStoredTicket,
  clearAllStoredTickets,
  sanitizeTicketError,
  createTicketAuthError,
  validateWebSocketUrl,
  buildTicketWebSocketUrl,
  extractTicketFromWebSocketUrl
} from '../ticket-auth-utils';
import { TicketAuthData } from '../../providers/ticket-auth-provider';

// Mock sessionStorage
const mockSessionStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  length: 0,
  clear: jest.fn(),
  key: jest.fn()
};

Object.defineProperty(window, 'sessionStorage', {
  value: mockSessionStorage,
  writable: true
});

describe('ticket-auth-utils', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('validateTicketLocally', () => {
    it('should validate a future ticket as valid', () => {
      const futureTicket: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date(Date.now() + 60000), // 1 minute in future
        permissions: ['websocket']
      };

      const result = validateTicketLocally(futureTicket);

      expect(result.isValid).toBe(true);
      expect(result.timeUntilExpiry).toBeGreaterThan(50000);
      expect(result.reason).toBeUndefined();
    });

    it('should validate an expired ticket as invalid', () => {
      const expiredTicket: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date(Date.now() - 60000), // 1 minute in past
        permissions: ['websocket']
      };

      const result = validateTicketLocally(expiredTicket);

      expect(result.isValid).toBe(false);
      expect(result.reason).toBe('Ticket has expired');
      expect(result.timeUntilExpiry).toBe(0);
    });

    it('should handle null ticket', () => {
      const result = validateTicketLocally(null);

      expect(result.isValid).toBe(false);
      expect(result.reason).toBe('No ticket provided');
      expect(result.timeUntilExpiry).toBeUndefined();
    });
  });

  describe('checkTicketPermissions', () => {
    const ticket: TicketAuthData = {
      ticketId: 'test-123',
      userId: 'user-123',
      expires: new Date(Date.now() + 60000),
      permissions: ['websocket', 'read', 'write']
    };

    it('should check permissions correctly when all required permissions are present', () => {
      const result = checkTicketPermissions(ticket, ['websocket', 'read']);

      expect(result.hasPermission).toBe(true);
      expect(result.missingPermissions).toEqual([]);
    });

    it('should check permissions correctly when some permissions are missing', () => {
      const result = checkTicketPermissions(ticket, ['websocket', 'admin']);

      expect(result.hasPermission).toBe(false);
      expect(result.missingPermissions).toEqual(['admin']);
    });

    it('should handle empty required permissions', () => {
      const result = checkTicketPermissions(ticket, []);

      expect(result.hasPermission).toBe(true);
      expect(result.missingPermissions).toEqual([]);
    });

    it('should handle null ticket', () => {
      const result = checkTicketPermissions(null, ['websocket']);

      expect(result.hasPermission).toBe(false);
      expect(result.missingPermissions).toEqual(['websocket']);
    });

    it('should handle ticket with no permissions', () => {
      const ticketNoPerms: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date(Date.now() + 60000),
        permissions: []
      };

      const result = checkTicketPermissions(ticketNoPerms, ['websocket']);

      expect(result.hasPermission).toBe(false);
      expect(result.missingPermissions).toEqual(['websocket']);
    });
  });

  describe('formatTimeUntilExpiry', () => {
    it('should format seconds correctly', () => {
      const ticket: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date(Date.now() + 30000), // 30 seconds
        permissions: []
      };

      const result = formatTimeUntilExpiry(ticket);
      expect(result).toBe('Less than 1 minute');
    });

    it('should format minutes correctly', () => {
      const ticket: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date(Date.now() + 150000), // 2.5 minutes
        permissions: []
      };

      const result = formatTimeUntilExpiry(ticket);
      expect(result).toBe('2 minutes');
    });

    it('should format hours correctly', () => {
      const ticket: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date(Date.now() + 3900000), // 1h 5m
        permissions: []
      };

      const result = formatTimeUntilExpiry(ticket);
      expect(result).toBe('1h 5m');
    });

    it('should format days correctly', () => {
      const ticket: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date(Date.now() + 90000000), // ~25 hours
        permissions: []
      };

      const result = formatTimeUntilExpiry(ticket);
      expect(result).toBe('1d 1h');
    });

    it('should handle expired ticket', () => {
      const ticket: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date(Date.now() - 60000), // 1 minute ago
        permissions: []
      };

      const result = formatTimeUntilExpiry(ticket);
      expect(result).toBe('Ticket has expired');
    });

    it('should handle null ticket', () => {
      const result = formatTimeUntilExpiry(null);
      expect(result).toBe('No ticket');
    });
  });

  describe('shouldRefreshTicket', () => {
    it('should recommend refresh for expiring ticket', () => {
      const ticket: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date(Date.now() + 240000), // 4 minutes (less than 5 minute default)
        permissions: []
      };

      const result = shouldRefreshTicket(ticket);
      expect(result).toBe(true);
    });

    it('should not recommend refresh for fresh ticket', () => {
      const ticket: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date(Date.now() + 600000), // 10 minutes
        permissions: []
      };

      const result = shouldRefreshTicket(ticket);
      expect(result).toBe(false);
    });

    it('should recommend refresh for expired ticket', () => {
      const ticket: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date(Date.now() - 60000), // expired
        permissions: []
      };

      const result = shouldRefreshTicket(ticket);
      expect(result).toBe(true);
    });

    it('should recommend refresh for null ticket', () => {
      const result = shouldRefreshTicket(null);
      expect(result).toBe(true);
    });

    it('should use custom threshold', () => {
      const ticket: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date(Date.now() + 600000), // 10 minutes
        permissions: []
      };

      const result = shouldRefreshTicket(ticket, 15); // 15 minute threshold
      expect(result).toBe(true);
    });
  });

  describe('storage functions', () => {
    describe('createTicketStorageKey', () => {
      it('should create valid storage key', () => {
        const result = createTicketStorageKey('user-123');
        expect(result).toBe('netra_ticket_user_123');
      });

      it('should sanitize special characters', () => {
        const result = createTicketStorageKey('user@example.com');
        expect(result).toBe('netra_ticket_user_example_com');
      });

      it('should throw for empty user ID', () => {
        expect(() => createTicketStorageKey('')).toThrow('User ID is required');
        expect(() => createTicketStorageKey('   ')).toThrow('User ID is required');
      });
    });

    describe('storeTicketSecurely', () => {
      const ticket: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date('2024-12-31T23:59:59Z'),
        permissions: ['websocket']
      };

      it('should store ticket successfully', () => {
        const result = storeTicketSecurely(ticket);

        expect(result).toBe(true);
        expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
          'netra_ticket_user_123',
          expect.stringContaining('test-123')
        );
      });

      it('should handle storage errors gracefully', () => {
        mockSessionStorage.setItem.mockImplementationOnce(() => {
          throw new Error('Storage full');
        });

        const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
        const result = storeTicketSecurely(ticket);

        expect(result).toBe(false);
        expect(consoleSpy).toHaveBeenCalledWith('Failed to store ticket securely:', expect.any(Error));
        consoleSpy.mockRestore();
      });
    });

    describe('retrieveStoredTicket', () => {
      it('should retrieve valid stored ticket', () => {
        const storedData = {
          ticket: {
            ticketId: 'test-123',
            userId: 'user-123',
            expires: new Date(Date.now() + 60000).toISOString(),
            permissions: ['websocket']
          },
          cachedAt: new Date().toISOString(),
          lastValidated: new Date().toISOString()
        };

        mockSessionStorage.getItem.mockReturnValue(JSON.stringify(storedData));

        const result = retrieveStoredTicket('user-123');

        expect(result).toEqual({
          ticketId: 'test-123',
          userId: 'user-123',
          expires: expect.any(Date),
          permissions: ['websocket']
        });
      });

      it('should return null for missing ticket', () => {
        mockSessionStorage.getItem.mockReturnValue(null);

        const result = retrieveStoredTicket('user-123');
        expect(result).toBeNull();
      });

      it('should clear expired ticket', () => {
        const expiredData = {
          ticket: {
            ticketId: 'test-123',
            userId: 'user-123',
            expires: new Date(Date.now() - 60000).toISOString(), // expired
            permissions: ['websocket']
          },
          cachedAt: new Date().toISOString(),
          lastValidated: new Date().toISOString()
        };

        mockSessionStorage.getItem.mockReturnValue(JSON.stringify(expiredData));

        const result = retrieveStoredTicket('user-123');

        expect(result).toBeNull();
        expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('netra_ticket_user_123');
      });

      it('should handle malformed data gracefully', () => {
        mockSessionStorage.getItem.mockReturnValue('invalid json');

        const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
        const result = retrieveStoredTicket('user-123');

        expect(result).toBeNull();
        expect(consoleSpy).toHaveBeenCalledWith('Failed to retrieve stored ticket:', expect.any(Error));
        consoleSpy.mockRestore();
      });
    });

    describe('clearStoredTicket', () => {
      it('should clear specific ticket', () => {
        const result = clearStoredTicket('user-123');

        expect(result).toBe(true);
        expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('netra_ticket_user_123');
      });

      it('should handle errors gracefully', () => {
        mockSessionStorage.removeItem.mockImplementationOnce(() => {
          throw new Error('Remove failed');
        });

        const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
        const result = clearStoredTicket('user-123');

        expect(result).toBe(false);
        expect(consoleSpy).toHaveBeenCalledWith('Failed to clear stored ticket:', expect.any(Error));
        consoleSpy.mockRestore();
      });
    });

    describe('clearAllStoredTickets', () => {
      it('should clear all ticket keys', () => {
        mockSessionStorage.length = 3;
        mockSessionStorage.key
          .mockReturnValueOnce('netra_ticket_user1')
          .mockReturnValueOnce('other_key')
          .mockReturnValueOnce('netra_ticket_user2');

        const result = clearAllStoredTickets();

        expect(result).toBe(true);
        expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('netra_ticket_user1');
        expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('netra_ticket_user2');
        expect(mockSessionStorage.removeItem).not.toHaveBeenCalledWith('other_key');
      });
    });
  });

  describe('error handling', () => {
    describe('sanitizeTicketError', () => {
      it('should sanitize ticket IDs', () => {
        const result = sanitizeTicketError('Error: ticketId=abc123 failed');
        expect(result).toBe('Error: ticketId=*** failed');
      });

      it('should sanitize user IDs', () => {
        const result = sanitizeTicketError('Failed for userId=user123');
        expect(result).toBe('Failed for userId=***');
      });

      it('should sanitize multiple sensitive fields', () => {
        const result = sanitizeTicketError('ticketId=abc userId=user token=xyz secret=key');
        expect(result).toBe('ticketId=*** userId=*** token=*** secret=***');
      });

      it('should handle Error objects', () => {
        const error = new Error('ticketId=sensitive123');
        const result = sanitizeTicketError(error);
        expect(result).toBe('ticketId=***');
      });

      it('should handle TicketAuthError objects', () => {
        const error = { code: 'TEST', message: 'ticketId=abc123', timestamp: new Date() };
        const result = sanitizeTicketError(error);
        expect(result).toBe('ticketId=***');
      });
    });

    describe('createTicketAuthError', () => {
      it('should create structured error', () => {
        const result = createTicketAuthError('TEST_CODE', 'Test message');

        expect(result).toEqual({
          code: 'TEST_CODE',
          message: 'Test message',
          timestamp: expect.any(Date)
        });
      });

      it('should sanitize error message', () => {
        const result = createTicketAuthError('TEST_CODE', 'Error with ticketId=abc123');

        expect(result.message).toBe('Error with ticketId=***');
      });

      it('should include original error if provided', () => {
        const originalError = new Error('Original error');
        const result = createTicketAuthError('TEST_CODE', 'Test message', originalError);

        expect(result).toEqual({
          code: 'TEST_CODE',
          message: 'Test message',
          timestamp: expect.any(Date),
          originalError: 'Original error'
        });
      });
    });
  });

  describe('WebSocket URL functions', () => {
    describe('validateWebSocketUrl', () => {
      it('should validate valid WebSocket URLs', () => {
        expect(validateWebSocketUrl('ws://localhost:8000')).toEqual({ isValid: true });
        expect(validateWebSocketUrl('wss://example.com/ws')).toEqual({ isValid: true });
      });

      it('should reject invalid protocols', () => {
        const result = validateWebSocketUrl('http://example.com');
        expect(result.isValid).toBe(false);
        expect(result.reason).toBe('WebSocket URL must use ws:// or wss:// protocol');
      });

      it('should reject empty URLs', () => {
        const result = validateWebSocketUrl('');
        expect(result.isValid).toBe(false);
        expect(result.reason).toBe('WebSocket URL is required');
      });

      it('should reject malformed URLs', () => {
        const result = validateWebSocketUrl('not-a-url');
        expect(result.isValid).toBe(false);
        expect(result.reason).toBe('Invalid WebSocket URL format');
      });
    });

    describe('buildTicketWebSocketUrl', () => {
      const ticket: TicketAuthData = {
        ticketId: 'test-123',
        userId: 'user-123',
        expires: new Date(),
        permissions: []
      };

      it('should build URL with ticket parameters', () => {
        const result = buildTicketWebSocketUrl('ws://localhost:8000/ws', ticket);
        expect(result).toBe('ws://localhost:8000/ws?ticket=test-123&userId=user-123');
      });

      it('should include additional parameters', () => {
        const result = buildTicketWebSocketUrl(
          'ws://localhost:8000/ws',
          ticket,
          { room: 'chat', protocol: 'v1' }
        );
        expect(result).toContain('ticket=test-123');
        expect(result).toContain('userId=user-123');
        expect(result).toContain('room=chat');
        expect(result).toContain('protocol=v1');
      });

      it('should throw for invalid base URL', () => {
        expect(() => buildTicketWebSocketUrl('http://invalid', ticket)).toThrow();
      });
    });

    describe('extractTicketFromWebSocketUrl', () => {
      it('should extract ticket information', () => {
        const url = 'ws://localhost:8000/ws?ticket=test-123&userId=user-123&other=value';
        const result = extractTicketFromWebSocketUrl(url);

        expect(result).toEqual({
          ticketId: 'test-123',
          userId: 'user-123'
        });
      });

      it('should handle missing parameters', () => {
        const url = 'ws://localhost:8000/ws?other=value';
        const result = extractTicketFromWebSocketUrl(url);

        expect(result).toEqual({});
      });

      it('should handle malformed URLs', () => {
        const result = extractTicketFromWebSocketUrl('not-a-url');
        expect(result).toEqual({});
      });
    });
  });
});