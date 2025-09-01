/// <reference types="cypress" />

/**
 * User Notifications & Preferences E2E Tests
 * Updated for current system implementation:
 * - Auth endpoints: /auth/config, /auth/me, /auth/verify, /auth/refresh
 * - Current token structure: jwt_token, refresh_token, user
 * - API endpoints: /api/user/* for user management
 * - Circuit breaker integration for resilient API calls
 * 
 * BVJ: Growth & Enterprise - Personalized preferences drive user engagement
 * Value Impact: Customization options reduce churn and increase satisfaction
 */

describe('User Notifications & Preferences', () => {
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

  it('should manage notification preferences', () => {
    // Navigate to notification settings
    cy.visit('/settings');
    cy.get('button').contains('Notifications').click();

    // Mock notifications settings endpoint with current API structure
    cy.intercept('GET', '/api/user/notifications/settings', {
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

    // Mock update endpoint with current API structure
    cy.intercept('PATCH', '/api/user/notifications/settings', {
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
  });

  it('should send test notifications', () => {
    cy.visit('/settings');
    cy.get('button').contains('Notifications').click();

    // Mock settings load with current API structure
    cy.intercept('GET', '/api/user/notifications/settings', {
      statusCode: 200,
      body: {
        email_notifications: { optimization_complete: true },
        in_app_notifications: { agent_updates: true },
        push_notifications: { enabled: true }
      }
    }).as('getSettings');

    cy.wait('@getSettings');

    // Test notification
    cy.get('button').contains('Send Test Notification').click();

    // Mock test notification with current API structure
    cy.intercept('POST', '/api/user/notifications/test', {
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
    cy.visit('/settings');
    cy.get('button').contains('Preferences').click();

    // Mock preferences endpoint with current API structure
    cy.intercept('GET', '/api/user/preferences', {
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

    // Mock update preferences with current API structure
    cy.intercept('PATCH', '/api/user/preferences', {
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
  });

  it('should validate preference values', () => {
    cy.visit('/settings');
    cy.get('button').contains('Preferences').click();

    // Mock initial preferences with current API structure
    cy.intercept('GET', '/api/user/preferences', {
      statusCode: 200,
      body: {
        auto_save_interval: 30,
        theme: 'light'
      }
    }).as('getInitialPrefs');

    cy.wait('@getInitialPrefs');

    // Test invalid auto-save interval
    cy.get('input[name="auto_save_interval"]').clear().type('0');
    cy.get('button').contains('Save Preferences').click();
    cy.contains('Auto-save interval must be at least 5 seconds').should('be.visible');

    // Test maximum interval
    cy.get('input[name="auto_save_interval"]').clear().type('3600');
    cy.get('button').contains('Save Preferences').click();
    cy.contains('Auto-save interval cannot exceed 1 hour').should('be.visible');
  });

  it('should sync preferences across tabs', () => {
    cy.visit('/settings');
    cy.get('button').contains('Preferences').click();

    // Mock preferences load with current API structure
    cy.intercept('GET', '/api/user/preferences', {
      statusCode: 200,
      body: { theme: 'light', compact_view: false }
    }).as('getPrefs');

    cy.wait('@getPrefs');

    // Change theme
    cy.get('select[name="theme"]').select('dark');

    // Mock successful update with current API structure
    cy.intercept('PATCH', '/api/user/preferences', {
      statusCode: 200,
      body: { theme: 'dark', compact_view: false }
    }).as('updateTheme');

    cy.get('button').contains('Save Preferences').click();
    cy.wait('@updateTheme');

    // Simulate storage event (preference sync)
    cy.window().then((win) => {
      win.dispatchEvent(new StorageEvent('storage', {
        key: 'user_preferences',
        newValue: JSON.stringify({ theme: 'dark', compact_view: false })
      }));
    });

    // Verify theme applied
    cy.get('body').should('have.class', 'dark');
  });

  it('should handle notification permission requests', () => {
    cy.visit('/settings');
    cy.get('button').contains('Notifications').click();

    // Mock Notification API
    cy.window().then((win) => {
      // Mock permission request
      const originalNotification = win.Notification;
      win.Notification = {
        permission: 'default',
        requestPermission: cy.stub().resolves('granted')
      } as any;

      // Enable push notifications
      cy.get('input[name="push_enabled"]').check();

      // Should trigger permission request
      cy.wrap(win.Notification.requestPermission).should('have.been.called');

      // Restore original
      win.Notification = originalNotification;
    });
  });

  it('should export user preferences', () => {
    cy.visit('/settings');
    cy.get('button').contains('Preferences').click();

    // Export preferences
    cy.get('button').contains('Export Preferences').click();

    // Mock export with current API structure
    cy.intercept('GET', '/api/user/preferences/export', {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Content-Disposition': 'attachment; filename=preferences.json'
      },
      body: {
        theme: 'dark',
        language: 'en',
        notifications: { email: true, push: false }
      }
    }).as('exportPrefs');

    cy.wait('@exportPrefs');

    cy.contains('Preferences exported successfully').should('be.visible');
  });
});