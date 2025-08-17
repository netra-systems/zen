describe('User Notifications and Preferences', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    cy.visit('/');
  });

  it('should manage notification preferences', () => {
    // Navigate to notification settings
    cy.visit('/settings');
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
  });

  it('should test notification delivery', () => {
    cy.visit('/settings');
    cy.get('button').contains('Notifications').click();

    // Mock notification settings
    cy.intercept('GET', '/api/users/notifications/settings', {
      statusCode: 200,
      body: {
        email_notifications: { optimization_complete: true },
        in_app_notifications: { agent_updates: true },
        push_notifications: { enabled: true }
      }
    }).as('getNotificationSettings');

    cy.wait('@getNotificationSettings');

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
    cy.contains('Email: ✓ Delivered').should('be.visible');
    cy.contains('In-app: ✓ Delivered').should('be.visible');
    cy.contains('Push: ✓ Delivered').should('be.visible');
  });

  it('should manage application preferences and themes', () => {
    // Navigate to preferences
    cy.visit('/settings');
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

  it('should handle timezone and localization preferences', () => {
    cy.visit('/settings');
    cy.get('button').contains('Preferences').click();

    // Test timezone selection
    const timezones = [
      { value: 'America/New_York', label: 'Eastern Time (EST/EDT)' },
      { value: 'America/Los_Angeles', label: 'Pacific Time (PST/PDT)' },
      { value: 'Europe/London', label: 'Greenwich Mean Time (GMT)' },
      { value: 'Asia/Tokyo', label: 'Japan Standard Time (JST)' }
    ];

    timezones.forEach(timezone => {
      cy.get('select[name="timezone"]').select(timezone.value);
      cy.get('select[name="timezone"] option:selected').should('contain', timezone.label);
    });

    // Test date format options
    const dateFormats = [
      { value: 'MM/DD/YYYY', example: '12/31/2024' },
      { value: 'DD/MM/YYYY', example: '31/12/2024' },
      { value: 'YYYY-MM-DD', example: '2024-12-31' },
      { value: 'DD MMM YYYY', example: '31 Dec 2024' }
    ];

    dateFormats.forEach(format => {
      cy.get('select[name="date_format"]').select(format.value);
      cy.contains(`Example: ${format.example}`).should('be.visible');
    });

    // Test language selection
    cy.get('select[name="language"]').select('es');
    cy.contains('Idioma cambiado a Español').should('be.visible'); // Success message in Spanish
  });

  it('should manage keyboard shortcuts preferences', () => {
    cy.visit('/settings');
    cy.get('button').contains('Preferences').click();
    cy.get('button').contains('Keyboard Shortcuts').click();

    // Mock shortcuts settings
    cy.intercept('GET', '/api/users/preferences/shortcuts', {
      statusCode: 200,
      body: {
        enabled: true,
        custom_shortcuts: {
          'new_chat': 'Ctrl+N',
          'toggle_sidebar': 'Ctrl+B',
          'search': 'Ctrl+K',
          'send_message': 'Ctrl+Enter'
        }
      }
    }).as('getShortcuts');

    cy.wait('@getShortcuts');

    // Verify current shortcuts
    cy.contains('New Chat: Ctrl+N').should('be.visible');
    cy.contains('Toggle Sidebar: Ctrl+B').should('be.visible');
    cy.contains('Search: Ctrl+K').should('be.visible');
    cy.contains('Send Message: Ctrl+Enter').should('be.visible');

    // Test customizing a shortcut
    cy.get('button[data-shortcut="new_chat"]').contains('Change').click();
    cy.get('input[name="shortcut_input"]').type('{cmd}T');
    cy.get('button').contains('Save Shortcut').click();

    // Mock update shortcut
    cy.intercept('PATCH', '/api/users/preferences/shortcuts', {
      statusCode: 200,
      body: {
        enabled: true,
        custom_shortcuts: {
          'new_chat': 'Cmd+T',
          'toggle_sidebar': 'Ctrl+B',
          'search': 'Ctrl+K',
          'send_message': 'Ctrl+Enter'
        }
      }
    }).as('updateShortcuts');

    cy.wait('@updateShortcuts');

    // Verify shortcut was updated
    cy.contains('New Chat: Cmd+T').should('be.visible');
    cy.contains('Shortcut updated successfully').should('be.visible');
  });

  it('should handle accessibility preferences', () => {
    cy.visit('/settings');
    cy.get('button').contains('Preferences').click();
    cy.get('button').contains('Accessibility').click();

    // Mock accessibility settings
    cy.intercept('GET', '/api/users/preferences/accessibility', {
      statusCode: 200,
      body: {
        high_contrast: false,
        large_text: false,
        reduced_motion: false,
        screen_reader_optimized: false,
        focus_indicators: true
      }
    }).as('getAccessibilitySettings');

    cy.wait('@getAccessibilitySettings');

    // Test accessibility options
    cy.get('input[name="high_contrast"]').check();
    cy.get('body').should('have.class', 'high-contrast');

    cy.get('input[name="large_text"]').check();
    cy.get('body').should('have.class', 'large-text');

    cy.get('input[name="reduced_motion"]').check();
    cy.get('body').should('have.class', 'reduced-motion');

    // Mock save accessibility settings
    cy.intercept('PATCH', '/api/users/preferences/accessibility', {
      statusCode: 200,
      body: {
        high_contrast: true,
        large_text: true,
        reduced_motion: true,
        screen_reader_optimized: false,
        focus_indicators: true
      }
    }).as('updateAccessibilitySettings');

    cy.get('button').contains('Save Accessibility Settings').click();
    cy.wait('@updateAccessibilitySettings');

    // Verify success message
    cy.contains('Accessibility settings updated').should('be.visible');
  });
});
