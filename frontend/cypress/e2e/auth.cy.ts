
describe('Authentication', () => {
  it('should allow a user to log in and out', () => {
    // Visit the login page
    cy.visit('/login');

    // Mock the API response for fetching user data
    cy.intercept('GET', '/api/me', {
      statusCode: 200,
      body: { id: 1, full_name: 'Test User', email: 'test@example.com', picture: 'https://example.com/avatar.jpg' },
    }).as('getUserRequest');

    // Mock auth config to prevent actual OAuth redirect
    cy.intercept('GET', '/api/auth/config', {
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

    // Stub window.location.href to prevent actual navigation
    cy.window().then((win) => {
      const stub = cy.stub(win.location, 'href').as('locationHref');
    });

    // Click the login button
    cy.get('button').contains('Login with Google').click();

    // Instead of actual OAuth flow, simulate successful authentication
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-token');
      win.localStorage.setItem('user', JSON.stringify({
        id: 1,
        full_name: 'Test User',
        email: 'test@example.com',
        picture: 'https://example.com/avatar.jpg'
      }));
      
      // Trigger a storage event to notify the app of the change
      win.dispatchEvent(new StorageEvent('storage', {
        key: 'jwt_token',
        newValue: 'test-token',
        storageArea: win.localStorage
      }));
    });

    // Visit the home page, which should now be accessible
    cy.visit('/');

    // Wait for the user request to complete
    cy.wait('@getUserRequest');

    // Verify that the user info is visible (user avatar and name)
    cy.get('img[alt="Test User"]').should('be.visible');
    cy.contains('Test User').should('be.visible');

    // Mock logout endpoint
    cy.intercept('POST', '/api/auth/logout', {
      statusCode: 200,
      body: { success: true }
    }).as('logoutRequest');

    // Log out using the Logout button
    cy.get('button').contains('Logout').click();

    // Verify that the user is redirected to the login page
    cy.url().should('include', '/login');
  });
});
