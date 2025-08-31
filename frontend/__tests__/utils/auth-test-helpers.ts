/**
 * Auth Test Helpers - Comprehensive Authentication Testing Utilities
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: All (Free → Enterprise)
 * - Business Goal: Ensure secure and reliable authentication across all user tiers
 * - Value Impact: Prevents auth failures that block 100% of user interactions
 * - Revenue Impact: Protects entire $500K+ MRR dependent on secure authentication
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - File size: ≤300 lines (MANDATORY)
 * - Functions: ≤8 lines each (MANDATORY)
 * - TypeScript with full type safety
 * - Composable and reusable utilities
 */

import { jest } from '@jest/globals';
import { User, Token, AuthEndpoints, AuthConfigResponse } from '../../types/unified/auth.types';

// ============================================================================
// AUTH USER MOCK FACTORIES - User account generation
// ============================================================================

export interface MockUser {
  id: string;
  email: string;
  full_name?: string | null;
  picture?: string | null;
  is_active?: boolean;
  is_superuser?: boolean;
  access_token?: string;
  token_type?: string;
}

/**
 * Create mock user with minimal data
 */
export function createMockUser(overrides: Partial<MockUser> = {}): MockUser {
  const id = overrides.id || `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  return {
    id,
    email: overrides.email || `test.${id}@example.com`,
    full_name: overrides.full_name || `Test User ${id.slice(-8)}`,
    picture: overrides.picture || null,
    is_active: overrides.is_active !== false,
    is_superuser: overrides.is_superuser || false,
    access_token: overrides.access_token || `token_${id}`,
    token_type: overrides.token_type || 'bearer',
    ...overrides
  };
}

/**
 * Create authenticated user with token
 */
export function createAuthenticatedUser(email?: string): MockUser {
  return createMockUser({
    email: email || 'auth.user@example.com',
    is_active: true,
    access_token: `valid_token_${Date.now()}`,
    token_type: 'bearer'
  });
}

/**
 * Create admin user with elevated permissions
 */
export function createAdminUser(): MockUser {
  return createMockUser({
    email: 'admin@example.com',
    full_name: 'Admin User',
    is_active: true,
    is_superuser: true,
    access_token: `admin_token_${Date.now()}`
  });
}

/**
 * Create guest/unauthenticated user
 */
export function createGuestUser(): MockUser {
  return createMockUser({
    id: 'guest',
    email: 'guest@netrasystems.ai',
    is_active: false,
    access_token: undefined,
    token_type: undefined
  });
}

// ============================================================================
// TOKEN MOCK FACTORIES - Authentication token generation
// ============================================================================

export interface MockToken {
  access_token: string;
  token_type: string;
  expires_in?: number | null;
  refresh_token?: string | null;
  user: MockUser;
}

/**
 * Create mock token with user
 */
export function createMockToken(user?: MockUser): MockToken {
  const mockUser = user || createAuthenticatedUser();
  
  return {
    access_token: `token_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    token_type: 'bearer',
    expires_in: 3600, // 1 hour
    refresh_token: `refresh_${Date.now()}`,
    user: mockUser
  };
}

/**
 * Create expired token
 */
export function createExpiredToken(): MockToken {
  const token = createMockToken();
  return {
    ...token,
    expires_in: -1 // Expired
  };
}

/**
 * Create mock expired token with user ID
 */
export function createMockExpiredToken(userId: string): string {
  return `expired_token_${userId}_${Date.now()}`;
}

/**
 * Create mock expiring token with user ID and duration
 */
export function createMockExpiringToken(userId: string, expiresInSeconds: number): string {
  return `expiring_token_${userId}_${expiresInSeconds}_${Date.now()}`;
}

/**
 * Create token without refresh capability
 */
export function createTokenWithoutRefresh(): MockToken {
  const token = createMockToken();
  return {
    ...token,
    refresh_token: null
  };
}

// ============================================================================
// AUTH STATE MOCK FACTORIES - Authentication state generation
// ============================================================================

export interface MockAuthState {
  user: MockUser | null;
  token: MockToken | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

/**
 * Create authenticated auth state
 */
export function createAuthenticatedState(user?: MockUser): MockAuthState {
  const mockUser = user || createAuthenticatedUser();
  
  return {
    user: mockUser,
    token: createMockToken(mockUser),
    isAuthenticated: true,
    isLoading: false,
    error: null
  };
}

/**
 * Alias for createAuthenticatedState for backward compatibility
 */
export const createMockAuthenticatedState = createAuthenticatedState;

/**
 * Create unauthenticated auth state
 */
export function createUnauthenticatedState(): MockAuthState {
  return {
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: false,
    error: null
  };
}

/**
 * Alias for createUnauthenticatedState for backward compatibility
 */
export const createMockUnauthenticatedState = createUnauthenticatedState;

/**
 * Create loading auth state
 */
export function createLoadingAuthState(): MockAuthState {
  return {
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
    error: null
  };
}

/**
 * Create error auth state
 */
export function createErrorAuthState(error: string = 'Authentication failed'): MockAuthState {
  return {
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: false,
    error
  };
}

// ============================================================================
// AUTH CONFIG MOCK FACTORIES - Configuration generation
// ============================================================================

/**
 * Create mock auth config response
 */
export function createMockAuthConfig(): AuthConfigResponse {
  return {
    google_client_id: 'test_google_client_id.apps.googleusercontent.com',
    endpoints: {
      login: '/auth/login',
      logout: '/auth/logout',
      callback: '/auth/callback',
      token: '/auth/token',
      user: '/auth/user',
      dev_login: '/auth/dev-login'
    },
    development_mode: true,
    authorized_javascript_origins: ['http://localhost:3000'],
    authorized_redirect_uris: ['http://localhost:3000/auth/callback'],
    google_login_url: 'https://accounts.google.com/oauth/authorize',
    logout_url: '/auth/logout'
  };
}

// ============================================================================
// AUTH SERVICE MOCK FACTORIES - Service mocking utilities
// ============================================================================

/**
 * Setup auth service mocks
 */
export function setupAuthServiceMocks() {
  return {
    login: jest.fn(() => Promise.resolve(createMockToken())),
    logout: jest.fn(() => Promise.resolve({ success: true })),
    refreshToken: jest.fn(() => Promise.resolve(createMockToken())),
    getCurrentUser: jest.fn(() => Promise.resolve(createAuthenticatedUser())),
    validateToken: jest.fn(() => Promise.resolve(true))
  };
}

/**
 * Create mock auth context
 */
export function createMockAuthContext(state?: Partial<MockAuthState>) {
  const authState = {
    ...createUnauthenticatedState(),
    ...state
  };
  
  return {
    authState,
    login: jest.fn(() => Promise.resolve(createMockToken())),
    logout: jest.fn(() => Promise.resolve(undefined)),
    refreshAuth: jest.fn(() => Promise.resolve(createMockToken()))
  };
}

// ============================================================================
// AUTH VALIDATION HELPERS - Testing utilities
// ============================================================================

/**
 * Assert user is authenticated
 */
export function expectUserAuthenticated(user: MockUser | null): void {
  expect(user).toBeDefined();
  expect(user?.is_active).toBe(true);
  expect(user?.access_token).toBeDefined();
  expect(typeof user?.access_token).toBe('string');
}

/**
 * Assert user is not authenticated
 */
export function expectUserNotAuthenticated(user: MockUser | null): void {
  expect(user === null || user.access_token === undefined).toBe(true);
}

/**
 * Assert token is valid
 */
export function expectValidToken(token: MockToken | null): void {
  expect(token).toBeDefined();
  expect(typeof token?.access_token).toBe('string');
  expect(token?.token_type).toBe('bearer');
  expect(token?.user).toBeDefined();
}

/**
 * Assert auth state is authenticated
 */
export function expectAuthStateAuthenticated(state: MockAuthState): void {
  expect(state.isAuthenticated).toBe(true);
  expect(state.user).toBeDefined();
  expect(state.token).toBeDefined();
  expect(state.error).toBeNull();
}

/**
 * Assert auth state has error
 */
export function expectAuthStateError(state: MockAuthState, expectedError?: string): void {
  expect(state.isAuthenticated).toBe(false);
  expect(state.error).toBeDefined();
  if (expectedError) {
    expect(state.error).toBe(expectedError);
  }
}

// ============================================================================
// SESSION MANAGEMENT HELPERS - Session testing utilities
// ============================================================================

/**
 * Mock session storage operations
 */
export function setupSessionMocks() {
  return {
    saveSession: jest.fn(),
    loadSession: jest.fn().mockReturnValue(createMockToken()),
    clearSession: jest.fn(),
    isSessionValid: jest.fn().mockReturnValue(true)
  };
}

/**
 * Simulate session expiry
 */
export function simulateSessionExpiry(): MockAuthState {
  return createErrorAuthState('Session expired');
}

/**
 * Simulate successful login flow
 */
export function simulateLoginFlow(email?: string): {
  initialState: MockAuthState;
  loadingState: MockAuthState;
  successState: MockAuthState;
} {
  return {
    initialState: createUnauthenticatedState(),
    loadingState: createLoadingAuthState(),
    successState: createAuthenticatedState(createAuthenticatedUser(email))
  };
}

/**
 * Mock localStorage for auth persistence
 */
export function mockAuthStorage() {
  const storage: Record<string, string> = {};
  
  return {
    getItem: jest.fn((key: string) => storage[key] || null),
    setItem: jest.fn((key: string, value: string) => { storage[key] = value; }),
    removeItem: jest.fn((key: string) => { delete storage[key]; }),
    clear: jest.fn(() => { Object.keys(storage).forEach(key => delete storage[key]); })
  };
}

// All functions are already exported above - no need for re-export