/**
 * Auth Alignment Test
 * Verifies that the unified authentication system works correctly
 * Business Value: Platform Stability - ensures reliable authentication
 */

import { 
  setupAuthenticatedState, 
  setupAuthEndpoints,
  clearAuthState,
  verifyAuthenticated 
} from '../support/auth-helpers';
import { 
  setupTestWithAuth, 
  visitWithAuth,
  TEST_USERS 
} from '../support/test-auth-config';

describe('Authentication Alignment Test', () => {
  beforeEach(() => {
    clearAuthState();
  });

  it('should set up authentication state correctly', () => {
    setupAuthenticatedState();
    verifyAuthenticated();
    
    // Verify JWT token exists
    cy.window().then((win) => {
      const token = win.localStorage.getItem('jwt_token');
      expect(token).to.be.a('string');
      expect(token).to.include('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9');
    });
  });

  it('should set up user data correctly', () => {
    setupAuthenticatedState(TEST_USERS.default);
    
    cy.window().then((win) => {
      const userData = win.localStorage.getItem('user');
      expect(userData).to.be.a('string');
      
      const user = JSON.parse(userData);
      expect(user.id).to.equal(TEST_USERS.default.id);
      expect(user.email).to.equal(TEST_USERS.default.email);
      expect(user.full_name).to.equal(TEST_USERS.default.full_name);
    });
  });

  it('should clear authentication state', () => {
    setupAuthenticatedState();
    verifyAuthenticated();
    
    clearAuthState();
    
    cy.window().then((win) => {
      expect(win.localStorage.getItem('jwt_token')).to.be.null;
      expect(win.localStorage.getItem('user')).to.be.null;
    });
  });

  it('should visit page with authentication', () => {
    visitWithAuth('/chat');
    
    // Should have auth token
    verifyAuthenticated();
    
    // Should be on chat page
    cy.url().should('include', '/chat');
  });

  it('should set up complete test environment with auth', () => {
    setupTestWithAuth();
    cy.visit('/chat');
    
    // Should have auth token
    verifyAuthenticated();
    
    // Should have auth endpoints mocked
    cy.request({
      url: 'http://localhost:8081/auth/config',
      failOnStatusCode: false
    }).then((response) => {
      // Either real service or mocked
      expect(response.status).to.be.oneOf([200, 404]);
    });
  });

  it('should handle different user types', () => {
    // Test default user
    setupAuthenticatedState(TEST_USERS.default);
    cy.window().then((win) => {
      const userData = JSON.parse(win.localStorage.getItem('user'));
      expect(userData.email).to.equal('dev@example.com');
    });
    
    clearAuthState();
    
    // Test admin user
    setupAuthenticatedState(TEST_USERS.admin);
    cy.window().then((win) => {
      const userData = JSON.parse(win.localStorage.getItem('user'));
      expect(userData.email).to.equal('admin@example.com');
    });
    
    clearAuthState();
    
    // Test premium user
    setupAuthenticatedState(TEST_USERS.premium);
    cy.window().then((win) => {
      const userData = JSON.parse(win.localStorage.getItem('user'));
      expect(userData.email).to.equal('premium@example.com');
    });
  });

  it('should work with login command', () => {
    cy.login();
    
    // Should have JWT token
    verifyAuthenticated();
    
    // Should be on chat page
    cy.url().should('include', '/chat');
  });

  it('should maintain consistency across helpers', () => {
    // Test that all helpers use jwt_token (not auth_token)
    setupAuthenticatedState();
    
    cy.window().then((win) => {
      // Should have jwt_token
      expect(win.localStorage.getItem('jwt_token')).to.be.a('string');
      
      // Should NOT have auth_token (old pattern)
      expect(win.localStorage.getItem('auth_token')).to.be.null;
    });
  });
});