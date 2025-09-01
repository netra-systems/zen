/**
 * CRITICAL: Auth Persistence and Token Propagation Regression Tests
 * 
 * These tests MUST FAIL initially to expose the current issues:
 * 1. Users are logged out on page refresh
 * 2. AuthGuard doesn't properly propagate tokens to threads/components
 * 
 * @priority CRITICAL
 * @category regression
 */

describe('Critical Auth Persistence Regressions', () => {
  const TEST_USER = {
    email: 'test@example.com',
    password: 'password123',
    name: 'Test User'
  };

  beforeEach(() => {
    // Clear all storage to ensure clean state
    cy.clearAllSessionStorage();
    cy.clearAllLocalStorage();
    cy.clearAllCookies();
    
    // Visit the app
    cy.visit('/', { failOnStatusCode: false });
  });

  describe('Issue #1: Page Refresh Logout', () => {
    it('MUST maintain authentication state after page refresh', () => {
      // Step 1: Login successfully
      cy.window().then((win) => {
        // Simulate successful login by setting token
        const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxOTk5OTk5OTk5LCJpYXQiOjE1MTYyMzkwMjJ9.abc';
        win.localStorage.setItem('jwt_token', mockToken);
      });

      // Step 2: Navigate to protected page
      cy.visit('/chat');
      cy.wait(2000); // Wait for auth initialization

      // Step 3: Verify user is authenticated
      cy.window().its('localStorage.jwt_token').should('exist');
      
      // Step 4: Refresh the page
      cy.reload();
      cy.wait(3000); // Wait for auth re-initialization

      // Step 5: CRITICAL ASSERTION - User should still be authenticated
      cy.window().its('localStorage.jwt_token').should('exist');
      cy.url().should('include', '/chat'); // Should stay on protected page
      cy.get('[data-testid="loading"]').should('not.exist'); // No loading screen
      
      // Step 6: Verify auth context still has user
      cy.window().then((win) => {
        // Check if auth context maintains user state
        cy.wrap(win).should('have.property', '__NEXT_AUTH_USER__');
      });
    });

    it('MUST restore user data from localStorage token on mount', () => {
      // Pre-set a valid token before page load
      const validToken = generateValidJWT({
        email: TEST_USER.email,
        sub: 'user-123',
        exp: Math.floor(Date.now() / 1000) + 3600 // 1 hour from now
      });

      cy.window().then((win) => {
        win.localStorage.setItem('jwt_token', validToken);
      });

      // Load the page fresh
      cy.visit('/chat');
      cy.wait(2000);

      // User should be authenticated without manual login
      cy.url().should('include', '/chat');
      
      // Check that user info is available in the UI
      cy.get('[data-testid="user-menu"]', { timeout: 10000 }).should('exist');
      cy.get('[data-testid="user-email"]').should('contain', TEST_USER.email);
    });

    it('MUST handle token refresh during page lifecycle', () => {
      // Mock the token refresh endpoint
      cy.intercept('POST', '**/auth/refresh', {
        statusCode: 200,
        body: {
          jwt_token: generateValidJWT({
            email: TEST_USER.email,
            sub: 'user-123',
            exp: Math.floor(Date.now() / 1000) + 3600 // New token with 1 hour expiry
          }),
          refresh_token: 'new-refresh-token-123'
        }
      }).as('tokenRefresh');

      // Set a token that's about to expire
      const aboutToExpireToken = generateValidJWT({
        email: TEST_USER.email,
        sub: 'user-123',
        exp: Math.floor(Date.now() / 1000) + 30, // 30 seconds from now
        iat: Math.floor(Date.now() / 1000) - 30
      });

      cy.window().then((win) => {
        win.localStorage.setItem('jwt_token', aboutToExpireToken);
        win.localStorage.setItem('refresh_token', 'old-refresh-token-123');
      });

      cy.visit('/chat');
      cy.wait(2000);

      // Wait for automatic token refresh (should happen within 30 seconds)
      cy.wait('@tokenRefresh', { timeout: 35000 });

      // Token should be refreshed automatically
      cy.window().then((win) => {
        const currentToken = win.localStorage.getItem('jwt_token');
        expect(currentToken).to.not.equal(aboutToExpireToken);
        expect(currentToken).to.exist;
      });

      // User should remain authenticated
      cy.url().should('include', '/chat');
    });
  });

  describe('Issue #2: AuthGuard Token Propagation', () => {
    beforeEach(() => {
      // Setup authenticated state
      const validToken = generateValidJWT({
        email: TEST_USER.email,
        sub: 'user-123',
        exp: Math.floor(Date.now() / 1000) + 3600
      });

      cy.window().then((win) => {
        win.localStorage.setItem('jwt_token', validToken);
      });
    });

    it('MUST pass authentication token to thread components', () => {
      cy.visit('/chat');
      cy.wait(2000);

      // Create a new thread
      cy.get('[data-testid="new-thread-button"]').click();
      cy.wait(1000);

      // Check that API calls include auth headers
      cy.intercept('POST', '**/api/**', (req) => {
        // CRITICAL: Authorization header must be present for authenticated endpoints
        if (!req.url.includes('/auth/config') && !req.url.includes('/auth/me')) {
          expect(req.headers).to.have.property('authorization');
          expect(req.headers.authorization).to.match(/^Bearer .+/);
        }
      }).as('apiWithAuth');

      // Type a message to trigger API call
      cy.get('[data-testid="message-input"]').type('Test message{enter}');
      
      cy.wait('@apiWithAuth');
    });

    it('MUST maintain auth state when navigating between protected routes', () => {
      cy.visit('/chat');
      cy.wait(2000);

      // Navigate to another protected route
      cy.visit('/corpus');
      cy.wait(2000);

      // Should not redirect to login
      cy.url().should('include', '/corpus');
      
      // Navigate back
      cy.visit('/chat');
      cy.wait(2000);

      // Should still be authenticated
      cy.url().should('include', '/chat');

      // Token should persist throughout navigation
      cy.window().its('localStorage.jwt_token').should('exist');
    });

    it('MUST provide auth token to all API calls from protected pages', () => {
      // Intercept all API calls
      let apiCallCount = 0;
      cy.intercept('**/(api|auth)/**', (req) => {
        if (req.method !== 'OPTIONS') {
          apiCallCount++;
          // Every API call should have authorization header except public endpoints
          if (!req.url.includes('/auth/config') && !req.url.includes('/auth/me') && !req.url.includes('/auth/verify')) {
            expect(req.headers).to.have.property('authorization');
            expect(req.headers.authorization).to.match(/^Bearer .+/);
          }
        }
      });

      cy.visit('/chat');
      cy.wait(3000);

      // Trigger some API calls
      cy.get('[data-testid="message-input"]').type('Test message');
      cy.wait(1000);

      // Verify API calls were made with auth
      cy.wrap(null).then(() => {
        expect(apiCallCount).to.be.greaterThan(0);
      });
    });
  });

  describe('Dev Environment Auto-Login Persistence', () => {
    it('MUST maintain dev auto-login across page refreshes', () => {
      // In dev mode, auto-login should persist
      cy.visit('/', { 
        onBeforeLoad: (win) => {
          // Set development mode flag
          win.localStorage.setItem('NODE_ENV', 'development');
        }
      });

      cy.wait(5000); // Wait for auto-login

      // Should be automatically logged in
      cy.window().its('localStorage.jwt_token').should('exist');

      // Refresh page
      cy.reload();
      cy.wait(3000);

      // Should still be logged in
      cy.window().its('localStorage.jwt_token').should('exist');
      
      // Should not show login page
      cy.get('[data-testid="login-button"]').should('not.exist');
    });

    it('MUST respect explicit logout in dev mode', () => {
      cy.visit('/');
      cy.wait(5000); // Wait for potential auto-login

      // Explicitly logout
      cy.get('[data-testid="user-menu"]').click();
      cy.get('[data-testid="logout-button"]').click();
      cy.wait(2000);

      // Refresh page
      cy.reload();
      cy.wait(3000);

      // Should NOT auto-login after explicit logout
      cy.window().its('localStorage.jwt_token').should('not.exist');
      cy.get('[data-testid="login-button"]').should('exist');
    });
  });

  describe('Critical State Synchronization', () => {
    it('MUST sync auth state between AuthContext and Zustand store', () => {
      const validToken = generateValidJWT({
        email: TEST_USER.email,
        sub: 'user-123',
        exp: Math.floor(Date.now() / 1000) + 3600
      });

      cy.window().then((win) => {
        win.localStorage.setItem('jwt_token', validToken);
      });

      cy.visit('/chat');
      cy.wait(2000);

      // Check both auth context and Zustand store
      cy.window().then((win) => {
        // Check auth state persistence mechanisms
        const zustandState = win.localStorage.getItem('auth-storage');
        const jwtToken = win.localStorage.getItem('jwt_token');
        
        // At least one persistence mechanism should work
        if (zustandState) {
          const state = JSON.parse(zustandState);
          expect(state.state.token || jwtToken).to.exist;
          expect(state.state.user).to.exist;
        } else {
          expect(jwtToken).to.equal(validToken);
        }
      });
    });

    it('MUST handle concurrent auth operations without race conditions', () => {
      const validToken = generateValidJWT({
        email: TEST_USER.email,
        sub: 'user-123',
        exp: Math.floor(Date.now() / 1000) + 60 // Short expiry
      });

      cy.window().then((win) => {
        win.localStorage.setItem('jwt_token', validToken);
      });

      // Open multiple tabs/windows simulation
      cy.visit('/chat');
      cy.wait(1000);

      // Simulate storage event from another tab
      cy.window().then((win) => {
        const newToken = generateValidJWT({
          email: TEST_USER.email,
          sub: 'user-123',
          exp: Math.floor(Date.now() / 1000) + 3600
        });
        
        // Dispatch storage event
        const event = new StorageEvent('storage', {
          key: 'jwt_token',
          newValue: newToken,
          oldValue: validToken,
          storageArea: win.localStorage
        });
        win.dispatchEvent(event);
      });

      cy.wait(2000);

      // Should handle the token update gracefully
      cy.url().should('include', '/chat');
      cy.get('[data-testid="user-email"]').should('contain', TEST_USER.email);
    });
  });
});

// Helper function to generate valid JWT for testing
function generateValidJWT(payload: any): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = btoa(JSON.stringify({
    ...payload,
    iat: payload.iat || Math.floor(Date.now() / 1000),
    name: payload.name || 'Test User'
  }));
  return `${header}.${body}.test-signature`;
}