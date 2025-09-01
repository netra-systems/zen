/**
 * Unified Authentication Helpers for Cypress Tests
 * Provides consistent authentication methods across all test suites
 * Business Value: Platform Stability - ensures reliable test authentication
 */

export interface TestUser {
  id: string;
  email: string;
  full_name: string;
  token?: string;
}

// Default test user configuration
export const DEFAULT_TEST_USER: TestUser = {
  id: 'test-user-id',
  email: Cypress.env('CYPRESS_TEST_USER') || 'dev@example.com',
  full_name: 'Test User'
};

/**
 * Setup authenticated state by setting JWT token in localStorage
 * This is the primary method for test authentication
 */
export function setupAuthenticatedState(user: Partial<TestUser> = {}): void {
  const testUser = { ...DEFAULT_TEST_USER, ...user };
  
  cy.window().then((win) => {
    // Create a mock JWT token for testing
    const futureTimestamp = Math.floor(Date.now() / 1000) + (24 * 60 * 60); // 24 hours from now
    const mockPayload = btoa(JSON.stringify({
      sub: testUser.id,
      email: testUser.email,
      full_name: testUser.full_name,
      role: 'user',
      iat: Math.floor(Date.now() / 1000),
      exp: futureTimestamp
    }));
    const mockToken = testUser.token || `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${mockPayload}.mock-signature-for-testing`;
    
    // Set the JWT token (standard across all services)
    win.localStorage.setItem('jwt_token', mockToken);
    
    // Set user data if needed by frontend
    win.localStorage.setItem('user', JSON.stringify({
      id: testUser.id,
      email: testUser.email,
      full_name: testUser.full_name,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }));
  });
}

/**
 * Clear authentication state
 */
export function clearAuthState(): void {
  cy.window().then((win) => {
    win.localStorage.removeItem('jwt_token');
    win.localStorage.removeItem('user');
    win.localStorage.removeItem('refresh_token');
  });
}

/**
 * Setup auth API endpoints for testing
 */
export function setupAuthEndpoints(): void {
  // Mock auth config endpoint
  cy.intercept('GET', '**/auth/config', {
    statusCode: 200,
    body: {
      development_mode: true,
      enable_signup: true,
      oauth_providers: [],
      require_email_verification: false
    }
  }).as('authConfig');
  
  // Mock user endpoint
  cy.intercept('GET', '**/auth/user', {
    statusCode: 200,
    body: {
      id: DEFAULT_TEST_USER.id,
      email: DEFAULT_TEST_USER.email,
      full_name: DEFAULT_TEST_USER.full_name
    }
  }).as('authUser');
  
  // Mock token refresh
  cy.intercept('POST', '**/auth/refresh', {
    statusCode: 200,
    body: {
      access_token: 'new-test-token',
      refresh_token: 'new-refresh-token'
    }
  }).as('authRefresh');
}

/**
 * Perform actual login through UI (for integration tests)
 * Falls back to setupAuthenticatedState for faster test execution
 */
export function performUILogin(email?: string, password?: string): void {
  const testEmail = email || DEFAULT_TEST_USER.email;
  const testPassword = password || Cypress.env('CYPRESS_TEST_PASSWORD') || 'dev';
  
  // Check current URL to see if already logged in
  cy.url().then((url) => {
    if (url.includes('/chat') || url.includes('/settings')) {
      cy.log('Already authenticated, skipping login');
      return;
    }
    
    // Try dev mode login first
    cy.request({
      url: 'http://localhost:8081/auth/config',
      failOnStatusCode: false,
      timeout: 3000
    }).then((response) => {
      if (response.status === 200 && response.body?.development_mode) {
        // Development mode - use Quick Dev Login
        cy.visit('/login');
        cy.contains('button', 'Quick Dev Login', { timeout: 10000 })
          .should('be.visible')
          .should('not.be.disabled')
          .click();
        
        // Wait for successful login
        cy.url({ timeout: 15000 }).should('not.include', '/login');
        
        // Verify JWT token is stored
        cy.window().then((win) => {
          expect(win.localStorage.getItem('jwt_token')).to.be.a('string').and.not.be.empty;
        });
      } else {
        // Production mode - use mock authentication for testing
        cy.log('Using mock authentication for testing');
        setupAuthenticatedState();
        cy.visit('/chat');
      }
    });
  });
}

/**
 * Setup complete test environment with authentication
 * This is the recommended method for most tests
 */
export function setupAuthenticatedTestEnvironment(): void {
  setupAuthEndpoints();
  setupAuthenticatedState();
}

/**
 * Verify authentication state
 */
export function verifyAuthenticated(): void {
  cy.window().then((win) => {
    const token = win.localStorage.getItem('jwt_token');
    expect(token).to.be.a('string').and.not.be.empty;
  });
}