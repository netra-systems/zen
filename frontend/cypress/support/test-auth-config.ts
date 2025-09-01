/**
 * Consolidated Auth Test Configuration
 * Provides standard authentication setup for all Cypress tests
 * Business Value: Platform Stability - ensures consistent test authentication
 */

import { 
  setupAuthenticatedState, 
  setupAuthEndpoints,
  clearAuthState,
  verifyAuthenticated 
} from './auth-helpers';

/**
 * Standard test setup that includes authentication
 * Use this at the beginning of test suites that require auth
 */
export function setupTestWithAuth(): void {
  // Setup auth API endpoints
  setupAuthEndpoints();
  
  // Setup authenticated state
  setupAuthenticatedState();
  
  // Setup WebSocket mock if needed
  cy.mockWebSocket();
}

/**
 * Visit page with authentication already set up
 * Use this instead of cy.visit() for authenticated pages
 */
export function visitWithAuth(url: string): void {
  setupAuthenticatedState();
  cy.visit(url);
}

/**
 * Standard beforeEach hook for authenticated tests
 * Use this in describe blocks that need authentication
 */
export function authBeforeEach(): void {
  // Clear any previous auth state
  clearAuthState();
  
  // Setup fresh auth state
  setupTestWithAuth();
}

/**
 * Verify user is authenticated and on expected page
 */
export function verifyAuthenticatedPage(expectedUrl: string): void {
  verifyAuthenticated();
  cy.url().should('include', expectedUrl);
}

// Export common test user data for consistency
export const TEST_USERS = {
  default: {
    id: 'test-user-id',
    email: 'dev@example.com',
    full_name: 'Test User'
  },
  admin: {
    id: 'admin-user-id',
    email: 'admin@example.com',
    full_name: 'Admin User'
  },
  premium: {
    id: 'premium-user-id',
    email: 'premium@example.com',
    full_name: 'Premium User'
  }
};

// Export auth-related intercept aliases for consistency
export const AUTH_ALIASES = {
  config: '@authConfig',
  user: '@authUser',
  refresh: '@authRefresh',
  login: '@authLogin',
  logout: '@authLogout'
};