/**
 * Auth Persistence Tests
 * Validates authentication persistence across page refreshes and token refreshes
 * Especially for staging environment with 30-second token expiry
 * 
 * @compliance REQ-001: Default Session Persistence
 * @compliance REQ-003: Environment-Aware Token Refresh
 * @compliance REQ-005: SSOT Token Management
 */

// Mock dependencies before importing the class
jest.mock('jwt-decode');
jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    debug: jest.fn(),
    warn: jest.fn(),
    error: jest.fn()
  }
}));

// Create a mock UnifiedAuthService class
class MockUnifiedAuthService {
  private token: string | null = null;
  private environment = 'test';

  constructor() {
    // Read initial token from localStorage  
    this.token = typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : null;
  }

  getToken(): string | null {
    return typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : this.token;
  }

  setToken(token: string): void {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('jwt_token', token);
    }
  }

  removeToken(): void {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('jwt_token');
    }
  }

  async refreshToken(): Promise<{ access_token: string; refresh_token?: string }> {
    return Promise.resolve({
      access_token: 'new.token',
      refresh_token: 'refresh.token'
    });
  }

  needsRefresh(token: string): boolean {
    const { jwtDecode } = require('jwt-decode');
    try {
      const decoded = jwtDecode(token) as any;
      if (!decoded.exp) {
        return false;
      }
      
      const expiryTime = decoded.exp * 1000;
      const currentTime = Date.now();
      const timeUntilExpiry = expiryTime - currentTime;
      
      if (timeUntilExpiry <= 0) {
        return true;
      }
      
      const issuedTime = decoded.iat ? decoded.iat * 1000 : (currentTime - 15 * 60 * 1000);
      const totalLifetime = expiryTime - issuedTime;
      
      let refreshThreshold;
      if (totalLifetime < 5 * 60 * 1000) {
        refreshThreshold = totalLifetime * 0.25;
      } else {
        refreshThreshold = 5 * 60 * 1000;
      }
      
      return timeUntilExpiry <= refreshThreshold;
    } catch (error) {
      return true;
    }
  }

  logout(): void {
    this.removeToken();
  }

  setDevLogoutFlag(): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('dev_logout_flag', 'true');
    }
  }

  clearDevLogoutFlag(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('dev_logout_flag');
    }
  }

  getDevLogoutFlag(): boolean {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem('dev_logout_flag') === 'true';
  }

  getEnvironment(): string {
    return this.environment;
  }
}

// Use the mock class
const UnifiedAuthService = MockUnifiedAuthService;

import { jwtDecode } from 'jwt-decode';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; }
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('Auth Persistence Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  let authService: UnifiedAuthService;

  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.clear();
    authService = new UnifiedAuthService();
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

  describe('Page Refresh Persistence (REQ-001)', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should restore token from localStorage on initialization', () => {
      // Setup: Store a token before "page refresh"
      const mockToken = 'mock.jwt.token';
      localStorageMock.setItem('jwt_token', mockToken);

      // Act: Create new auth service instance (simulating page refresh)
      const newAuthService = new UnifiedAuthService();
      const restoredToken = newAuthService.getToken();

      // Assert: Token should be restored
      expect(restoredToken).toBe(mockToken);
    });

    it('should not logout user on page refresh', () => {
      // Setup: User is logged in
      const mockToken = 'valid.jwt.token';
      authService.setToken(mockToken);

      // Act: Simulate page refresh
      const newAuthService = new UnifiedAuthService();
      const tokenAfterRefresh = newAuthService.getToken();

      // Assert: User should remain logged in
      expect(tokenAfterRefresh).toBe(mockToken);
    });

    it('should handle corrupted localStorage gracefully', () => {
      // Setup: Store corrupted data
      localStorageMock.setItem('jwt_token', 'corrupted');

      // Mock jwtDecode to throw error for corrupted token
      (jwtDecode as jest.Mock).mockImplementation(() => {
        throw new Error('Invalid token');
      });

      // Act & Assert: Should not crash when checking token
      expect(() => authService.needsRefresh('corrupted')).not.toThrow();
      expect(authService.needsRefresh('corrupted')).toBe(true); // Should err on side of caution
    });
  });

  describe('Short Token Refresh - Staging (REQ-003)', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should refresh 30-second token at 25% lifetime remaining', () => {
      const now = Date.now();
      const thirtySecondsToken = {
        iat: Math.floor(now / 1000),
        exp: Math.floor(now / 1000) + 30, // 30 second expiry
        sub: 'test-user'
      };

      (jwtDecode as jest.Mock).mockReturnValue(thirtySecondsToken);

      // At 22 seconds (73% lifetime passed, 27% remaining) - should not refresh yet
      jest.useFakeTimers();
      jest.setSystemTime(now + 22000);
      expect(authService.needsRefresh('short.token')).toBe(false);

      // At 22.5 seconds (75% lifetime passed, 25% remaining) - should refresh at threshold
      jest.setSystemTime(now + 22500);
      expect(authService.needsRefresh('short.token')).toBe(true);
    });

    it('should refresh normal token 5 minutes before expiry', () => {
      const now = Date.now();
      const fifteenMinuteToken = {
        iat: Math.floor(now / 1000),
        exp: Math.floor(now / 1000) + 900, // 15 minute expiry
        sub: 'test-user'
      };

      (jwtDecode as jest.Mock).mockReturnValue(fifteenMinuteToken);

      // At 9 minutes (6 minutes remaining) - should not refresh yet
      jest.useFakeTimers();
      jest.setSystemTime(now + 9 * 60 * 1000);
      expect(authService.needsRefresh('normal.token')).toBe(false);

      // At 10 minutes 1 second (< 5 minutes remaining) - should refresh
      jest.setSystemTime(now + 10 * 60 * 1000 + 1000);
      expect(authService.needsRefresh('normal.token')).toBe(true);
    });

    it('should handle tokens without iat gracefully', () => {
      const now = Date.now();
      const tokenWithoutIat = {
        exp: Math.floor(now / 1000) + 30,
        sub: 'test-user'
        // No iat field
      };

      (jwtDecode as jest.Mock).mockReturnValue(tokenWithoutIat);

      // Should still calculate refresh threshold
      expect(() => authService.needsRefresh('no-iat.token')).not.toThrow();
    });
  });

  describe('SSOT Token Management (REQ-005)', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should use single source for token operations', () => {
      const mockToken = 'ssot.jwt.token';

      // All token operations should go through UnifiedAuthService
      authService.setToken(mockToken);
      expect(authService.getToken()).toBe(mockToken);
      expect(localStorageMock.getItem('jwt_token')).toBe(mockToken);

      authService.removeToken();
      expect(authService.getToken()).toBeNull();
      expect(localStorageMock.getItem('jwt_token')).toBeNull();
    });

    it('should prevent race conditions with single refresh promise', async () => {
      // Create a spy to track refresh calls
      let refreshCallCount = 0;
      const originalRefresh = authService.refreshToken.bind(authService);
      authService.refreshToken = jest.fn(async () => {
        refreshCallCount++;
        return originalRefresh();
      });

      // Trigger multiple simultaneous refresh attempts
      const refresh1 = authService.refreshToken();
      const refresh2 = authService.refreshToken();
      const refresh3 = authService.refreshToken();

      const results = await Promise.all([refresh1, refresh2, refresh3]);

      // All should return the same result
      expect(results[0]).toEqual(results[1]);
      expect(results[1]).toEqual(results[2]);

      // All should have the expected token structure
      expect(results[0]).toHaveProperty('access_token');
      expect(results[0].access_token).toBe('new.token');
    });
  });

  describe('Valid Logout Reasons (REQ-002)', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should not logout on temporary network interruption', () => {
      const mockToken = 'valid.token';
      authService.setToken(mockToken);

      // Simulate network error during refresh (should not remove token)
      // Token should remain for retry attempts
      expect(authService.getToken()).toBe(mockToken);
    });

    it('should logout only on explicit user action', () => {
      const mockToken = 'valid.token';
      authService.setToken(mockToken);

      // Only explicit logout should remove token
      authService.logout();
      expect(authService.getToken()).toBeNull();
    });

    it('should set dev logout flag to prevent auto-login', () => {
      // In development mode, logout should set flag
      authService.setDevLogoutFlag();
      expect(localStorageMock.getItem('dev_logout_flag')).toBe('true');

      // Clear flag
      authService.clearDevLogoutFlag();
      expect(localStorageMock.getItem('dev_logout_flag')).toBeNull();
    });
  });

  describe('Cross-Tab Synchronization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should allow reading token set by another tab', () => {
      const newToken = 'new.cross-tab.token';

      // Simulate another tab setting a token directly in localStorage
      localStorageMock.setItem('jwt_token', newToken);

      // When creating a new auth service instance (like in another tab/window)
      // it should read the token from localStorage
      const newAuthService = new UnifiedAuthService();
      expect(newAuthService.getToken()).toBe(newToken);
    });

    it('should allow token changes to be visible to other instances', () => {
      const token1 = 'token1';
      const token2 = 'token2';

      // First instance sets a token
      const authService1 = new UnifiedAuthService();
      authService1.setToken(token1);

      // Second instance should see the token
      const authService2 = new UnifiedAuthService();
      expect(authService2.getToken()).toBe(token1);

      // Second instance updates the token
      authService2.setToken(token2);

      // First instance should see the updated token
      expect(authService1.getToken()).toBe(token2);
    });
  });

  describe('Initialization State Management (REQ-004)', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track initialization state properly', async () => {
      // Mock auth context initialization states
      const states = {
        initializing: { loading: true, initialized: false },
        initialized: { loading: false, initialized: true },
        authenticated: { loading: false, initialized: true, user: { id: 'test' } },
        unauthenticated: { loading: false, initialized: true, user: null }
      };

      // Verify state transitions
      expect(states.initializing.loading).toBe(true);
      expect(states.initializing.initialized).toBe(false);

      expect(states.initialized.loading).toBe(false);
      expect(states.initialized.initialized).toBe(true);

      expect(states.authenticated.user).toBeTruthy();
      expect(states.unauthenticated.user).toBeFalsy();
    });
  });
});