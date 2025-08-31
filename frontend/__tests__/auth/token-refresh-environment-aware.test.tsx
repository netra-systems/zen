/**
 * @fileoverview Tests for environment-aware token refresh behavior
 * 
 * Tests the fixes for critical authentication persistence issues:
 * 1. Dynamic refresh thresholds for short vs long-lived tokens  
 * 2. Environment-aware refresh scheduling
 * 3. Proper initialization tracking to prevent AuthGuard race conditions
 * 
 * @environment development,staging
 */

import { unifiedAuthService } from '@/auth/unified-auth-service';
import { jwtDecode } from 'jwt-decode';

// Mock jwt-decode
jest.mock('jwt-decode');
const mockJwtDecode = jwtDecode as jest.MockedFunction<typeof jwtDecode>;

// Mock logger
const mockLogger = {
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
};

jest.mock('@/lib/logger', () => ({
  logger: mockLogger,
}));

describe('Token Refresh Environment-Aware Behavior', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let service: typeof unifiedAuthService;
  
  beforeEach(() => {
    jest.clearAllMocks();
    service = unifiedAuthService;
  });

  describe('needsRefresh - Short-lived tokens (30 seconds)', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should refresh at 25% of lifetime for 30-second token', () => {
      const now = Date.now();
      const iat = Math.floor(now / 1000) - 23; // issued 23 seconds ago
      const exp = Math.floor(now / 1000) + 7;  // expires in 7 seconds
      
      mockJwtDecode.mockReturnValue({
        exp,
        iat,
        sub: 'test-user',
      });

      const result = service.needsRefresh('fake-token');

      // For 30s token (total lifetime), 25% = 7.5s
      // With 7 seconds remaining, should need refresh
      expect(result).toBe(true);
      expect(mockLogger.debug).toHaveBeenCalledWith(
        'Token refresh check',
        expect.objectContaining({
          needsRefresh: true,
          timeUntilExpiry: 7,
          totalLifetime: 30,
          refreshThreshold: 7, // 25% of 30s = 7.5s, rounded down
        })
      );
    });

    test('should NOT refresh at 50% of lifetime for 30-second token', () => {
      const now = Date.now();
      const iat = Math.floor(now / 1000) - 15; // issued 15 seconds ago
      const exp = Math.floor(now / 1000) + 15; // expires in 15 seconds
      
      mockJwtDecode.mockReturnValue({
        exp,
        iat,
        sub: 'test-user',
      });

      const result = service.needsRefresh('fake-token');

      // For 30s token, should not refresh at 50% lifetime (15s remaining)
      // Refresh threshold is 25% = 7.5s
      expect(result).toBe(false);
      expect(mockLogger.debug).toHaveBeenCalledWith(
        'Token refresh check',
        expect.objectContaining({
          needsRefresh: false,
          timeUntilExpiry: 15,
          totalLifetime: 30,
          refreshThreshold: 7, // 25% of 30s
        })
      );
    });
  });

  describe('needsRefresh - Normal tokens (15+ minutes)', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should refresh 5 minutes before expiry for 15-minute token', () => {
      const now = Date.now();
      const iat = Math.floor(now / 1000) - 10 * 60; // issued 10 minutes ago
      const exp = Math.floor(now / 1000) + 4 * 60;  // expires in 4 minutes
      
      mockJwtDecode.mockReturnValue({
        exp,
        iat,
        sub: 'test-user',
      });

      const result = service.needsRefresh('fake-token');

      // For 15-minute token, should refresh when < 5 minutes remain
      expect(result).toBe(true);
      expect(mockLogger.debug).toHaveBeenCalledWith(
        'Token refresh check',
        expect.objectContaining({
          needsRefresh: true,
          timeUntilExpiry: 240, // 4 minutes in seconds
          totalLifetime: 900,   // 15 minutes in seconds
          refreshThreshold: 300, // 5 minutes in seconds
        })
      );
    });

    test('should NOT refresh when 6 minutes remain for 15-minute token', () => {
      const now = Date.now();
      const iat = Math.floor(now / 1000) - 9 * 60; // issued 9 minutes ago
      const exp = Math.floor(now / 1000) + 6 * 60; // expires in 6 minutes
      
      mockJwtDecode.mockReturnValue({
        exp,
        iat,
        sub: 'test-user',
      });

      const result = service.needsRefresh('fake-token');

      expect(result).toBe(false);
      expect(mockLogger.debug).toHaveBeenCalledWith(
        'Token refresh check',
        expect.objectContaining({
          needsRefresh: false,
          timeUntilExpiry: 360,  // 6 minutes in seconds
          totalLifetime: 900,    // 15 minutes in seconds
          refreshThreshold: 300, // 5 minutes in seconds
        })
      );
    });
  });

  describe('needsRefresh - Edge cases', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should handle missing iat by estimating token lifetime', () => {
      const now = Date.now();
      const exp = Math.floor(now / 1000) + 4 * 60; // expires in 4 minutes
      
      mockJwtDecode.mockReturnValue({
        exp,
        // No iat provided
        sub: 'test-user',
      });

      const result = service.needsRefresh('fake-token');

      // Should default to 15-minute token assumption and use 5-minute threshold
      expect(result).toBe(true);
      expect(mockLogger.debug).toHaveBeenCalledWith(
        'Token refresh check',
        expect.objectContaining({
          needsRefresh: true,
          timeUntilExpiry: 240,
          // totalLifetime should be estimated (current time - 15 minutes)
          refreshThreshold: 300,
        })
      );
    });

    test('should return true for malformed token', () => {
      mockJwtDecode.mockImplementation(() => {
        throw new Error('Invalid token');
      });

      const result = service.needsRefresh('invalid-token');

      expect(result).toBe(true);
      expect(mockLogger.error).toHaveBeenCalledWith(
        'Error checking token expiry',
        expect.any(Error)
      );
    });

    test('should return false for token without expiry', () => {
      mockJwtDecode.mockReturnValue({
        // No exp field
        sub: 'test-user',
      });

      const result = service.needsRefresh('fake-token');

      expect(result).toBe(false);
    });
  });

  describe('Token lifetime classification', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('should classify 2-minute token as short-lived', () => {
      const now = Date.now();
      const iat = Math.floor(now / 1000) - 30;  // issued 30 seconds ago
      const exp = Math.floor(now / 1000) + 90;  // expires in 90 seconds (2 minutes total)
      
      mockJwtDecode.mockReturnValue({ exp, iat, sub: 'test-user' });

      service.needsRefresh('fake-token');

      expect(mockLogger.debug).toHaveBeenCalledWith(
        'Token refresh check',
        expect.objectContaining({
          totalLifetime: 120, // 2 minutes
          refreshThreshold: 30, // 25% of 120s = 30s
        })
      );
    });

    test('should classify 5-minute token as normal (boundary case)', () => {
      const now = Date.now();
      const iat = Math.floor(now / 1000) - 60;   // issued 1 minute ago
      const exp = Math.floor(now / 1000) + 240;  // expires in 4 minutes (5 minutes total)
      
      mockJwtDecode.mockReturnValue({ exp, iat, sub: 'test-user' });

      service.needsRefresh('fake-token');

      expect(mockLogger.debug).toHaveBeenCalledWith(
        'Token refresh check',
        expect.objectContaining({
          totalLifetime: 300, // 5 minutes
          refreshThreshold: 300, // Should use 5-minute threshold for boundary case
        })
      );
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});