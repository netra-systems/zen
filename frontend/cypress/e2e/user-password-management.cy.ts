/// <reference types="cypress" />

/**
 * User Password Management E2E Tests
 * Updated for current system implementation:
 * - Auth endpoints: /auth/config, /auth/me, /auth/verify, /auth/refresh
 * - Current token structure: jwt_token, refresh_token, user
 * - API endpoints: /api/user/* for user management
 * - Circuit breaker integration for resilient API calls
 * 
 * BVJ: Enterprise segment - Password security drives enterprise compliance
 * Value Impact: Password controls = security compliance = Enterprise trust
 */

describe('User Password Management', () => {
  beforeEach(() => {
    // Clear storage and setup authenticated state matching current system
    cy.clearLocalStorage();
    cy.clearCookies();
    
    // Prevent uncaught exceptions from failing tests
    Cypress.on('uncaught:exception', (err, runnable) => {
      return false;
    });
    
    // Setup current auth state structure
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token-12345');
      win.localStorage.setItem('refresh_token', 'test-refresh-token-67890');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      }));
    });
    
    // Mock auth verification
    cy.intercept('POST', '/auth/verify', {
      statusCode: 200,
      body: { valid: true, user_id: 'test-user-id' }
    }).as('verifyAuth');

    cy.visit('/', { failOnStatusCode: false });
  });

  it('should handle password change successfully', () => {
    // Navigate to security settings
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Fill in password change form
    cy.get('input[name="current_password"]').type('currentPassword123');
    cy.get('input[name="new_password"]').type('newSecurePassword456!');
    cy.get('input[name="confirm_password"]').type('newSecurePassword456!');

    // Mock password change endpoint with current API structure
    cy.intercept('POST', '/api/user/change-password', {
      statusCode: 200,
      body: {
        success: true,
        message: 'Password changed successfully'
      }
    }).as('changePassword');

    // Submit password change
    cy.get('button').contains('Change Password').click();
    cy.wait('@changePassword');

    // Verify success message
    cy.contains('Password changed successfully').should('be.visible');

    // Verify form is cleared
    cy.get('input[name="current_password"]').should('have.value', '');
    cy.get('input[name="new_password"]').should('have.value', '');
    cy.get('input[name="confirm_password"]').should('have.value', '');
  });

  it('should validate password requirements', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Test password validation - weak password
    cy.get('input[name="current_password"]').type('currentPassword123');
    cy.get('input[name="new_password"]').type('weak');
    cy.get('input[name="confirm_password"]').type('weak');

    // Verify validation error
    cy.contains('Password must be at least 8 characters').should('be.visible');

    // Test password mismatch
    cy.get('input[name="new_password"]').clear().type('StrongPassword123!');
    cy.get('input[name="confirm_password"]').clear().type('DifferentPassword456!');
    cy.get('button').contains('Change Password').click();

    // Verify mismatch error
    cy.contains('Passwords do not match').should('be.visible');
  });

  it('should handle incorrect current password', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Fill in password change form with wrong current password
    cy.get('input[name="current_password"]').type('wrongPassword');
    cy.get('input[name="new_password"]').type('newSecurePassword456!');
    cy.get('input[name="confirm_password"]').type('newSecurePassword456!');

    // Mock incorrect password error with current API structure
    cy.intercept('POST', '/api/user/change-password', {
      statusCode: 400,
      body: {
        error: 'Current password is incorrect',
        field: 'current_password'
      }
    }).as('incorrectPassword');

    cy.get('button').contains('Change Password').click();
    cy.wait('@incorrectPassword');

    // Verify error message
    cy.contains('Current password is incorrect').should('be.visible');
  });

  it('should enforce password complexity requirements', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Test various password complexity scenarios
    const weakPasswords = [
      { pass: '12345678', error: 'Password must contain letters and numbers' },
      { pass: 'password', error: 'Password must contain numbers and special characters' },
      { pass: 'PASSWORD123', error: 'Password must contain lowercase letters' },
      { pass: 'password123', error: 'Password must contain uppercase letters' }
    ];

    weakPasswords.forEach(({ pass, error }) => {
      cy.get('input[name="current_password"]').clear().type('currentPassword123');
      cy.get('input[name="new_password"]').clear().type(pass);
      cy.get('input[name="confirm_password"]').clear().type(pass);
      
      // Should show validation error immediately
      cy.contains(error).should('be.visible');
    });
  });

  it('should handle password change rate limiting', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Fill valid form
    cy.get('input[name="current_password"]').type('currentPassword123');
    cy.get('input[name="new_password"]').type('newSecurePassword456!');
    cy.get('input[name="confirm_password"]').type('newSecurePassword456!');

    // Mock rate limit error with current API structure
    cy.intercept('POST', '/api/user/change-password', {
      statusCode: 429,
      body: {
        error: 'Too many password change attempts. Please wait 5 minutes.',
        retry_after: new Date(Date.now() + 300000).toISOString()
      }
    }).as('rateLimitError');

    cy.get('button').contains('Change Password').click();
    cy.wait('@rateLimitError');

    // Verify rate limit message
    cy.contains('Too many password change attempts').should('be.visible');
    cy.contains('Please wait 5 minutes').should('be.visible');
  });

  it('should show password strength indicator', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Test password strength feedback
    cy.get('input[name="current_password"]').type('currentPassword123');
    
    // Weak password
    cy.get('input[name="new_password"]').type('weak');
    cy.get('[data-testid="password-strength"]').should('contain', 'Weak');
    cy.get('[data-testid="password-strength-bar"]').should('have.class', 'strength-weak');

    // Medium password
    cy.get('input[name="new_password"]').clear().type('Password123');
    cy.get('[data-testid="password-strength"]').should('contain', 'Medium');
    cy.get('[data-testid="password-strength-bar"]').should('have.class', 'strength-medium');

    // Strong password
    cy.get('input[name="new_password"]').clear().type('StrongPassword123!');
    cy.get('[data-testid="password-strength"]').should('contain', 'Strong');
    cy.get('[data-testid="password-strength-bar"]').should('have.class', 'strength-strong');
  });

  it('should handle password history validation', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Try to reuse recent password
    cy.get('input[name="current_password"]').type('currentPassword123');
    cy.get('input[name="new_password"]').type('previousPassword456!');
    cy.get('input[name="confirm_password"]').type('previousPassword456!');

    // Mock password history error with current API structure
    cy.intercept('POST', '/api/user/change-password', {
      statusCode: 400,
      body: {
        error: 'Cannot reuse any of your last 5 passwords',
        field: 'new_password'
      }
    }).as('passwordHistoryError');

    cy.get('button').contains('Change Password').click();
    cy.wait('@passwordHistoryError');

    // Verify history validation error
    cy.contains('Cannot reuse any of your last 5 passwords').should('be.visible');
  });

  it('should require current password for security changes', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Try to submit without current password
    cy.get('input[name="new_password"]').type('newSecurePassword456!');
    cy.get('input[name="confirm_password"]').type('newSecurePassword456!');

    // Change password button should be disabled
    cy.get('button').contains('Change Password').should('be.disabled');

    // Fill current password
    cy.get('input[name="current_password"]').type('currentPassword123');

    // Button should now be enabled
    cy.get('button').contains('Change Password').should('not.be.disabled');
  });

  it('should log password changes for audit', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Successful password change
    cy.get('input[name="current_password"]').type('currentPassword123');
    cy.get('input[name="new_password"]').type('newSecurePassword456!');
    cy.get('input[name="confirm_password"]').type('newSecurePassword456!');

    // Mock successful change with audit log and current API structure
    cy.intercept('POST', '/api/user/change-password', {
      statusCode: 200,
      body: {
        success: true,
        message: 'Password changed successfully',
        audit_id: 'audit-12345'
      }
    }).as('auditedPasswordChange');

    cy.get('button').contains('Change Password').click();
    cy.wait('@auditedPasswordChange');

    // Verify audit notification
    cy.contains('Password changed successfully').should('be.visible');
    cy.contains('This change has been logged for security').should('be.visible');
  });
});