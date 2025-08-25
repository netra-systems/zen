
describe('Authentication and Session Token Lifecycle (L4)', () => {

  const TEST_USER = Cypress.env('CYPRESS_TEST_USER');
  const TEST_PASSWORD = Cypress.env('CYPRESS_TEST_PASSWORD');
  const LOGIN_URL = '/login';
  const PROTECTED_API_ENDPOINT = '/api/user/profile'; // Example protected endpoint
  const AUTH_SERVICE_URL = 'http://localhost:8001/api/auth/token'; // Example auth service URL

  beforeEach(() => {
    cy.visit(LOGIN_URL);
    cy.window().then((win) => {
      win.localStorage.clear();
    });
  });

  it('should allow a user to log in, access a protected route, and log out', () => {
    // 1. Visit the login page and enter credentials
    // NOTE: Replace with actual selectors for the login form
    cy.get('input[name="username"]').type(TEST_USER);
    cy.get('input[name="password"]').type(TEST_PASSWORD);
    cy.get('button[type="submit"]').click();

    // 2. Verify that a JWT is received and stored
    cy.window().then((win) => {
      const token = win.localStorage.getItem('authToken');
      expect(token).to.be.a('string').and.not.be.empty;

      // 3. Make an authenticated API call to a protected endpoint
      cy.request({
        url: PROTECTED_API_ENDPOINT,
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }).then((response) => {
        // 4. Verify the API call is successful
        expect(response.status).to.eq(200);
        expect(response.body).to.have.property('user');
      });
    });

    // 5. Log the user out
    // NOTE: Replace with actual selector for the logout button
    cy.get('button#logout').click();

    // 6. Verify the session is destroyed
    cy.window().then((win) => {
      const token = win.localStorage.getItem('authToken');
      expect(token).to.be.null;
    });

    // 7. Verify user is redirected to the login page
    cy.url().should('include', LOGIN_URL);
  });

  it('should prevent access to protected routes without a valid token', () => {
    cy.request({
      url: PROTECTED_API_ENDPOINT,
      failOnStatusCode: false // Don't fail the test on a 4xx/5xx response
    }).then((response) => {
      expect(response.status).to.eq(401); // Unauthorized
    });
  });
});
