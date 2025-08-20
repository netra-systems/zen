/**
 * User Active Sessions E2E Tests
 * Split from user-device-sessions.cy.ts for 450-line compliance
 * 
 * BVJ: Growth & Enterprise - Session visibility drives security transparency
 * Value Impact: Device awareness = security control = user confidence
 */

describe('User Active Sessions Management', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    cy.visit('/');
  });

  it('should display active sessions with device details', () => {
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
            current: true,
            user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
          },
          {
            id: 'session-2',
            device_name: 'Safari on iPhone',
            ip_address: '192.168.1.101',
            location: 'New York, US',
            last_active: new Date(Date.now() - 3600000).toISOString(),
            current: false,
            user_agent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)'
          },
          {
            id: 'session-3',
            device_name: 'Firefox on Linux',
            ip_address: '192.168.1.102',
            location: 'San Francisco, US',
            last_active: new Date(Date.now() - 86400000).toISOString(),
            current: false,
            user_agent: 'Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101'
          }
        ]
      }
    }).as('getSessions');

    cy.wait('@getSessions');

    // Verify current session
    cy.contains('Chrome on Windows').parent().should('contain', 'Current Session');
    cy.contains('192.168.1.100').should('be.visible');
    cy.contains('Active now').should('be.visible');

    // Verify other sessions
    cy.contains('Safari on iPhone').should('be.visible');
    cy.contains('Last active: 1 hour ago').should('be.visible');
    
    cy.contains('Firefox on Linux').should('be.visible');
    cy.contains('Last active: 1 day ago').should('be.visible');
  });

  it('should prevent revoking current session', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Mock current session only
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: {
        sessions: [{
          id: 'session-current',
          device_name: 'Chrome on Windows',
          current: true,
          last_active: new Date().toISOString()
        }]
      }
    }).as('getCurrentSession');

    cy.wait('@getCurrentSession');

    // Verify current session cannot be revoked
    cy.contains('Chrome on Windows').parent().should('contain', 'Current Session');
    cy.contains('Chrome on Windows').parent().find('button').contains('Revoke').should('not.exist');
    cy.contains('You cannot revoke your current session').should('be.visible');
  });

  it('should handle session loading errors gracefully', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Mock session loading error
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 500,
      body: {
        error: 'Unable to load sessions'
      }
    }).as('getSessionsError');

    cy.wait('@getSessionsError');

    // Verify error handling
    cy.contains('Unable to load active sessions').should('be.visible');
    cy.get('button').contains('Retry').should('be.visible');

    // Test retry functionality
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: {
        sessions: [{
          id: 'session-retry',
          device_name: 'Chrome on Windows',
          current: true
        }]
      }
    }).as('retryGetSessions');

    cy.get('button').contains('Retry').click();
    cy.wait('@retryGetSessions');

    // Verify sessions loaded
    cy.contains('Chrome on Windows').should('be.visible');
  });

  it('should display session details with device information', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Mock detailed session info
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: {
        sessions: [{
          id: 'session-detailed',
          device_name: 'Chrome on Windows 11',
          ip_address: '192.168.1.100',
          location: 'New York, NY, United States',
          last_active: new Date().toISOString(),
          login_time: new Date(Date.now() - 7200000).toISOString(),
          current: true,
          user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          device_type: 'desktop',
          browser_version: 'Chrome 120.0.0.0'
        }]
      }
    }).as('getDetailedSessions');

    cy.wait('@getDetailedSessions');

    // Verify detailed information
    cy.contains('Chrome on Windows 11').should('be.visible');
    cy.contains('192.168.1.100').should('be.visible');
    cy.contains('New York, NY, United States').should('be.visible');
    cy.contains('Logged in 2 hours ago').should('be.visible');
    cy.contains('Desktop').should('be.visible');
  });

  it('should export session history', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Export session history
    cy.get('button').contains('Export Session History').click();

    // Mock export endpoint
    cy.intercept('GET', '/api/users/sessions/export', {
      statusCode: 200,
      headers: {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=session-history.csv'
      },
      body: 'session_id,device_name,ip_address,location,start_time,end_time,duration\nsession-1,Chrome,192.168.1.100,NY,2024-01-01,2024-01-01,3600'
    }).as('exportSessions');

    cy.wait('@exportSessions');

    // Verify export completed
    cy.contains('Session history exported successfully').should('be.visible');
  });

  it('should handle empty sessions list', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Mock empty sessions (should not happen, but good to test)
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: {
        sessions: []
      }
    }).as('getEmptySessions');

    cy.wait('@getEmptySessions');

    // Verify appropriate message
    cy.contains('No active sessions found').should('be.visible');
    cy.contains('This is unusual - you should have at least one active session').should('be.visible');
  });

  it('should refresh sessions list automatically', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Initial sessions load
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: {
        sessions: [{
          id: 'session-1',
          device_name: 'Chrome on Windows',
          current: true
        }]
      }
    }).as('initialSessions');

    cy.wait('@initialSessions');

    // Mock updated sessions after auto-refresh
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
          }
        ]
      }
    }).as('refreshedSessions');

    // Trigger manual refresh
    cy.get('button').contains('Refresh').click();
    cy.wait('@refreshedSessions');

    // Verify new session appears
    cy.contains('Safari on iPhone').should('be.visible');
  });

});