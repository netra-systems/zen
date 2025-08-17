describe('User Security and Privacy Settings', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    cy.visit('/');
  });

  it('should handle password change', () => {
    // Navigate to security settings
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Fill in password change form
    cy.get('input[name="current_password"]').type('currentPassword123');
    cy.get('input[name="new_password"]').type('newSecurePassword456!');
    cy.get('input[name="confirm_password"]').type('newSecurePassword456!');

    // Mock password change endpoint
    cy.intercept('POST', '/api/users/change-password', {
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

    // Test weak password validation
    cy.get('input[name="current_password"]').type('currentPassword123');
    cy.get('input[name="new_password"]').type('weak');
    cy.get('input[name="confirm_password"]').type('weak');

    // Verify validation error
    cy.contains('Password must be at least 8 characters').should('be.visible');
    cy.contains('Password must contain uppercase and lowercase letters').should('be.visible');
    cy.contains('Password must contain at least one number').should('be.visible');
    cy.contains('Password must contain at least one special character').should('be.visible');

    // Test password mismatch
    cy.get('input[name="new_password"]').clear().type('StrongPassword123!');
    cy.get('input[name="confirm_password"]').clear().type('DifferentPassword456!');
    cy.get('button').contains('Change Password').click();

    // Verify mismatch error
    cy.contains('Passwords do not match').should('be.visible');
  });

  it('should manage two-factor authentication', () => {
    // Navigate to security settings
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock 2FA status
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

  it('should disable two-factor authentication', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock 2FA as enabled
    cy.intercept('GET', '/api/users/2fa/status', {
      statusCode: 200,
      body: {
        enabled: true,
        backup_codes_generated: true
      }
    }).as('get2FAStatusEnabled');

    cy.wait('@get2FAStatusEnabled');

    // Test disabling 2FA
    cy.get('button').contains('Disable Two-Factor Authentication').click();

    // Confirm disable
    cy.contains('Are you sure you want to disable two-factor authentication?').should('be.visible');
    cy.contains('This will make your account less secure').should('be.visible');

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

  it('should export and delete user data', () => {
    // Navigate to privacy settings
    cy.visit('/settings');
    cy.get('button').contains('Privacy').click();

    // Request data export
    cy.get('button').contains('Export My Data').click();

    // Mock export request
    cy.intercept('POST', '/api/users/export-data', {
      statusCode: 202,
      body: {
        export_id: 'export-123',
        status: 'processing',
        message: 'Your data export has been initiated. You will receive an email when it is ready.'
      }
    }).as('requestExport');

    cy.wait('@requestExport');

    // Verify export initiated
    cy.contains('Your data export has been initiated').should('be.visible');

    // Check export status
    cy.intercept('GET', '/api/users/export-data/export-123/status', {
      statusCode: 200,
      body: {
        export_id: 'export-123',
        status: 'completed',
        download_url: '/api/users/export-data/export-123/download',
        expires_at: new Date(Date.now() + 86400000).toISOString()
      }
    }).as('exportStatus');

    cy.get('button').contains('Check Export Status').click();
    cy.wait('@exportStatus');

    // Verify download is available
    cy.contains('Your data export is ready').should('be.visible');
    cy.get('a').contains('Download Export').should('have.attr', 'href', '/api/users/export-data/export-123/download');
  });

  it('should handle account deletion', () => {
    cy.visit('/settings');
    cy.get('button').contains('Privacy').click();

    // Test account deletion
    cy.get('button').contains('Delete My Account').click();

    // Verify warning modal
    cy.contains('This action cannot be undone').should('be.visible');
    cy.contains('All your data will be permanently deleted').should('be.visible');
    cy.contains('This includes your profile, API keys, and all associated data').should('be.visible');

    // Type confirmation
    cy.get('input[placeholder="Type DELETE to confirm"]').type('DELETE');

    // Mock deletion endpoint
    cy.intercept('DELETE', '/api/users/account', {
      statusCode: 200,
      body: {
        success: true,
        message: 'Account scheduled for deletion'
      }
    }).as('deleteAccount');

    // Confirm deletion
    cy.get('button').contains('Delete Account').click();
    cy.wait('@deleteAccount');

    // Verify deletion scheduled
    cy.contains('Account scheduled for deletion').should('be.visible');
    cy.contains('You will be logged out shortly').should('be.visible');

    // Verify logout after deletion
    cy.wait(2000);
    cy.url().should('include', '/login');
  });

  it('should manage session and device management', () => {
    // Navigate to security settings
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Mock active sessions
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: {
        sessions: [
          {
            id: 'session-1',
            device_name: 'Chrome on Windows',
            ip_address: '192.168.1.100',
            location: 'New York, US',
            last_active: new Date().toISOString(),
            current: true
          },
          {
            id: 'session-2',
            device_name: 'Safari on iPhone',
            ip_address: '192.168.1.101',
            location: 'New York, US',
            last_active: new Date(Date.now() - 3600000).toISOString(),
            current: false
          },
          {
            id: 'session-3',
            device_name: 'Firefox on Linux',
            ip_address: '192.168.1.102',
            location: 'San Francisco, US',
            last_active: new Date(Date.now() - 86400000).toISOString(),
            current: false
          }
        ]
      }
    }).as('getSessions');

    cy.wait('@getSessions');

    // Verify current session
    cy.contains('Chrome on Windows').parent().should('contain', 'Current Session');
    cy.contains('192.168.1.100').should('be.visible');

    // Verify other sessions
    cy.contains('Safari on iPhone').should('be.visible');
    cy.contains('Firefox on Linux').should('be.visible');
  });

  it('should revoke individual sessions', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Mock sessions
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: {
        sessions: [
          {
            id: 'session-1',
            device_name: 'Chrome on Windows',
            ip_address: '192.168.1.100',
            location: 'New York, US',
            last_active: new Date().toISOString(),
            current: true
          },
          {
            id: 'session-2',
            device_name: 'Safari on iPhone',
            ip_address: '192.168.1.101',
            location: 'New York, US',
            last_active: new Date(Date.now() - 3600000).toISOString(),
            current: false
          }
        ]
      }
    }).as('getSessions');

    cy.wait('@getSessions');

    // Revoke specific session
    cy.contains('Safari on iPhone').parent().find('button').contains('Revoke').click();

    // Mock revoke endpoint
    cy.intercept('DELETE', '/api/users/sessions/session-2', {
      statusCode: 204
    }).as('revokeSession');

    cy.wait('@revokeSession');

    // Verify session removed
    cy.contains('Safari on iPhone').should('not.exist');
    cy.contains('Session revoked successfully').should('be.visible');
  });

  it('should revoke all other sessions', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Mock sessions
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: {
        sessions: [
          {
            id: 'session-1',
            device_name: 'Chrome on Windows',
            current: true
          },
          {
            id: 'session-2',
            device_name: 'Safari on iPhone',
            current: false
          },
          {
            id: 'session-3',
            device_name: 'Firefox on Linux',
            current: false
          }
        ]
      }
    }).as('getSessions');

    cy.wait('@getSessions');

    // Revoke all other sessions
    cy.get('button').contains('Revoke All Other Sessions').click();

    // Confirm action
    cy.contains('This will log you out from all other devices').should('be.visible');

    // Mock revoke all endpoint
    cy.intercept('POST', '/api/users/sessions/revoke-all', {
      statusCode: 200,
      body: {
        revoked_count: 2,
        message: '2 session(s) revoked'
      }
    }).as('revokeAllSessions');

    cy.get('button').contains('Revoke All').click();
    cy.wait('@revokeAllSessions');

    // Verify only current session remains
    cy.contains('Firefox on Linux').should('not.exist');
    cy.contains('Safari on iPhone').should('not.exist');
    cy.contains('Chrome on Windows').should('be.visible');
    cy.contains('2 session(s) revoked').should('be.visible');
  });

  it('should handle security alerts and monitoring', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();

    // Mock security alerts
    cy.intercept('GET', '/api/users/security/alerts', {
      statusCode: 200,
      body: {
        alerts: [
          {
            id: 'alert-1',
            type: 'login_from_new_location',
            message: 'Login from new location: San Francisco, CA',
            timestamp: '2024-12-01T10:00:00Z',
            severity: 'medium',
            resolved: false
          },
          {
            id: 'alert-2',
            type: 'failed_login_attempts',
            message: '5 failed login attempts detected',
            timestamp: '2024-11-30T15:30:00Z',
            severity: 'high',
            resolved: true
          }
        ]
      }
    }).as('getSecurityAlerts');

    cy.get('button').contains('Security Alerts').click();
    cy.wait('@getSecurityAlerts');

    // Verify alerts are displayed
    cy.contains('Login from new location').should('be.visible');
    cy.contains('5 failed login attempts detected').should('be.visible');
    cy.contains('Medium').should('be.visible'); // Severity indicator
    cy.contains('Resolved').should('be.visible');

    // Test marking alert as resolved
    cy.get('[data-alert-id="alert-1"] button').contains('Mark as Resolved').click();

    cy.intercept('PATCH', '/api/users/security/alerts/alert-1', {
      statusCode: 200,
      body: { resolved: true }
    }).as('resolveAlert');

    cy.wait('@resolveAlert');
    cy.contains('Alert marked as resolved').should('be.visible');
  });
});
