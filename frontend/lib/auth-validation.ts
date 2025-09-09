/**
 * Auth State Validation Helpers
 * 
 * CRITICAL: These helpers ensure auth state consistency and prevent
 * the chat initialization failures we experienced.
 * 
 * CHAT IS KING - Auth must be bulletproof.
 * 
 * @compliance type_safety.xml - Strongly typed validation
 * @compliance CLAUDE.md - Chat is 90% of value delivery
 */

import { User } from '@/types';
import { logger } from '@/lib/logger';
import { jwtDecode } from 'jwt-decode';

export interface AuthStateValidation {
  isValid: boolean;
  hasToken: boolean;
  hasUser: boolean;
  tokenExpired: boolean;
  userMatchesToken: boolean;
  errors: string[];
  warnings: string[];
}

export interface TokenValidation {
  isValid: boolean;
  isExpired: boolean;
  issuedInFuture: boolean;
  hasRequiredFields: boolean;
  decodedUser: User | null;
  errors: string[];
}

export interface AtomicAuthUpdate {
  token: string | null;
  user: User | null;
  timestamp: number;
}

/**
 * Validates the consistency of auth state
 * This is CRITICAL for preventing chat initialization failures
 */
export function validateAuthState(
  token: string | null,
  user: User | null,
  initialized: boolean
): AuthStateValidation {
  const validation: AuthStateValidation = {
    isValid: false,
    hasToken: !!token,
    hasUser: !!user,
    tokenExpired: false,
    userMatchesToken: false,
    errors: [],
    warnings: []
  };

  // Check initialization
  if (!initialized) {
    validation.warnings.push('Auth context not yet initialized');
    return validation;
  }

  // No token and no user is valid (logged out state)
  if (!token && !user) {
    validation.isValid = true;
    return validation;
  }

  // Token without user is INVALID (this was our bug!)
  if (token && !user) {
    validation.errors.push('CRITICAL: Token exists but user not set - chat will fail');
    logger.error('[AUTH VALIDATION] Token without user detected', {
      component: 'auth-validation',
      action: 'state_mismatch',
      hasToken: true,
      hasUser: false
    });
    return validation;
  }

  // User without token is INVALID
  if (!token && user) {
    validation.errors.push('User exists but no token - authentication inconsistent');
    return validation;
  }

  // Both token and user exist - validate consistency
  if (token && user) {
    try {
      const tokenValidation = validateToken(token);
      
      if (!tokenValidation.isValid) {
        validation.errors.push(...tokenValidation.errors);
        validation.tokenExpired = tokenValidation.isExpired;
        return validation;
      }

      // Check if user matches token
      if (tokenValidation.decodedUser) {
        const tokenUserId = tokenValidation.decodedUser.id || (tokenValidation.decodedUser as { sub?: string }).sub;
        const currentUserId = user.id || (user as { sub?: string }).sub;
        
        if (tokenUserId !== currentUserId) {
          validation.errors.push(`User ID mismatch: token=${tokenUserId}, user=${currentUserId}`);
        } else if (tokenValidation.decodedUser.email !== user.email) {
          validation.warnings.push(`Email mismatch: token=${tokenValidation.decodedUser.email}, user=${user.email}`);
        } else {
          validation.userMatchesToken = true;
        }
      }

      validation.tokenExpired = tokenValidation.isExpired;
      validation.isValid = validation.errors.length === 0 && validation.userMatchesToken;
      
    } catch (error) {
      validation.errors.push(`Token validation error: ${(error as Error).message}`);
    }
  }

  // Log validation result if there are issues
  if (!validation.isValid || validation.warnings.length > 0) {
    logger.warn('[AUTH VALIDATION] Auth state validation issues', {
      component: 'auth-validation',
      action: 'validation_complete',
      isValid: validation.isValid,
      errors: validation.errors,
      warnings: validation.warnings
    });
  }

  return validation;
}

/**
 * Validates a JWT token
 */
export function validateToken(token: string): TokenValidation {
  const validation: TokenValidation = {
    isValid: false,
    isExpired: false,
    issuedInFuture: false,
    hasRequiredFields: false,
    decodedUser: null,
    errors: []
  };

  if (!token) {
    validation.errors.push('Token is empty');
    return validation;
  }

  // Check token format
  const parts = token.split('.');
  if (parts.length !== 3) {
    validation.errors.push(`Invalid token format: expected 3 parts, got ${parts.length}`);
    return validation;
  }

  try {
    // Decode token
    const decoded = jwtDecode(token) as Record<string, unknown> & {
      email?: string;
      exp?: number;
      iat?: number;
      sub?: string;
    };
    validation.decodedUser = decoded as User;

    // Check required fields
    const requiredFields = ['email', 'exp'];
    const missingFields = requiredFields.filter(field => !decoded[field]);
    
    if (missingFields.length > 0) {
      validation.errors.push(`Missing required fields: ${missingFields.join(', ')}`);
    } else {
      validation.hasRequiredFields = true;
    }

    // Check expiration
    const now = Math.floor(Date.now() / 1000);
    if (decoded.exp && decoded.exp < now) {
      validation.isExpired = true;
      validation.errors.push(`Token expired at ${new Date(decoded.exp * 1000).toISOString()}`);
    }

    // Check issued at time (iat)
    if (decoded.iat && decoded.iat > now + 60) { // Allow 60 seconds clock skew
      validation.issuedInFuture = true;
      validation.errors.push(`Token issued in future: ${new Date(decoded.iat * 1000).toISOString()}`);
    }

    // Token is valid if no errors
    validation.isValid = validation.errors.length === 0;

  } catch (error) {
    validation.errors.push(`Token decode error: ${(error as Error).message}`);
  }

  return validation;
}

/**
 * Monitors auth state for inconsistencies
 * Call this periodically or on state changes
 */
export function monitorAuthState(
  token: string | null,
  user: User | null,
  initialized: boolean,
  context: string = 'unknown'
): void {
  const validation = validateAuthState(token, user, initialized);
  
  if (!validation.isValid) {
    logger.error('[AUTH MONITOR] Auth state invalid', {
      component: 'auth-validation',
      action: 'monitor_alert',
      context,
      validation,
      timestamp: new Date().toISOString()
    });

    // Special alert for the critical bug we fixed
    if (validation.hasToken && !validation.hasUser) {
      logger.error('[AUTH MONITOR] CRITICAL BUG DETECTED: Token without user!', {
        component: 'auth-validation',
        action: 'critical_bug_detected',
        context,
        description: 'This is the exact bug that broke chat initialization'
      });
    }
  }
}

/**
 * Attempts to recover from invalid auth state
 * Returns true if recovery was attempted
 */
export async function attemptAuthRecovery(
  token: string | null,
  user: User | null,
  setUser: (user: User | null) => void,
  setToken: (token: string | null) => void
): Promise<boolean> {
  logger.info('[AUTH RECOVERY] Attempting auth state recovery', {
    component: 'auth-validation',
    action: 'recovery_start',
    hasToken: !!token,
    hasUser: !!user
  });

  // If we have a token but no user, try to decode it
  if (token && !user) {
    try {
      const decoded = jwtDecode(token) as User;
      
      // Validate the decoded token
      const validation = validateToken(token);
      if (validation.isValid && validation.decodedUser) {
        setUser(validation.decodedUser);
        logger.info('[AUTH RECOVERY] Successfully recovered user from token', {
          component: 'auth-validation',
          action: 'recovery_success',
          userId: validation.decodedUser.id || (validation.decodedUser as { sub?: string }).sub
        });
        return true;
      }
    } catch (error) {
      logger.error('[AUTH RECOVERY] Failed to recover user from token', error as Error);
    }
  }

  // If token is invalid, clear everything
  if (token) {
    const validation = validateToken(token);
    if (!validation.isValid) {
      logger.warn('[AUTH RECOVERY] Clearing invalid token', {
        component: 'auth-validation',
        action: 'clear_invalid_token',
        errors: validation.errors
      });
      setToken(null);
      setUser(null);
      localStorage.removeItem('jwt_token');
      return true;
    }
  }

  return false;
}

/**
 * Atomic auth state update helper - prevents race conditions
 * CRITICAL: Always use this for simultaneous token+user updates
 */
export function createAtomicAuthUpdate(
  token: string | null, 
  user: User | null
): AtomicAuthUpdate {
  return {
    token,
    user,
    timestamp: Date.now()
  };
}

/**
 * Apply atomic auth update with validation
 * Returns true if update was applied successfully
 */
export function applyAtomicAuthUpdate(
  update: AtomicAuthUpdate,
  setToken: (token: string | null) => void,
  setUser: (user: User | null) => void,
  syncAuthStore?: (user: User | null, token: string | null) => void
): boolean {
  try {
    // Validate the atomic update before applying
    const validation = validateAuthState(update.token, update.user, true);
    
    if (!validation.isValid && validation.errors.length > 0) {
      logger.error('[ATOMIC UPDATE] Invalid auth state in atomic update', {
        component: 'auth-validation',
        action: 'atomic_update_invalid',
        errors: validation.errors,
        update
      });
      return false;
    }

    // Apply updates atomically
    setToken(update.token);
    setUser(update.user);
    
    // Sync with external store if provided
    if (syncAuthStore) {
      syncAuthStore(update.user, update.token);
    }

    logger.info('[ATOMIC UPDATE] Auth state updated atomically', {
      component: 'auth-validation',
      action: 'atomic_update_success',
      hasToken: !!update.token,
      hasUser: !!update.user,
      timestamp: update.timestamp
    });
    
    return true;
  } catch (error) {
    logger.error('[ATOMIC UPDATE] Failed to apply atomic auth update', error as Error);
    return false;
  }
}

/**
 * Enhanced recovery with atomic updates and proper error handling
 */
export async function attemptEnhancedAuthRecovery(
  token: string | null,
  user: User | null,
  setUser: (user: User | null) => void,
  setToken: (token: string | null) => void,
  syncAuthStore?: (user: User | null, token: string | null) => void
): Promise<boolean> {
  logger.info('[ENHANCED RECOVERY] Starting enhanced auth recovery', {
    component: 'auth-validation',
    action: 'enhanced_recovery_start',
    hasToken: !!token,
    hasUser: !!user
  });

  // First try basic recovery
  const basicRecoverySuccess = await attemptAuthRecovery(token, user, setUser, setToken);
  if (basicRecoverySuccess) {
    logger.info('[ENHANCED RECOVERY] Basic recovery succeeded');
    return true;
  }

  // If basic recovery failed, try enhanced patterns
  
  // Pattern 1: Token exists but might be invalid - validate and recover
  if (token) {
    const tokenValidation = validateToken(token);
    
    if (tokenValidation.isValid && tokenValidation.decodedUser && !user) {
      // We have a valid token with user data but no user set
      const atomicUpdate = createAtomicAuthUpdate(token, tokenValidation.decodedUser);
      const success = applyAtomicAuthUpdate(atomicUpdate, setToken, setUser, syncAuthStore);
      
      if (success) {
        logger.info('[ENHANCED RECOVERY] Recovered user from valid token');
        return true;
      }
    } else if (!tokenValidation.isValid) {
      // Token is invalid - clear both token and user atomically
      const atomicUpdate = createAtomicAuthUpdate(null, null);
      const success = applyAtomicAuthUpdate(atomicUpdate, setToken, setUser, syncAuthStore);
      
      if (success) {
        logger.info('[ENHANCED RECOVERY] Cleared invalid token and user');
        // Also clear from localStorage
        if (typeof window !== 'undefined') {
          localStorage.removeItem('jwt_token');
        }
        return true;
      }
    }
  }

  // Pattern 2: User exists but no token - invalid state, clear both
  if (user && !token) {
    const atomicUpdate = createAtomicAuthUpdate(null, null);
    const success = applyAtomicAuthUpdate(atomicUpdate, setToken, setUser, syncAuthStore);
    
    if (success) {
      logger.info('[ENHANCED RECOVERY] Cleared user without token');
      return true;
    }
  }

  logger.warn('[ENHANCED RECOVERY] All recovery patterns failed');
  return false;
}

/**
 * Debug helper to log current auth state
 */
export function debugAuthState(
  token: string | null,
  user: User | null,
  initialized: boolean,
  context: string = 'debug'
): void {
  const validation = validateAuthState(token, user, initialized);
  
  console.group(`🔐 Auth State Debug (${context})`);
  console.log('Initialized:', initialized);
  console.log('Has Token:', validation.hasToken);
  console.log('Has User:', validation.hasUser);
  console.log('Valid:', validation.isValid);
  
  if (validation.errors.length > 0) {
    console.error('Errors:', validation.errors);
  }
  
  if (validation.warnings.length > 0) {
    console.warn('Warnings:', validation.warnings);
  }
  
  if (token) {
    try {
      const decoded = jwtDecode(token);
      console.log('Token Decoded:', decoded);
    } catch {
      console.error('Failed to decode token');
    }
  }
  
  if (user) {
    console.log('User:', { id: user.id, email: user.email });
  }
  
  console.groupEnd();
}

// Export for use in tests and monitoring
export const AuthValidation = {
  validateAuthState,
  validateToken,
  monitorAuthState,
  attemptAuthRecovery,
  attemptEnhancedAuthRecovery,
  createAtomicAuthUpdate,
  applyAtomicAuthUpdate,
  debugAuthState
};