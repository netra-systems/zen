describe('Complete Authentication Flow', () => {
  beforeEach(() => {
    cy.clearCookies();
    cy.clearLocalStorage();
  });

  it('should handle complete authentication flow with form login, session persistence, and logout', () => {
    // Visit login page
    cy.visit('/login');
    
    // Mock the login API endpoint
    cy.intercept('POST', '/api/auth/login', {
      statusCode: 200,
      body: {
        access_token: 'test-jwt-token',
        token_type: 'bearer',
        user: {
          id: 1,
          email: 'test@netrasystems.ai',
          full_name: 'Test User'
        }
      }
    }).as('loginRequest');

    // Mock the user endpoint
    cy.intercept('GET', '/api/me', {
      statusCode: 200,
      body: {
        id: 1,
        email: 'test@netrasystems.ai',
        full_name: 'Test User'
      }
    }).as('userRequest');

    // Fill in login form (assuming there's an email/password form option)
    cy.get('input[type="email"]').type('test@netrasystems.ai');
    cy.get('input[type="password"]').type('SecurePassword123!');
    cy.get('button[type="submit"]').contains('Sign In').click();

    // Wait for login to complete
    cy.wait('@loginRequest');
    
    // Should redirect to main app
    cy.url().should('include', '/chat');
    
    // Verify token is stored
    cy.window().its('localStorage.authToken').should('equal', 'test-jwt-token');
    
    // Verify user info is visible
    cy.contains('Test User').should('be.visible');
    
    // Test session persistence - reload page
    cy.reload();
    cy.wait('@userRequest');
    
    // Should still be logged in
    cy.contains('Test User').should('be.visible');
    
    // Test protected route access
    cy.visit('/corpus');
    cy.url().should('include', '/corpus');
    
    // Test logout
    cy.get('button').contains('Logout').click();
    
    // Should redirect to login
    cy.url().should('include', '/login');
    
    // Token should be cleared
    cy.window().its('localStorage.authToken').should('be.undefined');
    
    // Protected route should redirect to login
    cy.visit('/corpus');
    cy.url().should('include', '/login');
  });

  it('should handle authentication errors gracefully', () => {
    cy.visit('/login');
    
    // Mock failed login
    cy.intercept('POST', '/api/auth/login', {
      statusCode: 401,
      body: {
        detail: 'Invalid credentials'
      }
    }).as('failedLogin');

    // Try to login with invalid credentials
    cy.get('input[type="email"]').type('wrong@netrasystems.ai');
    cy.get('input[type="password"]').type('WrongPassword');
    cy.get('button[type="submit"]').contains('Sign In').click();

    cy.wait('@failedLogin');
    
    // Should show error message
    cy.contains('Invalid credentials').should('be.visible');
    
    // Should still be on login page
    cy.url().should('include', '/login');
  });

  it('should handle token expiration and refresh', () => {
    // Setup initial authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('authToken', 'expired-token');
    });

    // Mock expired token response
    cy.intercept('GET', '/api/me', {
      statusCode: 401,
      body: {
        detail: 'Token expired'
      }
    }).as('expiredToken');

    // Visit protected route
    cy.visit('/chat');
    
    cy.wait('@expiredToken');
    
    // Should redirect to login
    cy.url().should('include', '/login');
    
    // Token should be cleared
    cy.window().its('localStorage.authToken').should('be.undefined');
  });
});