/**
 * Unit Tests for Auth Validation Helpers
 * 
 * CRITICAL BUG REPRODUCTION: Token exists but user is null
 * This test suite reproduces the exact frontend auth state mismatch bug:
 * - hasToken: true (token exists in localStorage)
 * - hasUser: false (user object is null in React state)
 * - context: 'auth_init_complete' (during auth initialization)
 * 
 * BVJ: All segments - Critical for chat functionality to work
 * 
 * @compliance CLAUDE.md - Real tests that expose real bugs
 * @compliance type_safety.xml - Strongly typed validation
 */

import {
  validateAuthState,
  validateToken,
  monitorAuthState,
  attemptAuthRecovery,
  attemptEnhancedAuthRecovery,
  createAtomicAuthUpdate,
  applyAtomicAuthUpdate,
  debugAuthState,
  AuthValidation
} from '@/lib/auth-validation';
import { User } from '@/types';
import { logger } from '@/lib/logger';

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    error: jest.fn(),
    warn: jest.fn(),
    info: jest.fn(),
    debug: jest.fn(),
  }
}));

// Mock localStorage
const mockLocalStorage = {
  removeItem: jest.fn(),
  getItem: jest.fn(),
  setItem: jest.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  writable: true
});

describe('Auth Validation Helpers - CRITICAL BUG REPRODUCTION', () => {
  const mockUser: User = {
    id: 'test-user-123',
    email: 'test@example.com',
    full_name: 'Test User',
    exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour from now
  };

  // Valid JWT token for testing (mock)
  const validToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6InRlc3QtdXNlci0xMjMiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJmdWxsX25hbWUiOiJUZXN0IFVzZXIiLCJleHAiOjE5OTk5OTk5OTksInN1YiI6InRlc3QtdXNlci0xMjMifQ.FakeSignature';
  
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.removeItem.mockClear();
    mockLocalStorage.getItem.mockClear();
    mockLocalStorage.setItem.mockClear();
  });

  describe('CRITICAL BUG: Token without User State', () => {
    test('SHOULD FAIL: validateAuthState detects token without user (the exact bug)', () => {
      // REPRODUCE THE EXACT BUG SCENARIO:
      // Token exists in localStorage but user is null in React state
      const validation = validateAuthState(
        validToken, // hasToken: true
        null,       // hasUser: false - THIS IS THE BUG!
        true        // initialized: true (auth_init_complete)
      );

      // This should detect the critical bug
      expect(validation.isValid).toBe(false);
      expect(validation.hasToken).toBe(true);
      expect(validation.hasUser).toBe(false);
      expect(validation.errors).toContain('CRITICAL: Token exists but user not set - chat will fail');
      
      // Verify logger was called to flag this critical issue
      expect(logger.error).toHaveBeenCalledWith(
        '[AUTH VALIDATION] Token without user detected',
        expect.objectContaining({
          component: 'auth-validation',
          action: 'state_mismatch',
          hasToken: true,
          hasUser: false
        })
      );
    });

    test('SHOULD FAIL: monitorAuthState alerts on critical bug pattern', () => {
      // Monitor the exact bug scenario
      monitorAuthState(
        validToken, // token exists
        null,       // user is null - CRITICAL BUG
        true,       // initialized
        'auth_init_complete'
      );

      // Should trigger critical bug detection
      expect(logger.error).toHaveBeenCalledWith(
        '[AUTH MONITOR] CRITICAL BUG DETECTED: Token without user!',
        expect.objectContaining({
          component: 'auth-validation',
          action: 'critical_bug_detected',
          context: 'auth_init_complete',
          description: 'This is the exact bug that broke chat initialization'
        })
      );
    });

    test('SHOULD PASS: attemptAuthRecovery correctly recovers user from valid token', async () => {
      const mockSetUser = jest.fn();
      const mockSetToken = jest.fn();

      // Now with the fix, attemptAuthRecovery should work correctly with proper user parameter
      const recovered = await attemptAuthRecovery(
        validToken, // token exists
        null,       // user is initially null (the bug state)
        mockSetUser, 
        mockSetToken
      );
      
      // Should successfully recover user from token
      expect(recovered).toBe(true);
      expect(mockSetUser).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'test-user-123',
          email: 'test@example.com'
        })
      );
      
      // Verify recovery logging includes both token and user info
      expect(logger.info).toHaveBeenCalledWith(
        '[AUTH RECOVERY] Attempting auth state recovery',
        expect.objectContaining({
          component: 'auth-validation',
          action: 'recovery_start',
          hasToken: true,
          hasUser: false
        })
      );
      
      expect(logger.info).toHaveBeenCalledWith(
        '[AUTH RECOVERY] Successfully recovered user from token',
        expect.objectContaining({
          component: 'auth-validation',
          action: 'recovery_success',
          userId: 'test-user-123'
        })
      );
    });
  });

  describe('Token Validation Edge Cases', () => {
    test('SHOULD FAIL: validateToken handles invalid JWT format', () => {
      const invalidToken = 'invalid.token';
      
      const validation = validateToken(invalidToken);
      
      expect(validation.isValid).toBe(false);
      expect(validation.errors).toContain('Invalid token format: expected 3 parts, got 2');
    });

    test('SHOULD FAIL: validateToken detects expired tokens', () => {
      // Create expired token (exp in past)
      const expiredToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6InRlc3QtdXNlci0xMjMiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJmdWxsX25hbWUiOiJUZXN0IFVzZXIiLCJleHAiOjE2MDk0NTkyMDAsInN1YiI6InRlc3QtdXNlci0xMjMifQ.ExpiredSignature';
      
      const validation = validateToken(expiredToken);
      
      expect(validation.isValid).toBe(false);
      expect(validation.isExpired).toBe(true);
      expect(validation.errors.some(error => error.includes('Token expired at'))).toBe(true);
    });
  });

  describe('Atomic Auth Updates - Race Condition Prevention', () => {
    test('SHOULD PASS: createAtomicAuthUpdate creates proper update object', () => {
      const atomicUpdate = createAtomicAuthUpdate(validToken, mockUser);
      
      expect(atomicUpdate.token).toBe(validToken);
      expect(atomicUpdate.user).toBe(mockUser);
      expect(atomicUpdate.timestamp).toBeGreaterThan(Date.now() - 1000);
      expect(typeof atomicUpdate.timestamp).toBe('number');
    });

    test('SHOULD PASS: applyAtomicAuthUpdate applies valid updates atomically', () => {
      const mockSetToken = jest.fn();
      const mockSetUser = jest.fn();
      const mockSyncStore = jest.fn();
      
      const atomicUpdate = createAtomicAuthUpdate(validToken, mockUser);
      const success = applyAtomicAuthUpdate(
        atomicUpdate, 
        mockSetToken, 
        mockSetUser, 
        mockSyncStore
      );
      
      expect(success).toBe(true);
      expect(mockSetToken).toHaveBeenCalledWith(validToken);
      expect(mockSetUser).toHaveBeenCalledWith(mockUser);
      expect(mockSyncStore).toHaveBeenCalledWith(mockUser, validToken);
      
      expect(logger.info).toHaveBeenCalledWith(
        '[ATOMIC UPDATE] Auth state updated atomically',
        expect.objectContaining({
          component: 'auth-validation',
          action: 'atomic_update_success',
          hasToken: true,
          hasUser: true
        })
      );
    });

    test('SHOULD PASS: applyAtomicAuthUpdate handles logout state atomically', () => {
      const mockSetToken = jest.fn();
      const mockSetUser = jest.fn();
      const mockSyncStore = jest.fn();
      
      const atomicUpdate = createAtomicAuthUpdate(null, null);
      const success = applyAtomicAuthUpdate(
        atomicUpdate, 
        mockSetToken, 
        mockSetUser, 
        mockSyncStore
      );
      
      expect(success).toBe(true);
      expect(mockSetToken).toHaveBeenCalledWith(null);
      expect(mockSetUser).toHaveBeenCalledWith(null);
      expect(mockSyncStore).toHaveBeenCalledWith(null, null);
    });

    test('SHOULD PASS: attemptEnhancedAuthRecovery uses atomic updates', async () => {
      const mockSetUser = jest.fn();
      const mockSetToken = jest.fn();
      const mockSyncStore = jest.fn();

      const recovered = await attemptEnhancedAuthRecovery(
        validToken, // token exists
        null,       // user is null
        mockSetUser,
        mockSetToken,
        mockSyncStore
      );

      expect(recovered).toBe(true);
      expect(mockSetUser).toHaveBeenCalled();
      
      expect(logger.info).toHaveBeenCalledWith(
        '[ENHANCED RECOVERY] Starting enhanced auth recovery',
        expect.objectContaining({
          component: 'auth-validation',
          action: 'enhanced_recovery_start',
          hasToken: true,
          hasUser: false
        })
      );
    });
  });

  describe('Valid Auth State Scenarios', () => {
    test('SHOULD PASS: validateAuthState accepts valid token and user', () => {
      const validation = validateAuthState(
        validToken,
        mockUser,
        true
      );

      expect(validation.isValid).toBe(true);
      expect(validation.hasToken).toBe(true);
      expect(validation.hasUser).toBe(true);
      expect(validation.userMatchesToken).toBe(true);
      expect(validation.errors).toHaveLength(0);
    });

    test('SHOULD PASS: validateAuthState accepts logged out state', () => {
      const validation = validateAuthState(
        null, // no token
        null, // no user  
        true  // initialized
      );

      expect(validation.isValid).toBe(true);
      expect(validation.hasToken).toBe(false);
      expect(validation.hasUser).toBe(false);
      expect(validation.errors).toHaveLength(0);
    });
  });

  describe('Debug Helper', () => {
    test('debugAuthState logs comprehensive auth state information', () => {
      const consoleSpy = jest.spyOn(console, 'group').mockImplementation();
      const consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      const consoleEndSpy = jest.spyOn(console, 'groupEnd').mockImplementation();

      debugAuthState(validToken, null, true, 'test_debug');

      expect(consoleSpy).toHaveBeenCalledWith('🔐 Auth State Debug (test_debug)');
      expect(consoleLogSpy).toHaveBeenCalledWith('Has Token:', true);
      expect(consoleLogSpy).toHaveBeenCalledWith('Has User:', false);
      expect(consoleLogSpy).toHaveBeenCalledWith('Valid:', false);
      expect(consoleEndSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
      consoleLogSpy.mockRestore();
      consoleErrorSpy.mockRestore();
      consoleEndSpy.mockRestore();
    });
  });
});
