/**
 * Auth Service Client Logout Tests
 * =================================
 * Tests for auth service client logout with Authorization header
 * 
 * BVJ: Enterprise segment - ensures auth security and proper token handling
 */

// Mock fetch globally
global.fetch = jest.fn();

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  writable: true
});

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn()
  }
}));

// Mock unified API config
jest.mock('@/lib/unified-api-config', () => ({
  unifiedApiConfig: {
    environment: 'development',
    urls: {
      auth: 'http://localhost:8081',
      frontend: 'http://localhost:3000'
    },
    endpoints: {
      authConfig: 'http://localhost:8081/auth/config',
      authLogout: 'http://localhost:8081/auth/logout',
      authLogin: 'http://localhost:8081/auth/login',
      authCallback: 'http://localhost:8081/auth/callback',
      authToken: 'http://localhost:8081/auth/token',
      authMe: 'http://localhost:8081/auth/me',
      authSession: 'http://localhost:8081/auth/session'
    }
  },
  getOAuthRedirectUri: jest.fn()
}));

import { AuthServiceClient } from '@/lib/auth-service-client';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

describe('AuthServiceClient Logout', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  let authClient: AuthServiceClient;
  const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';

  beforeEach(() => {
    jest.clearAllMocks();
    authClient = new AuthServiceClient();
    (global.fetch as jest.Mock).mockClear();
    mockLocalStorage.getItem.mockClear();
  });

  afterEach(() => {
    jest.restoreAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('logout method', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should send Authorization header with token when available', async () => {
      // Setup: token exists in localStorage
      mockLocalStorage.getItem.mockReturnValue(mockToken);
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ success: true })
      });

      // Execute logout
      await authClient.logout();

      // Verify fetch was called with Authorization header
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8081/auth/logout',
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${mockToken}`
          })
        })
      );
    });

    it('should handle logout without token', async () => {
      // Setup: no token in localStorage
      mockLocalStorage.getItem.mockReturnValue(null);
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ success: true })
      });

      // Execute logout
      await authClient.logout();

      // Verify fetch was called without Authorization header
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8081/auth/logout',
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          })
        })
      );
      
      // Ensure Authorization header is not present
      const callArgs = (global.fetch as jest.Mock).mock.calls[0][1];
      expect(callArgs.headers).not.toHaveProperty('Authorization');
    });

    it('should throw error when logout fails', async () => {
      // Setup: token exists
      mockLocalStorage.getItem.mockReturnValue(mockToken);
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ error: 'Unauthorized' })
      });

      // Execute and expect error
      await expect(authClient.logout()).rejects.toThrow('Logout failed: 401');

      // Verify fetch was still called with proper headers
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8081/auth/logout',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': `Bearer ${mockToken}`
          })
        })
      );
    });

    it('should handle network errors', async () => {
      // Setup: network error
      mockLocalStorage.getItem.mockReturnValue(mockToken);
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      // Execute and expect error
      await expect(authClient.logout()).rejects.toThrow('Network error');
    });
  });
});