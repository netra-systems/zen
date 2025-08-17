/**
 * User Session Revocation E2E Tests
 * Split from user-device-sessions.cy.ts for 300-line compliance
 * 
 * BVJ: Enterprise segment - Session control drives security compliance
 * Value Impact: Remote session control = security incident response
 */

describe('User Session Revocation Management', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    cy.visit('/');
  });

  it('should revoke specific session successfully', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Mock sessions
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: {
        sessions: [
          {
            id: 'session-current',
            device_name: 'Chrome on Windows',
            current: true,
            last_active: new Date().toISOString()
          },
          {
            id: 'session-revoke',
            device_name: 'Safari on iPhone',
            current: false,
            last_active: new Date(Date.now() - 3600000).toISOString()
          }
        ]
      }
    }).as('getSessionsForRevoke');

    cy.wait('@getSessionsForRevoke');

    // Revoke specific session
    cy.contains('Safari on iPhone').parent().find('button').contains('Revoke').click();

    // Confirm revocation
    cy.contains('Are you sure you want to revoke this session?').should('be.visible');
    cy.contains('The user will be logged out from this device').should('be.visible');

    // Mock revoke endpoint
    cy.intercept('DELETE', '/api/users/sessions/session-revoke', {
      statusCode: 204
    }).as('revokeSession');

    cy.get('button').contains('Revoke Session').click();
    cy.wait('@revokeSession');

    // Verify session removed
    cy.contains('Safari on iPhone').should('not.exist');
    cy.contains('Session revoked successfully').should('be.visible');
  });

  it('should revoke all other sessions', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Mock multiple sessions
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: {
        sessions: [
          {
            id: 'session-current',
            device_name: 'Chrome on Windows',
            current: true
          },
          {
            id: 'session-other-1',
            device_name: 'Safari on iPhone',
            current: false
          },
          {
            id: 'session-other-2',
            device_name: 'Firefox on Linux',
            current: false
          }
        ]
      }
    }).as('getMultipleSessions');

    cy.wait('@getMultipleSessions');

    // Revoke all other sessions
    cy.get('button').contains('Revoke All Other Sessions').click();

    // Confirm action
    cy.contains('This will log you out from all other devices').should('be.visible');
    cy.contains('2 sessions will be revoked').should('be.visible');

    // Mock revoke all endpoint
    cy.intercept('POST', '/api/users/sessions/revoke-all', {
      statusCode: 200,
      body: {
        revoked_count: 2,
        message: '2 session(s) revoked successfully'
      }
    }).as('revokeAllSessions');

    cy.get('button').contains('Revoke All').click();
    cy.wait('@revokeAllSessions');

    // Verify only current session remains
    cy.contains('Firefox on Linux').should('not.exist');
    cy.contains('Safari on iPhone').should('not.exist');
    cy.contains('Chrome on Windows').should('be.visible');
    cy.contains('2 session(s) revoked successfully').should('be.visible');
  });

  it('should handle revocation confirmation modal', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Mock sessions for revocation test
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: {
        sessions: [
          {
            id: 'session-current',
            device_name: 'Chrome on Windows',
            current: true
          },
          {
            id: 'session-target',
            device_name: 'Safari on MacBook',
            current: false,
            location: 'San Francisco, US',
            last_active: new Date(Date.now() - 1800000).toISOString() // 30 min ago
          }
        ]
      }
    }).as('getRevocationSessions');

    cy.wait('@getRevocationSessions');

    // Start revocation
    cy.contains('Safari on MacBook').parent().find('button').contains('Revoke').click();

    // Verify detailed confirmation modal
    cy.contains('Revoke Session').should('be.visible');
    cy.contains('Safari on MacBook').should('be.visible');
    cy.contains('San Francisco, US').should('be.visible');
    cy.contains('Last active: 30 minutes ago').should('be.visible');
    cy.contains('This will immediately log out the user from this device').should('be.visible');

    // Cancel revocation
    cy.get('button').contains('Cancel').click();
    cy.contains('Revoke Session').should('not.exist');

    // Session should still be there
    cy.contains('Safari on MacBook').should('be.visible');
  });

  it('should handle revocation errors gracefully', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Mock sessions
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: {
        sessions: [
          {
            id: 'session-current',
            device_name: 'Chrome on Windows',
            current: true
          },
          {
            id: 'session-error',
            device_name: 'Firefox on Linux',
            current: false
          }
        ]
      }
    }).as('getErrorSessions');

    cy.wait('@getErrorSessions');

    // Attempt revocation
    cy.contains('Firefox on Linux').parent().find('button').contains('Revoke').click();

    // Mock revocation error
    cy.intercept('DELETE', '/api/users/sessions/session-error', {
      statusCode: 500,
      body: {
        error: 'Unable to revoke session. Please try again.'
      }
    }).as('revokeError');

    cy.get('button').contains('Revoke Session').click();
    cy.wait('@revokeError');

    // Verify error handling
    cy.contains('Unable to revoke session').should('be.visible');
    cy.get('button').contains('Try Again').should('be.visible');

    // Session should still be visible
    cy.contains('Firefox on Linux').should('be.visible');
  });

  it('should handle bulk revocation with confirmation', () => {
    cy.visit('/settings');
    cy.get('button').contains('Security').click();
    cy.get('button').contains('Active Sessions').click();

    // Mock many sessions
    cy.intercept('GET', '/api/users/sessions', {
      statusCode: 200,
      body: {
        sessions: [
          {
            id: 'session-current',
            device_name: 'Chrome on Windows',
            current: true
          },
          {
            id: 'session-mobile-1',
            device_name: 'Safari on iPhone',
            current: false
          },
          {
            id: 'session-mobile-2',
            device_name: 'Chrome on Android',
            current: false
          },
          {
            id: 'session-tablet',
            device_name: 'Safari on iPad',
            current: false
          }
        ]
      }
    }).as('getBulkSessions');

    cy.wait('@getBulkSessions');

    // Initiate bulk revocation
    cy.get('button').contains('Revoke All Other Sessions').click();

    // Verify bulk confirmation details
    cy.contains('Revoke All Other Sessions').should('be.visible');
    cy.contains('3 sessions will be revoked').should('be.visible');
    cy.contains('This will log out all other devices').should('be.visible');
    cy.contains('Your current session will remain active').should('be.visible');

    // List of sessions to be revoked
    cy.contains('Sessions to be revoked:').should('be.visible');
    cy.contains('Safari on iPhone').should('be.visible');
    cy.contains('Chrome on Android').should('be.visible');
    cy.contains('Safari on iPad').should('be.visible');

    // Current session should not be listed
    cy.contains('Chrome on Windows').should('not.exist');
  });

});