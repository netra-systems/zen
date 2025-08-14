
describe('Authentication', () => {
  it('should allow a user to log in and out', () => {
    // Mock the API responses
    cy.intercept('GET', '**/api/me', {
      statusCode: 200,
      body: { 
        id: 1, 
        full_name: 'Test User', 
        email: 'test@example.com', 
        picture: 'https://example.com/avatar.jpg' 
      },
    }).as('getUserRequest');

    cy.intercept('GET', '**/api/auth/config', {
      statusCode: 200,
      body: {
        auth_enabled: true,
        endpoints: {
          login: '/api/auth/login',
          logout: '/api/auth/logout',
          user: '/api/me',
          dev_login: '/api/auth/dev/login'
        }
      }
    }).as('authConfig');

    cy.intercept('POST', '**/api/auth/logout', {
      statusCode: 200,
      body: { success: true }
    }).as('logoutRequest');

    // Visit the login page
    cy.visit('/login');

    // Wait for auth config to load
    cy.wait('@authConfig');

    // Intercept OAuth redirect to prevent navigation
    cy.on('window:before:load', (win) => {
      Object.defineProperty(win, 'location', {
        value: {
          ...win.location,
          href: win.location.href,
          assign: cy.stub(),
          replace: cy.stub()
        },
        writable: true
      });
    });

    // Set authentication token before clicking login
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-token');
    });

    // Click the login button
    cy.get('button').contains('Login with Google').click();

    // Since we stubbed the redirect, manually navigate to the authenticated page
    cy.visit('/');

    // The app should request user data
    cy.wait('@getUserRequest');

    // Verify that the user info is visible
    cy.contains('Test User').should('be.visible');

    // Log out
    cy.get('button').contains('Logout').click();

    // Wait for logout request
    cy.wait('@logoutRequest');

    // Should redirect to login page (or check that token is removed)
    cy.window().then((win) => {
      expect(win.localStorage.getItem('jwt_token')).to.be.null;
    });
  });
});
