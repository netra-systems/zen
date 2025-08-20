/**
 * User 2FA Backup Codes E2E Tests
 * Split from user-2fa-management.cy.ts for 450-line compliance
 * 
 * BVJ: Enterprise segment - Backup codes = account recovery = business continuity
 * Value Impact: Recovery mechanisms = reduced support burden
 */

describe('User 2FA Backup Codes Management', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    cy.visit('/');
  });

  it('should show 2FA status and recovery options', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock enabled 2FA with recovery info
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: {
        enabled: true,
        backup_codes_generated: true,
        backup_codes_used: 2,
        backup_codes_remaining: 3,
        last_backup_code_used: '2024-12-01T10:00:00Z'
      }
    }).as('get2FAStatusWithRecovery');

    cy.wait('@get2FAStatusWithRecovery');

    // Verify 2FA status display
    cy.contains('Two-Factor Authentication: Enabled').should('be.visible');
    cy.contains('3 backup codes remaining').should('be.visible');
    cy.contains('Last backup code used: December 1').should('be.visible');

    // Verify recovery options
    cy.get('button').contains('View Backup Codes').should('be.visible');
    cy.get('button').contains('Regenerate Backup Codes').should('be.visible');
  });

  it('should regenerate 2FA backup codes', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock 2FA enabled status
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: {
        enabled: true,
        backup_codes_generated: true
      }
    }).as('get2FAEnabled');

    cy.wait('@get2FAEnabled');

    // Regenerate backup codes
    cy.get('button').contains('Regenerate Backup Codes').click();

    // Confirm regeneration
    cy.contains('This will invalidate your existing backup codes').should('be.visible');

    // Mock regeneration endpoint
    cy.intercept('POST', '/api/users/2fa/regenerate-codes', {
      statusCode: 200,
      body: {
        backup_codes: [
          'new-backup-1',
          'new-backup-2',
          'new-backup-3',
          'new-backup-4',
          'new-backup-5'
        ]
      }
    }).as('regenerateCodes');

    cy.get('button').contains('Regenerate').click();
    cy.wait('@regenerateCodes');

    // Verify new codes are displayed
    cy.contains('new-backup-1').should('be.visible');
    cy.contains('Backup codes regenerated successfully').should('be.visible');
  });

  it('should warn when backup codes are running low', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock low backup codes
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: {
        enabled: true,
        backup_codes_generated: true,
        backup_codes_remaining: 1
      }
    }).as('getLowBackupCodes');

    cy.wait('@getLowBackupCodes');

    // Verify low backup codes warning
    cy.contains('Only 1 backup code remaining').should('be.visible');
    cy.contains('Consider regenerating backup codes').should('be.visible');
    cy.get('[data-testid="backup-codes-warning"]').should('have.class', 'warning');
  });

  it('should display backup codes securely', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock 2FA enabled
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: {
        enabled: true,
        backup_codes_generated: true
      }
    }).as('get2FAEnabled');

    cy.wait('@get2FAEnabled');

    // View backup codes
    cy.get('button').contains('View Backup Codes').click();

    // Mock backup codes endpoint
    cy.intercept('GET', '/api/users/2fa/backup-codes', {
      statusCode: 200,
      body: {
        codes: [
          'backup-111111',
          'backup-222222',
          'backup-333333',
          'backup-444444',
          'backup-555555'
        ]
      }
    }).as('getBackupCodes');

    cy.wait('@getBackupCodes');

    // Verify codes are displayed
    cy.contains('backup-111111').should('be.visible');
    cy.contains('backup-222222').should('be.visible');

    // Verify security warnings
    cy.contains('Store these codes in a secure location').should('be.visible');
    cy.contains('Each code can only be used once').should('be.visible');

    // Verify download/print options
    cy.get('button').contains('Download Codes').should('be.visible');
    cy.get('button').contains('Print Codes').should('be.visible');
  });

  it('should handle backup codes download', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock enabled 2FA and codes
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: { enabled: true, backup_codes_generated: true }
    }).as('get2FAEnabled');

    cy.intercept('GET', '/api/users/2fa/backup-codes/download', {
      statusCode: 200,
      headers: { 'Content-Type': 'text/plain' },
      body: 'code-1\ncode-2\ncode-3'
    }).as('downloadCodes');

    cy.wait('@get2FAEnabled');
    cy.get('button').contains('Download Codes').click();
    cy.wait('@downloadCodes');

    cy.contains('Backup codes downloaded').should('be.visible');
  });

  it('should handle backup code regeneration confirmation', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock enabled 2FA
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: { enabled: true, backup_codes_generated: true }
    }).as('get2FAEnabled');

    cy.wait('@get2FAEnabled');

    // Start regeneration
    cy.get('button').contains('Regenerate Backup Codes').click();

    // Verify confirmation details
    cy.contains('Regenerate Backup Codes').should('be.visible');
    cy.contains('This will invalidate your existing backup codes').should('be.visible');
    cy.contains('Any unused codes will no longer work').should('be.visible');
    cy.contains('You will receive 5 new backup codes').should('be.visible');

    // Cancel regeneration
    cy.get('button').contains('Cancel').click();
    cy.contains('Regenerate Backup Codes').should('not.exist');
  });

  it('should handle backup codes not yet generated', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock 2FA enabled but no backup codes
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: {
        enabled: true,
        backup_codes_generated: false
      }
    }).as('get2FANoCodes');

    cy.wait('@get2FANoCodes');

    // Verify backup codes setup prompt
    cy.contains('Backup codes not yet generated').should('be.visible');
    cy.contains('Generate backup codes for account recovery').should('be.visible');
    cy.get('button').contains('Generate Backup Codes').should('be.visible');

    // Generate initial backup codes
    cy.intercept('POST', '/api/users/2fa/generate-codes', {
      statusCode: 200,
      body: {
        codes: ['first-1', 'first-2', 'first-3', 'first-4', 'first-5']
      }
    }).as('generateInitialCodes');

    cy.get('button').contains('Generate Backup Codes').click();
    cy.wait('@generateInitialCodes');

    // Verify codes generated
    cy.contains('first-1').should('be.visible');
    cy.contains('Backup codes generated successfully').should('be.visible');
  });

});