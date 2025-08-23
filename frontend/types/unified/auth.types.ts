/**
 * UNIFIED Auth Types - Single Source of Truth
 * 
 * Consolidates ALL authentication-related types from:
 * - types/domains/auth.ts
 * - types/auth.ts
 * - types/Token.ts
 * - types/backend_schema_auth.ts
 * - __tests__/utils/auth-test-helpers.ts
 * - types/config.ts (AuthEndpoints)
 * 
 * CRITICAL: This file replaces ALL other auth type definitions
 * Use ONLY these types for authentication
 */

// Re-export ALL auth types from domains (the authoritative source)
export type {
  // Core user types
  User,
  DevUser,
  GoogleUser,
  
  // Authentication configuration
  AuthEndpoints,
  AuthConfigResponse,
  
  // Token and authentication data
  Token,
  TokenPayload,
  DevLoginRequest,
  
  // User creation and management
  UserBase,
  UserCreate,
  UserCreateOAuth,
  UserUpdate
} from '../domains/auth';

// Re-export all utility functions
export {
  // Validation helpers
  isValidUser,
  isActiveUser,
  isAdminUser,
  hasValidToken,
  
  // Utility functions
  createGuestUser,
  sanitizeUserForClient
} from '../domains/auth';