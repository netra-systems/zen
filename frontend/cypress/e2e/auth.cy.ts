
describe('Authentication', () => {
  it('should allow a user to log in and out', () => {
    // Visit the login page
    cy.visit('/login');

    // Mock the API response for fetching user data
    cy.intercept('GET', '/api/me', {
      statusCode: 200,
      body: { id: 1, full_name: 'Test User', email: 'test@example.com' },
    }).as('getUserRequest');

    // Click the login button
    cy.get('button').contains('Login with Google').click();

    // Mock the successful login
    cy.window().then((win) => {
      win.localStorage.setItem('authToken', 'test-token');
    });

    // Visit the home page, which should now be accessible
    cy.visit('/');

    // Wait for the user request to complete
    cy.wait('@getUserRequest');

    // Verify that the user menu is visible
    cy.get('button[aria-label="Toggle user menu"]').should('be.visible');

    // Log out
    cy.get('button[aria-label="Toggle user menu"]').click();
    cy.contains('Logout').click();

    // Verify that the user is redirected to the login page
    cy.url().should('include', '/login');
  });
});
