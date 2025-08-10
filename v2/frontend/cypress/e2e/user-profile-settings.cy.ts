import { WebSocketMessage } from '@/types/chat';

describe('User Profile and Settings Management', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    cy.visit('/');
  });

  it('should display and update user profile information', () => {
    // Navigate to profile settings
    cy.get('button[aria-label="Toggle user menu"]').click();
    cy.contains('Settings').click();

    // Verify profile information is displayed
    cy.get('input[name="full_name"]').should('have.value', 'Test User');
    cy.get('input[name="email"]').should('have.value', 'test@netra.ai');
    cy.contains('Member since January 1, 2024').should('be.visible');

    // Update profile information
    const newName = 'Updated Test User';
    cy.get('input[name="full_name"]').clear().type(newName);

    // Mock profile update endpoint
    cy.intercept('PATCH', '/api/users/profile', {
      statusCode: 200,
      body: {
        id: 1,
        email: 'test@netra.ai',
        full_name: newName,
        created_at: '2024-01-01T00:00:00Z',
        avatar_url: null
      }
    }).as('updateProfile');

    // Save changes
    cy.get('button').contains('Save Profile').click();
    cy.wait('@updateProfile');

    // Verify success message
    cy.contains('Profile updated successfully').should('be.visible');

    // Verify updated name in header
    cy.get('button[aria-label="Toggle user menu"]').click();
    cy.contains(newName).should('be.visible');
  });

  it('should manage API keys and credentials', () => {
    // Navigate to API settings
    cy.get('button[aria-label="Toggle user menu"]').click();
    cy.contains('Settings').click();
    cy.get('button').contains('API Keys').click();

    // Mock API keys endpoint
    cy.intercept('GET', '/api/users/api-keys', {
      statusCode: 200,
      body: {
        keys: [
          {
            id: 'key-1',
            name: 'Production Key',
            provider: 'openai',
            last_used: '2024-12-01T10:00:00Z',
            created_at: '2024-11-01T00:00:00Z',
            masked_value: 'sk-...abc123'
          },
          {
            id: 'key-2',
            name: 'Development Key',
            provider: 'anthropic',
            last_used: null,
            created_at: '2024-11-15T00:00:00Z',
            masked_value: 'sk-ant-...xyz789'
          }
        ]
      }
    }).as('getApiKeys');

    cy.wait('@getApiKeys');

    // Verify existing keys are displayed
    cy.contains('Production Key').should('be.visible');
    cy.contains('OpenAI').should('be.visible');
    cy.contains('sk-...abc123').should('be.visible');
    cy.contains('Last used: December 1, 2024').should('be.visible');

    cy.contains('Development Key').should('be.visible');
    cy.contains('Anthropic').should('be.visible');
    cy.contains('Never used').should('be.visible');

    // Add new API key
    cy.get('button').contains('Add API Key').click();
    
    // Fill in new key details
    cy.get('input[name="key_name"]').type('Test API Key');
    cy.get('select[name="provider"]').select('openai');
    cy.get('input[name="api_key"]').type('sk-test-key-12345');

    // Mock add key endpoint
    cy.intercept('POST', '/api/users/api-keys', {
      statusCode: 201,
      body: {
        id: 'key-3',
        name: 'Test API Key',
        provider: 'openai',
        last_used: null,
        created_at: new Date().toISOString(),
        masked_value: 'sk-...12345'
      }
    }).as('addApiKey');

    // Save new key
    cy.get('button').contains('Save Key').click();
    cy.wait('@addApiKey');

    // Verify success message
    cy.contains('API key added successfully').should('be.visible');

    // Verify new key appears in list
    cy.contains('Test API Key').should('be.visible');

    // Test key validation
    cy.get('button').contains('Test Key').last().click();

    // Mock validation endpoint
    cy.intercept('POST', '/api/users/api-keys/key-3/validate', {
      statusCode: 200,
      body: {
        valid: true,
        model_access: ['gpt-4', 'gpt-3.5-turbo'],
        rate_limit: '10000 requests/day'
      }
    }).as('validateKey');

    cy.wait('@validateKey');

    // Verify validation result
    cy.contains('Key is valid').should('be.visible');
    cy.contains('Models: gpt-4, gpt-3.5-turbo').should('be.visible');
    cy.contains('Rate limit: 10000 requests/day').should('be.visible');

    // Delete API key
    cy.contains('Test API Key').parent().find('button[aria-label="Delete key"]').click();
    
    // Confirm deletion
    cy.contains('Are you sure you want to delete this API key?').should('be.visible');

    // Mock delete endpoint
    cy.intercept('DELETE', '/api/users/api-keys/key-3', {
      statusCode: 204
    }).as('deleteApiKey');

    cy.get('button').contains('Delete').click();
    cy.wait('@deleteApiKey');

    // Verify key is removed
    cy.contains('Test API Key').should('not.exist');
  });

  it('should manage notification preferences', () => {
    // Navigate to notification settings
    cy.get('button[aria-label="Toggle user menu"]').click();
    cy.contains('Settings').click();
    cy.get('button').contains('Notifications').click();

    // Mock notifications settings endpoint
    cy.intercept('GET', '/api/users/notifications/settings', {
      statusCode: 200,
      body: {
        email_notifications: {
          optimization_complete: true,
          weekly_reports: true,
          system_updates: false,
          marketing: false
        },
        in_app_notifications: {
          agent_updates: true,
          mentions: true,
          thread_replies: true
        },
        push_notifications: {
          enabled: false,
          critical_only: false
        }
      }
    }).as('getNotificationSettings');

    cy.wait('@getNotificationSettings');

    // Verify current settings
    cy.get('input[name="email_optimization_complete"]').should('be.checked');
    cy.get('input[name="email_weekly_reports"]').should('be.checked');
    cy.get('input[name="email_system_updates"]').should('not.be.checked');
    cy.get('input[name="in_app_agent_updates"]').should('be.checked');

    // Update notification preferences
    cy.get('input[name="email_system_updates"]').check();
    cy.get('input[name="email_weekly_reports"]').uncheck();
    cy.get('input[name="push_enabled"]').check();

    // Mock update endpoint
    cy.intercept('PATCH', '/api/users/notifications/settings', {
      statusCode: 200,
      body: {
        email_notifications: {
          optimization_complete: true,
          weekly_reports: false,
          system_updates: true,
          marketing: false
        },
        in_app_notifications: {
          agent_updates: true,
          mentions: true,
          thread_replies: true
        },
        push_notifications: {
          enabled: true,
          critical_only: false
        }
      }
    }).as('updateNotifications');

    // Save changes
    cy.get('button').contains('Save Preferences').click();
    cy.wait('@updateNotifications');

    // Verify success message
    cy.contains('Notification preferences updated').should('be.visible');

    // Test notification
    cy.get('button').contains('Send Test Notification').click();

    // Mock test notification
    cy.intercept('POST', '/api/users/notifications/test', {
      statusCode: 200,
      body: {
        sent: true,
        channels: ['email', 'in_app', 'push']
      }
    }).as('testNotification');

    cy.wait('@testNotification');

    // Verify test notification sent
    cy.contains('Test notification sent to all enabled channels').should('be.visible');
  });

  it('should manage application preferences and themes', () => {
    // Navigate to preferences
    cy.get('button[aria-label="Toggle user menu"]').click();
    cy.contains('Settings').click();
    cy.get('button').contains('Preferences').click();

    // Mock preferences endpoint
    cy.intercept('GET', '/api/users/preferences', {
      statusCode: 200,
      body: {
        theme: 'light',
        language: 'en',
        timezone: 'America/New_York',
        date_format: 'MM/DD/YYYY',
        default_model: 'claude-3-opus',
        auto_save_interval: 30,
        show_raw_data: false,
        enable_shortcuts: true,
        compact_view: false
      }
    }).as('getPreferences');

    cy.wait('@getPreferences');

    // Test theme switching
    cy.get('select[name="theme"]').should('have.value', 'light');
    cy.get('select[name="theme"]').select('dark');

    // Verify theme is applied immediately
    cy.get('body').should('have.class', 'dark');

    // Update other preferences
    cy.get('select[name="default_model"]').select('gpt-4');
    cy.get('input[name="auto_save_interval"]').clear().type('60');
    cy.get('input[name="show_raw_data"]').check();
    cy.get('input[name="compact_view"]').check();

    // Mock update preferences
    cy.intercept('PATCH', '/api/users/preferences', {
      statusCode: 200,
      body: {
        theme: 'dark',
        language: 'en',
        timezone: 'America/New_York',
        date_format: 'MM/DD/YYYY',
        default_model: 'gpt-4',
        auto_save_interval: 60,
        show_raw_data: true,
        enable_shortcuts: true,
        compact_view: true
      }
    }).as('updatePreferences');

    // Save preferences
    cy.get('button').contains('Save Preferences').click();
    cy.wait('@updatePreferences');

    // Verify preferences are applied
    cy.contains('Preferences saved successfully').should('be.visible');

    // Navigate back to chat to verify compact view
    cy.visit('/chat');
    cy.get('.chat-container').should('have.class', 'compact');

    // Verify default model is selected
    cy.get('select[name="model"]').should('have.value', 'gpt-4');
  });

  it('should handle password change', () => {
    // Navigate to security settings
    cy.get('button[aria-label="Toggle user menu"]').click();
    cy.contains('Settings').click();
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

    // Test password validation
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

  it('should manage two-factor authentication', () => {
    // Navigate to security settings
    cy.get('button[aria-label="Toggle user menu"]').click();
    cy.contains('Settings').click();
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

  it('should export and delete user data', () => {
    // Navigate to privacy settings
    cy.get('button[aria-label="Toggle user menu"]').click();
    cy.contains('Settings').click();
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

    // Test account deletion
    cy.get('button').contains('Delete My Account').click();

    // Verify warning modal
    cy.contains('This action cannot be undone').should('be.visible');
    cy.contains('All your data will be permanently deleted').should('be.visible');

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
    cy.get('button[aria-label="Toggle user menu"]').click();
    cy.contains('Settings').click();
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

    // Revoke specific session
    cy.contains('Safari on iPhone').parent().find('button').contains('Revoke').click();

    // Mock revoke endpoint
    cy.intercept('DELETE', '/api/users/sessions/session-2', {
      statusCode: 204
    }).as('revokeSession');

    cy.wait('@revokeSession');

    // Verify session removed
    cy.contains('Safari on iPhone').should('not.exist');

    // Revoke all other sessions
    cy.get('button').contains('Revoke All Other Sessions').click();

    // Confirm action
    cy.contains('This will log you out from all other devices').should('be.visible');

    // Mock revoke all endpoint
    cy.intercept('POST', '/api/users/sessions/revoke-all', {
      statusCode: 200,
      body: {
        revoked_count: 1,
        message: '1 session(s) revoked'
      }
    }).as('revokeAllSessions');

    cy.get('button').contains('Revoke All').click();
    cy.wait('@revokeAllSessions');

    // Verify only current session remains
    cy.contains('Firefox on Linux').should('not.exist');
    cy.contains('Chrome on Windows').should('be.visible');
    cy.contains('1 session(s) revoked').should('be.visible');
  });
});