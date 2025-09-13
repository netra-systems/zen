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

  describe('Uncovered Lines Coverage - Error Recovery & Edge Cases', () => {
    describe('Lines 63-65: Auth Context Not Initialized Coverage', () => {
      test('SHOULD PASS: validateAuthState handles uninitialized context with warning', () => {
        // Test the specific uncovered lines 63-65
        const validation = validateAuthState(
          validToken,  // token exists
          mockUser,    // user exists
          false        // initialized: false - triggers lines 63-65
        );

        // Should return early with warning (lines 63-65)
        expect(validation.isValid).toBe(false);
        expect(validation.hasToken).toBe(true);
        expect(validation.hasUser).toBe(true);
        expect(validation.warnings).toContain('Auth context not yet initialized');
        expect(validation.errors).toHaveLength(0); // No errors, just warning
      });

      test('SHOULD PASS: validateAuthState handles uninitialized context with no token/user', () => {
        const validation = validateAuthState(
          null,   // no token
          null,   // no user
          false   // initialized: false - triggers lines 63-65
        );

        expect(validation.isValid).toBe(false);
        expect(validation.warnings).toContain('Auth context not yet initialized');
      });
    });

    describe('Lines 87-89: User Without Token Edge Cases', () => {
      test('SHOULD FAIL: validateAuthState detects user without token (invalid state)', () => {
        // Test the specific uncovered lines 87-89
        const validation = validateAuthState(
          null,      // no token - triggers lines 87-89
          mockUser,  // user exists
          true       // initialized: true
        );

        // Should detect invalid state (lines 87-89)
        expect(validation.isValid).toBe(false);
        expect(validation.hasToken).toBe(false);
        expect(validation.hasUser).toBe(true);
        expect(validation.errors).toContain('User exists but no token - authentication inconsistent');
      });

      test('SHOULD PASS: attemptEnhancedAuthRecovery handles user without token pattern', async () => {
        const mockSetUser = jest.fn();
        const mockSetToken = jest.fn();
        const mockSyncStore = jest.fn();

        // Test Pattern 2: User exists but no token (lines referenced in enhanced recovery)
        const recovered = await attemptEnhancedAuthRecovery(
          null,        // no token
          mockUser,    // user exists - invalid state
          mockSetUser,
          mockSetToken,
          mockSyncStore
        );

        // Should clear both user and token atomically
        expect(recovered).toBe(true);
        expect(mockSetToken).toHaveBeenCalledWith(null);
        expect(mockSetUser).toHaveBeenCalledWith(null);
        expect(mockSyncStore).toHaveBeenCalledWith(null, null);
      });
    });

    describe('Lines 325-332: Critical Atomic Update Validation', () => {
      test('SHOULD FAIL: applyAtomicAuthUpdate rejects invalid state with errors', () => {
        const mockSetToken = jest.fn();
        const mockSetUser = jest.fn();
        const mockSyncStore = jest.fn();

        // Create invalid atomic update (token without user)
        const invalidUpdate = createAtomicAuthUpdate(validToken, null);
        
        // This should trigger validation failure in lines 325-332
        const success = applyAtomicAuthUpdate(
          invalidUpdate,
          mockSetToken,
          mockSetUser,
          mockSyncStore
        );

        expect(success).toBe(false); // Update rejected
        expect(mockSetToken).not.toHaveBeenCalled(); // No state changes
        expect(mockSetUser).not.toHaveBeenCalled();
        expect(mockSyncStore).not.toHaveBeenCalled();

        // Should log the validation error (lines 325-332)
        expect(logger.error).toHaveBeenCalledWith(
          '[ATOMIC UPDATE] Invalid auth state in atomic update',
          expect.objectContaining({
            component: 'auth-validation',
            action: 'atomic_update_invalid',
            errors: expect.arrayContaining(['CRITICAL: Token exists but user not set - chat will fail'])
          })
        );
      });

      test('SHOULD FAIL: applyAtomicAuthUpdate handles update with validation warnings', () => {
        const mockSetToken = jest.fn();
        const mockSetUser = jest.fn();

        // Create user with different email than token to trigger warnings
        const userWithDifferentEmail = {
          ...mockUser,
          email: 'different@example.com'
        };

        const updateWithWarnings = createAtomicAuthUpdate(validToken, userWithDifferentEmail);
        
        const success = applyAtomicAuthUpdate(
          updateWithWarnings,
          mockSetToken,
          mockSetUser
        );

        // Should still succeed despite warnings (only errors block updates)
        expect(success).toBe(true);
        expect(mockSetToken).toHaveBeenCalledWith(validToken);
        expect(mockSetUser).toHaveBeenCalledWith(userWithDifferentEmail);
      });

      test('SHOULD FAIL: applyAtomicAuthUpdate handles exception during validation', () => {
        const mockSetToken = jest.fn().mockImplementation(() => {
          throw new Error('Setter failed');
        });
        const mockSetUser = jest.fn();

        const validUpdate = createAtomicAuthUpdate(validToken, mockUser);
        
        const success = applyAtomicAuthUpdate(
          validUpdate,
          mockSetToken,
          mockSetUser
        );

        expect(success).toBe(false);
        expect(logger.error).toHaveBeenCalledWith(
          '[ATOMIC UPDATE] Failed to apply atomic auth update',
          expect.any(Error)
        );
      });
    });
  });

  describe('Enhanced Token Validation Edge Cases', () => {
    test('SHOULD FAIL: validateToken handles malformed JWT payload', () => {
      // Token with invalid base64 in payload
      const malformedToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.InvalidBase64Payload.FakeSignature';
      
      const validation = validateToken(malformedToken);
      
      expect(validation.isValid).toBe(false);
      expect(validation.errors.some(error => error.includes('Token decode error'))).toBe(true);
    });

    test('SHOULD FAIL: validateToken detects missing required fields', () => {
      // Token without email field
      const tokenWithoutEmail = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6InRlc3QtdXNlci0xMjMiLCJmdWxsX25hbWUiOiJUZXN0IFVzZXIiLCJleHAiOjE5OTk5OTk5OTksInN1YiI6InRlc3QtdXNlci0xMjMifQ.FakeSignature';
      
      const validation = validateToken(tokenWithoutEmail);
      
      expect(validation.isValid).toBe(false);
      expect(validation.hasRequiredFields).toBe(false);
      expect(validation.errors).toContain('Missing required fields: email');
    });

    test('SHOULD FAIL: validateToken detects future-issued tokens', () => {
      // Token issued in future (iat > now + 60s)
      const futureIssuedAt = Math.floor(Date.now() / 1000) + 3600; // 1 hour in future
      // Create a properly encoded token with future iat
      const payload = btoa(JSON.stringify({
        id: 'test-user-123',
        email: 'test@example.com',
        full_name: 'Test User',
        exp: 1999999999,
        iat: futureIssuedAt,
        sub: 'test-user-123'
      }));
      const futureToken = `eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.${payload}.FutureSignature`;
      
      const validation = validateToken(futureToken);
      
      expect(validation.isValid).toBe(false);
      expect(validation.issuedInFuture).toBe(true);
      expect(validation.errors.some(error => error.includes('Token issued in future'))).toBe(true);
    });

    test('SHOULD FAIL: validateToken handles empty token', () => {
      const validation = validateToken('');
      
      expect(validation.isValid).toBe(false);
      expect(validation.errors).toContain('Token is empty');
    });

    test('SHOULD FAIL: validateToken handles null token', () => {
      // @ts-expect-error Testing null input
      const validation = validateToken(null);
      
      expect(validation.isValid).toBe(false);
      expect(validation.errors).toContain('Token is empty');
    });
  });

  describe('Auth State Validation Complex Scenarios', () => {
    test('SHOULD FAIL: validateAuthState detects ID mismatch between token and user', () => {
      const userWithDifferentId = {
        ...mockUser,
        id: 'different-user-id'
      };

      const validation = validateAuthState(
        validToken,
        userWithDifferentId,
        true
      );

      expect(validation.isValid).toBe(false);
      expect(validation.userMatchesToken).toBe(false);
      expect(validation.errors.some(error => error.includes('User ID mismatch'))).toBe(true);
    });

    test('SHOULD FAIL: validateAuthState handles email mismatch with warning', () => {
      const userWithDifferentEmail = {
        ...mockUser,
        email: 'different@example.com'
      };

      const validation = validateAuthState(
        validToken,
        userWithDifferentEmail,
        true
      );

      // Should be invalid when email mismatches because userMatchesToken stays false
      // This is actually correct behavior - email mismatch should be treated as invalid
      expect(validation.isValid).toBe(false);
      expect(validation.userMatchesToken).toBe(false);
      expect(validation.warnings.some(warning => warning.includes('Email mismatch'))).toBe(true);
      expect(validation.errors).toHaveLength(0); // No errors, just warning, but invalid due to userMatchesToken=false
    });

    test('SHOULD FAIL: validateAuthState handles token validation failure', () => {
      const invalidToken = 'invalid.token.format';

      const validation = validateAuthState(
        invalidToken,
        mockUser,
        true
      );

      expect(validation.isValid).toBe(false);
      // Check for any token-related error (could be format or decode error)
      expect(validation.errors.length).toBeGreaterThan(0);
      expect(validation.errors.some(error => 
        error.includes('Invalid token format') || 
        error.includes('Token validation error') ||
        error.includes('Token decode error')
      )).toBe(true);
    });
  });

  describe('Recovery Functions Edge Cases', () => {
    test('SHOULD FAIL: attemptAuthRecovery handles invalid token gracefully', async () => {
      const mockSetUser = jest.fn();
      const mockSetToken = jest.fn();
      const invalidToken = 'invalid.token.format';

      const recovered = await attemptAuthRecovery(
        invalidToken,
        null,
        mockSetUser,
        mockSetToken
      );

      expect(recovered).toBe(true); // Should clear invalid token
      expect(mockSetToken).toHaveBeenCalledWith(null);
      expect(mockSetUser).toHaveBeenCalledWith(null);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('jwt_token');
    });

    test('SHOULD PASS: attemptAuthRecovery handles recovery failure', async () => {
      const mockSetUser = jest.fn();
      const mockSetToken = jest.fn();

      // Test with no token and no user (nothing to recover)
      const recovered = await attemptAuthRecovery(
        null,
        null,
        mockSetUser,
        mockSetToken
      );

      expect(recovered).toBe(false);
      expect(mockSetUser).not.toHaveBeenCalled();
      expect(mockSetToken).not.toHaveBeenCalled();
    });

    test('SHOULD FAIL: attemptAuthRecovery handles token decode exception', async () => {
      const mockSetUser = jest.fn();
      const mockSetToken = jest.fn();
      
      // Token that will cause decode error (invalid base64)
      const corruptToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.CorruptedPayload123!@#.FakeSignature';

      const recovered = await attemptAuthRecovery(
        corruptToken,
        null,
        mockSetUser,
        mockSetToken
      );

      expect(recovered).toBe(true); // Should clear corrupt token
      expect(mockSetToken).toHaveBeenCalledWith(null);
      expect(mockSetUser).toHaveBeenCalledWith(null);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('jwt_token');
    });

    test('SHOULD PASS: attemptEnhancedAuthRecovery falls back when all patterns fail', async () => {
      const mockSetUser = jest.fn();
      const mockSetToken = jest.fn();
      const mockSyncStore = jest.fn();

      // Mock basic recovery to fail
      jest.spyOn(AuthValidation, 'attemptAuthRecovery').mockResolvedValue(false);

      const recovered = await attemptEnhancedAuthRecovery(
        null,  // no token
        null,  // no user
        mockSetUser,
        mockSetToken,
        mockSyncStore
      );

      expect(recovered).toBe(false);
      expect(logger.warn).toHaveBeenCalledWith('[ENHANCED RECOVERY] All recovery patterns failed');
    });

    test('SHOULD PASS: attemptEnhancedAuthRecovery clears localStorage in browser environment', async () => {
      const mockSetUser = jest.fn();
      const mockSetToken = jest.fn();
      
      // Create expired token to trigger clear pattern
      const expiredToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6InRlc3QtdXNlci0xMjMiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJmdWxsX25hbWUiOiJUZXN0IFVzZXIiLCJleHAiOjE2MDk0NTkyMDAsInN1YiI6InRlc3QtdXNlci0xMjMifQ.ExpiredSignature';

      const recovered = await attemptEnhancedAuthRecovery(
        expiredToken,
        null,
        mockSetUser,
        mockSetToken
      );

      expect(recovered).toBe(true);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('jwt_token');
    });
  });

  describe('Auth Monitoring Comprehensive Coverage', () => {
    test('SHOULD PASS: monitorAuthState handles valid state without logging errors', () => {
      monitorAuthState(
        validToken,
        mockUser,
        true,
        'test_context'
      );

      // Should not log any errors for valid state
      expect(logger.error).not.toHaveBeenCalled();
    });

    test('SHOULD FAIL: monitorAuthState logs validation details for invalid state', () => {
      monitorAuthState(
        'invalid.token',
        mockUser,
        true,
        'test_invalid_context'
      );

      expect(logger.error).toHaveBeenCalledWith(
        '[AUTH MONITOR] Auth state invalid',
        expect.objectContaining({
          component: 'auth-validation',
          action: 'monitor_alert',
          context: 'test_invalid_context',
          validation: expect.objectContaining({
            isValid: false
          }),
          timestamp: expect.any(String)
        })
      );
    });
  });

  describe('Debug Helper Complete Coverage', () => {
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

    test('debugAuthState handles token decode failure gracefully', () => {
      const consoleSpy = jest.spyOn(console, 'group').mockImplementation();
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      const consoleEndSpy = jest.spyOn(console, 'groupEnd').mockImplementation();

      debugAuthState('invalid.token', null, true, 'test_decode_fail');

      expect(consoleErrorSpy).toHaveBeenCalledWith('Failed to decode token');

      consoleSpy.mockRestore();
      consoleErrorSpy.mockRestore();
      consoleEndSpy.mockRestore();
    });

    test('debugAuthState logs user information when present', () => {
      const consoleSpy = jest.spyOn(console, 'group').mockImplementation();
      const consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
      const consoleEndSpy = jest.spyOn(console, 'groupEnd').mockImplementation();

      debugAuthState(validToken, mockUser, true, 'test_with_user');

      expect(consoleLogSpy).toHaveBeenCalledWith('User:', {
        id: mockUser.id,
        email: mockUser.email
      });

      consoleSpy.mockRestore();
      consoleLogSpy.mockRestore();
      consoleEndSpy.mockRestore();
    });

    test('debugAuthState shows errors and warnings when present', () => {
      const consoleSpy = jest.spyOn(console, 'group').mockImplementation();
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
      const consoleEndSpy = jest.spyOn(console, 'groupEnd').mockImplementation();

      // Test with uninitialized state (generates warnings)
      debugAuthState(validToken, mockUser, false, 'test_with_warnings');

      expect(consoleWarnSpy).toHaveBeenCalledWith('Warnings:', expect.arrayContaining(['Auth context not yet initialized']));

      consoleSpy.mockRestore();
      consoleErrorSpy.mockRestore();
      consoleWarnSpy.mockRestore();
      consoleEndSpy.mockRestore();
    });
  });
});
