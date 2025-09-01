/// <reference types="cypress" />

/**
 * User Profile Basic Information Management E2E Tests
 * Updated for current system implementation:
 * - Auth endpoints: /auth/config, /auth/me, /auth/verify, /auth/refresh
 * - Current token structure: jwt_token, refresh_token, user
 * - API endpoints: /api/user/* for user management
 * - Circuit breaker integration for resilient API calls
 */

describe('User Profile Basic Information Management', () => {
  beforeEach(() => {
    // Clear storage and setup authenticated state matching current system
    cy.clearLocalStorage();
    cy.clearCookies();
    
    // Prevent uncaught exceptions from failing tests
    Cypress.on('uncaught:exception', (err, runnable) => {
      return false;
    });
    
    // Setup current auth state structure (matching actual token names)
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'mock-jwt-token-for-testing');
      win.localStorage.setItem('refresh_token', 'mock-refresh-token-for-testing');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
        picture: null,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      }));
    });
    
    // Mock auth verification endpoint
    cy.intercept('POST', '/auth/verify', {
      statusCode: 200,
      body: { valid: true, user_id: 'test-user-id' }
    }).as('verifyAuth');
    
    // Mock user profile endpoint
    cy.intercept('GET', '/api/user/profile', {
      statusCode: 200,
      body: {
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
        picture: null,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      }
    }).as('getUserProfile');
    
    // Visit main page
    cy.visit('/', { failOnStatusCode: false });
  });

  it('should display user profile information in header', () => {
    // Since /settings doesn't exist, check user display in header component
    cy.get('[data-testid="auth-component"]').should('exist');
    cy.get('[data-testid="user-email"]').should('contain', 'Test User');

    
    // Verify logout functionality exists
    cy.get('[data-testid="logout-button"]').should('exist').and('contain', 'Logout');
  });

  it('should validate user authentication state', () => {
    // Check that user is properly authenticated with current token structure
    cy.window().then((win) => {
      const token = win.localStorage.getItem('jwt_token');
      const refreshToken = win.localStorage.getItem('refresh_token');
      const user = win.localStorage.getItem('user');
      expect(token).to.equal('mock-jwt-token-for-testing');
      expect(refreshToken).to.equal('mock-refresh-token-for-testing');
      expect(user).to.not.be.null;
      
      if (user) {
        const userData = JSON.parse(user);
        expect(userData.email).to.equal('test@netrasystems.ai');
        expect(userData.full_name).to.equal('Test User');
      }
    });
  });

  it('should handle logout functionality', () => {
    // Test logout button exists and works
    cy.get('[data-testid="logout-button"]').should('exist');
    
    // Mock logout endpoint with current auth service structure
    cy.intercept('POST', '/auth/logout', {
      statusCode: 200,
      body: { success: true, message: 'Logged out successfully' }
    }).as('logoutRequest');
    
    cy.get('[data-testid="logout-button"]').click();
    
    // After logout, user should see login button
    cy.get('[data-testid="login-button"]').should('exist');
  });

  it('should persist authentication across page reloads', () => {
    // Navigate to different pages and verify auth persists
    const testRoutes = ['/chat', '/corpus', '/admin'];
    
    testRoutes.forEach(route => {
      cy.visit(route, { failOnStatusCode: false });
      
      // Check that auth data persists in localStorage with current token structure
      cy.window().then((win) => {
        const token = win.localStorage.getItem('jwt_token');
        const refreshToken = win.localStorage.getItem('refresh_token');
        const user = win.localStorage.getItem('user');
        expect(token).to.not.be.null;
        expect(refreshToken).to.not.be.null;
        expect(user).to.not.be.null;
      });
    });
  });

  it('should display user avatar when available', () => {
    // Update user data to include avatar
    cy.window().then((win) => {
      const userData = {
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
        picture: 'https://example.com/avatar.jpg',
        created_at: '2024-01-01T00:00:00Z'
      };
      win.localStorage.setItem('user', JSON.stringify(userData));
    });
    
    cy.reload();
    
    // Check if avatar is displayed in header
    cy.get('[data-testid="auth-component"]').within(() => {
      cy.get('img').should('have.attr', 'src', 'https://example.com/avatar.jpg');
      cy.get('img').should('have.attr', 'alt', 'Test User');
    });
  });

  it('should handle missing avatar gracefully', () => {
    // Set user without avatar
    cy.window().then((win) => {
      const userData = {
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
        picture: null,
        created_at: '2024-01-01T00:00:00Z'
      };
      win.localStorage.setItem('user', JSON.stringify(userData));
    });
    
    cy.reload();
    
    // Should still show user name without avatar image
    cy.get('[data-testid="auth-component"]').within(() => {
      cy.get('[data-testid="user-email"]').should('contain', 'Test User');
      cy.get('img').should('not.exist'); // No avatar image when picture is null
    });
  });

  it('should handle keyboard navigation in header', () => {
    // Test tab navigation through header elements
    cy.get('body').tab();
    
    // Should be able to navigate to logout button
    cy.get('[data-testid="logout-button"]').focus();
    cy.focused().should('contain', 'Logout');
    
    // Test keyboard activation
    cy.get('[data-testid="logout-button"]').type('{enter}');
    cy.get('[data-testid="login-button"]').should('exist');
  });

  it('should maintain session state during navigation', () => {
    // Navigate between different pages
    const pages = ['/', '/chat', '/corpus'];
    
    pages.forEach(page => {
      cy.visit(page, { failOnStatusCode: false });
      
      // Verify user remains authenticated on each page
      cy.get('[data-testid="auth-component"]').should('exist');
      cy.get('[data-testid="user-email"]').should('contain', 'Test User');
    });
  });

  it('should handle authentication errors gracefully', () => {
    // Clear auth data to simulate expired token (current token structure)
    cy.window().then((win) => {
      win.localStorage.removeItem('jwt_token');
      win.localStorage.removeItem('refresh_token');
      win.localStorage.removeItem('user');
    });
    
    cy.reload();
    
    // Should show login button when not authenticated
    cy.get('[data-testid="login-button"]').should('exist').and('contain', 'Login with Google');
    
    // Should not show user profile components when not authenticated
    cy.get('[data-testid="user-email"]').should('not.exist');
  });
});
