/**
 * User 2FA Setup E2E Tests  
 * Split from user-2fa-management.cy.ts for 450-line compliance
 * 
 * BVJ: Enterprise segment - 2FA setup drives security compliance
 * Value Impact: Authentication security = Enterprise trust
 */

describe('User Two-Factor Authentication Setup', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    cy.visit('/');
  });

  it('should enable two-factor authentication', () => {
    // Navigate to security settings
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock 2FA status - disabled
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: {
        enabled: false,
        backup_codes_generated: false
      }
    }).as('get2FAStatus');

    cy.wait('@get2FAStatus');

    // Enable 2FA
    cy.get('button').contains('Enable Two-Factor Authentication').click();

    // Mock 2FA setup
    cy.intercept('POST', '/api/users/2fa/setup', {
      statusCode: 200,
      body: {
        secret: 'JBSWY3DPEHPK3PXP',
        qr_code: 'data:image/png;base64,iVBORw0KGgoAAAANS...',
        backup_codes: [
          'backup-code-1',
          'backup-code-2',
          'backup-code-3',
          'backup-code-4',
          'backup-code-5'
        ]
      }
    }).as('setup2FA');

    cy.wait('@setup2FA');

    // Verify QR code is displayed
    cy.get('img[alt="2FA QR Code"]').should('be.visible');
    cy.contains('JBSWY3DPEHPK3PXP').should('be.visible');

    // Verify backup codes
    cy.contains('Backup Codes').should('be.visible');
    cy.contains('backup-code-1').should('be.visible');

    // Enter verification code
    cy.get('input[name="verification_code"]').type('123456');

    // Mock verification
    cy.intercept('POST', '/api/users/2fa/verify', {
      statusCode: 200,
      body: {
        success: true,
        message: 'Two-factor authentication enabled successfully'
      }
    }).as('verify2FA');

    // Complete setup
    cy.get('button').contains('Verify and Enable').click();
    cy.wait('@verify2FA');

    // Verify success
    cy.contains('Two-factor authentication enabled successfully').should('be.visible');

    // Verify 2FA is now shown as enabled
    cy.contains('Two-Factor Authentication: Enabled').should('be.visible');
  });

  it('should handle invalid 2FA verification codes', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock 2FA status and setup
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: { enabled: false, backup_codes_generated: false }
    }).as('get2FAStatus');

    cy.intercept('POST', '/api/users/2fa/setup', {
      statusCode: 200,
      body: {
        secret: 'JBSWY3DPEHPK3PXP',
        qr_code: 'data:image/png;base64,test...',
        backup_codes: ['backup-code-1']
      }
    }).as('setup2FA');

    cy.wait('@get2FAStatus');
    cy.get('button').contains('Enable Two-Factor Authentication').click();
    cy.wait('@setup2FA');

    // Enter invalid verification code
    cy.get('input[name="verification_code"]').type('000000');

    // Mock verification failure
    cy.intercept('POST', '/api/users/2fa/verify', {
      statusCode: 400,
      body: {
        error: 'Invalid verification code',
        field: 'verification_code'
      }
    }).as('invalidVerify2FA');

    cy.get('button').contains('Verify and Enable').click();
    cy.wait('@invalidVerify2FA');

    // Verify error message
    cy.contains('Invalid verification code').should('be.visible');
  });

  it('should test 2FA code verification during setup', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Setup 2FA
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: { enabled: false }
    }).as('get2FAStatus');

    cy.intercept('POST', '/api/users/2fa/setup', {
      statusCode: 200,
      body: {
        secret: 'TESTTEST',
        qr_code: 'data:image/png;base64,test',
        backup_codes: ['test-1', 'test-2']
      }
    }).as('setup2FA');

    cy.wait('@get2FAStatus');
    cy.get('button').contains('Enable Two-Factor Authentication').click();
    cy.wait('@setup2FA');

    // Test verification code validation
    cy.get('input[name="verification_code"]').type('12');
    cy.contains('Code must be 6 digits').should('be.visible');

    cy.get('input[name="verification_code"]').clear().type('abcdef');
    cy.contains('Code must contain only numbers').should('be.visible');

    // Valid format should clear errors
    cy.get('input[name="verification_code"]').clear().type('123456');
    cy.contains('Code must be 6 digits').should('not.exist');
  });

  it('should handle 2FA setup errors gracefully', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock status check
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: { enabled: false }
    }).as('get2FAStatus');

    cy.wait('@get2FAStatus');

    // Mock setup error
    cy.intercept('POST', '/api/users/2fa/setup', {
      statusCode: 500,
      body: {
        error: 'Unable to generate 2FA secret. Please try again.'
      }
    }).as('setup2FAError');

    cy.get('button').contains('Enable Two-Factor Authentication').click();
    cy.wait('@setup2FAError');

    // Verify error handling
    cy.contains('Unable to generate 2FA secret').should('be.visible');
    cy.get('button').contains('Try Again').should('be.visible');
  });

  it('should disable two-factor authentication', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock 2FA status - enabled
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: {
        enabled: true,
        backup_codes_generated: true
      }
    }).as('get2FAEnabledStatus');

    cy.wait('@get2FAEnabledStatus');

    // Test disabling 2FA
    cy.get('button').contains('Disable Two-Factor Authentication').click();

    // Confirm disable
    cy.contains('Are you sure you want to disable two-factor authentication?').should('be.visible');

    // Mock disable endpoint
    cy.intercept('POST', '/api/users/2fa/disable', {
      statusCode: 200,
      body: {
        success: true,
        message: 'Two-factor authentication disabled'
      }
    }).as('disable2FA');

    cy.get('button').contains('Disable').click();
    cy.wait('@disable2FA');

    // Verify 2FA is disabled
    cy.contains('Two-Factor Authentication: Disabled').should('be.visible');
  });

  it('should handle 2FA disable confirmation', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock enabled 2FA
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: { enabled: true, backup_codes_generated: true }
    }).as('get2FAEnabled');

    cy.wait('@get2FAEnabled');

    // Start disable process
    cy.get('button').contains('Disable Two-Factor Authentication').click();

    // Verify confirmation modal details
    cy.contains('Disable Two-Factor Authentication').should('be.visible');
    cy.contains('This will reduce your account security').should('be.visible');
    cy.contains('Your backup codes will be invalidated').should('be.visible');

    // Cancel should close modal
    cy.get('button').contains('Cancel').click();
    cy.contains('Disable Two-Factor Authentication').should('not.exist');

    // Still enabled
    cy.contains('Two-Factor Authentication: Enabled').should('be.visible');
  });

  it('should validate 2FA requirements before enabling', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock 2FA status check
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: { enabled: false }
    }).as('get2FAStatus');

    cy.wait('@get2FAStatus');

    // Verify requirements are displayed
    cy.contains('Requirements for 2FA').should('be.visible');
    cy.contains('Authenticator app (Google Authenticator, Authy, etc.)').should('be.visible');
    cy.contains('Active email address for backup codes').should('be.visible');
    cy.contains('Secure storage for backup codes').should('be.visible');

    // Verify setup prerequisites
    cy.get('input[name="acknowledge_requirements"]').check();
    cy.get('button').contains('Enable Two-Factor Authentication').should('not.be.disabled');
  });
});