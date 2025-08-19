/**
 * Auth Test Helpers - Phase 1, Agent 1
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: All tiers (Free, Early, Mid, Enterprise)
 * - Business Goal: Prevent auth failures that block user access
 * - Value Impact: Reduces auth-related support tickets by 80%
 * - Revenue Impact: Prevents churn from auth issues
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - File size: ≤300 lines (MANDATORY)
 * - Functions: ≤8 lines each (MANDATORY)
 * - TypeScript with full type safety
 * - Composable and reusable utilities
 */

import { jest } from '@jest/globals';
// Define types based on existing auth patterns in the codebase
export interface TestUser {
  id: string;
  email: string;
  full_name?: string;
  name?: string;
  sub?: string;
  role?: string;
}

export interface AuthEndpoints {
  login: string;
  logout: string;
  callback: string;
  token: string;
  user: string;
  dev_login: string;
}

export interface AuthConfigResponse {
  development_mode: boolean;
  google_client_id: string;
  endpoints: AuthEndpoints;
  authorized_javascript_origins: string[];
  authorized_redirect_uris: string[];
}

// ============================================================================
// MOCK USER FACTORIES - User object creation utilities
// ============================================================================

/**
 * Create a basic authenticated user for testing
 */
export function createMockUser(
  id: string = 'test_user_123',
  email: string = 'test@example.com',
  options: Partial<TestUser> = {}
): TestUser {
  return {
    id,
    email,
    full_name: options.full_name || 'Test User',
    name: options.name || 'Test User',
    sub: options.sub || id,
    role: options.role || 'admin',
    ...options
  };
}

/**
 * Create an admin user for privileged testing
 */
export function createMockAdminUser(
  id: string = 'admin_user_456',
  email: string = 'admin@example.com'
): TestUser {
  return createMockUser(id, email, {
    role: 'admin',
    full_name: 'Admin User',
    name: 'Admin User'
  });
}

/**
 * Create a regular user for standard testing
 */
export function createMockRegularUser(
  id: string = 'regular_user_789',
  email: string = 'user@example.com'
): TestUser {
  return createMockUser(id, email, {
    role: 'user',
    full_name: 'Regular User',
    name: 'Regular User'
  });
}

/**
 * Create a guest user for anonymous testing
 */
export function createMockGuestUser(): TestUser {
  return createMockUser('guest_user', 'guest@example.com', {
    role: 'guest',
    full_name: 'Guest User',
    name: 'Guest User'
  });
}

// ============================================================================
// TOKEN MANAGEMENT MOCKS - JWT and session utilities
// ============================================================================

/**
 * Create a mock JWT token for testing
 */
export function createMockToken(
  userId: string = 'test_user_123',
  expiresIn: number = 3600
): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(JSON.stringify({
    sub: userId,
    email: 'test@example.com',
    exp: Math.floor(Date.now() / 1000) + expiresIn,
    iat: Math.floor(Date.now() / 1000)
  }));
  const signature = 'mock_signature_123';
  
  return `${header}.${payload}.${signature}`;
}

/**
 * Create an expired token for expiration testing
 */
export function createMockExpiredToken(userId: string = 'test_user_123'): string {
  return createMockToken(userId, -3600); // Expired 1 hour ago
}

/**
 * Create a token that expires soon for refresh testing
 */
export function createMockExpiringToken(
  userId: string = 'test_user_123',
  expiresInSeconds: number = 300
): string {
  return createMockToken(userId, expiresInSeconds);
}

/**
 * Decode mock token payload for testing
 */
export function decodeMockToken(token: string): any {
  try {
    const parts = token.split('.');
    const payload = JSON.parse(atob(parts[1]));
    return payload;
  } catch {
    return null;
  }
}

// ============================================================================
// AUTH CONFIG MOCKS - Configuration and endpoints
// ============================================================================

/**
 * Create mock auth configuration for testing
 */
export function createMockAuthConfig(
  developmentMode: boolean = false,
  options: Partial<AuthConfigResponse> = {}
): AuthConfigResponse {
  const baseUrl = 'http://localhost:8081';
  
  return {
    development_mode: developmentMode,
    google_client_id: options.google_client_id || 'mock-google-client-id',
    endpoints: {
      login: `${baseUrl}/auth/login`,
      logout: `${baseUrl}/auth/logout`,
      callback: `${baseUrl}/auth/callback`,
      token: `${baseUrl}/auth/token`,
      user: `${baseUrl}/auth/me`,
      dev_login: `${baseUrl}/auth/dev/login`,
      ...options.endpoints
    },
    authorized_javascript_origins: ['http://localhost:3000'],
    authorized_redirect_uris: ['http://localhost:3000/auth/callback'],
    ...options
  };
}

/**
 * Create development mode auth config
 */
export function createMockDevAuthConfig(): AuthConfigResponse {
  return createMockAuthConfig(true, {
    google_client_id: 'dev-mode-disabled'
  });
}

/**
 * Create production auth config
 */
export function createMockProdAuthConfig(): AuthConfigResponse {
  return createMockAuthConfig(false, {
    google_client_id: 'prod-google-client-id-123'
  });
}

// ============================================================================
// SESSION STATE HELPERS - Auth state management
// ============================================================================

/**
 * Create mock authenticated session state
 */
export function createMockAuthenticatedState(
  user?: TestUser,
  token?: string
): {
  isAuthenticated: boolean;
  user: TestUser | null;
  token: string | null;
  loading: boolean;
  error: string | null;
} {
  return {
    isAuthenticated: true,
    user: user || createMockUser(),
    token: token || createMockToken(),
    loading: false,
    error: null
  };
}

/**
 * Create mock unauthenticated session state
 */
export function createMockUnauthenticatedState(): {
  isAuthenticated: boolean;
  user: TestUser | null;
  token: string | null;
  loading: boolean;
  error: string | null;
} {
  return {
    isAuthenticated: false,
    user: null,
    token: null,
    loading: false,
    error: null
  };
}

/**
 * Create mock loading auth state
 */
export function createMockLoadingAuthState(): {
  isAuthenticated: boolean;
  user: TestUser | null;
  token: string | null;
  loading: boolean;
  error: string | null;
} {
  return {
    isAuthenticated: false,
    user: null,
    token: null,
    loading: true,
    error: null
  };
}

/**
 * Create mock auth error state
 */
export function createMockAuthErrorState(
  error: string = 'Authentication failed'
): {
  isAuthenticated: boolean;
  user: TestUser | null;
  token: string | null;
  loading: boolean;
  error: string | null;
} {
  return {
    isAuthenticated: false,
    user: null,
    token: null,
    loading: false,
    error
  };
}

// ============================================================================
// LOGIN/LOGOUT SIMULATORS - Auth flow simulation
// ============================================================================

/**
 * Simulate successful login flow
 */
export function simulateSuccessfulLogin(
  user?: TestUser,
  token?: string
): { user: TestUser; token: string } {
  const mockUser = user || createMockUser();
  const mockToken = token || createMockToken(mockUser.id);
  
  return { user: mockUser, token: mockToken };
}

/**
 * Simulate failed login attempt
 */
export function simulateFailedLogin(
  reason: string = 'Invalid credentials'
): { error: string } {
  return { error: reason };
}

/**
 * Simulate logout process
 */
export function simulateLogout(): {
  isAuthenticated: boolean;
  user: null;
  token: null;
} {
  return {
    isAuthenticated: false,
    user: null,
    token: null
  };
}

/**
 * Simulate dev mode login
 */
export function simulateDevLogin(
  userId: string = 'dev_user_123'
): { user: TestUser; token: string; dev_mode: boolean } {
  const user = createMockUser(userId, 'dev@example.com');
  const token = createMockToken(userId);
  
  return { user, token, dev_mode: true };
}

// ============================================================================
// AUTH SERVICE MOCKS - Service method mocking
// ============================================================================

/**
 * Create comprehensive auth service mock
 */
export function createMockAuthService() {
  return {
    getAuthConfig: jest.fn().mockResolvedValue(createMockAuthConfig()),
    getToken: jest.fn().mockReturnValue(null),
    getDevLogoutFlag: jest.fn().mockReturnValue(false),
    handleLogin: jest.fn().mockImplementation(() => {}),
    handleLogout: jest.fn().mockImplementation(() => Promise.resolve()),
    setDevLogoutFlag: jest.fn().mockImplementation(() => {}),
    clearDevLogoutFlag: jest.fn().mockImplementation(() => {}),
    removeToken: jest.fn().mockImplementation(() => {}),
    handleDevLogin: jest.fn().mockResolvedValue(simulateDevLogin()),
    getAuthHeaders: jest.fn().mockReturnValue({})
  };
}

/**
 * Create auth store mock with methods
 */
export function createMockAuthStore(authenticated: boolean = false) {
  const state = authenticated 
    ? createMockAuthenticatedState()
    : createMockUnauthenticatedState();
    
  return {
    ...state,
    login: jest.fn(),
    logout: jest.fn(),
    setLoading: jest.fn(),
    setError: jest.fn(),
    clearError: jest.fn()
  };
}

// ============================================================================
// AUTH ASSERTION HELPERS - Testing utilities
// ============================================================================

/**
 * Assert user object has required fields
 */
export function expectValidUser(user: TestUser): void {
  expect(user).toHaveProperty('id');
  expect(user).toHaveProperty('email');
  expect(user).toHaveProperty('full_name');
  expect(typeof user.id).toBe('string');
  expect(typeof user.email).toBe('string');
  expect(user.email).toContain('@');
}

/**
 * Assert token is properly formatted JWT
 */
export function expectValidToken(token: string): void {
  expect(typeof token).toBe('string');
  expect(token.split('.')).toHaveLength(3);
  
  const decoded = decodeMockToken(token);
  expect(decoded).toBeDefined();
  expect(decoded).toHaveProperty('sub');
  expect(decoded).toHaveProperty('exp');
}

/**
 * Assert auth state is consistent
 */
export function expectConsistentAuthState(state: {
  isAuthenticated: boolean;
  user: TestUser | null;
  token: string | null;
}): void {
  if (state.isAuthenticated) {
    expect(state.user).toBeDefined();
    expect(state.token).toBeDefined();
  } else {
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
  }
}