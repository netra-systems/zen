describe('Complete Authentication Flow', () => {
  beforeEach(() => {
    cy.clearCookies();
    cy.clearLocalStorage();
  });

  it('should handle complete authentication flow with form login, session persistence, and logout', () => {
    // Visit login page
    cy.visit('/login');
    
    // Mock the auth config endpoint
    cy.intercept('GET', '**/auth/config', {
      statusCode: 200,
      body: {
        login_url: '/auth/login',
        callback_url: '/auth/callback',
        logout_url: '/auth/logout',
        user: '/auth/me',
        endpoints: {
          login: '/auth/dev/login',
          refresh: '/auth/refresh',
          verify: '/auth/verify'
        }
      }
    }).as('authConfig');

    // Mock the login API endpoint with current structure
    cy.intercept('POST', '**/auth/dev/login', {
      statusCode: 200,
      body: {
        jwt_token: 'test-jwt-token',
        refresh_token: 'test-refresh-token',
        token_type: 'bearer',
        user: {
          id: 'test-user-id',
          email: 'test@netrasystems.ai',
          full_name: 'Test User'
        }
      }
    }).as('loginRequest');

    // Mock the user endpoint with current auth structure
    cy.intercept('GET', '**/auth/me', {
      statusCode: 200,
      body: {
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
        role: 'user',
        verified: true
      }
    }).as('userRequest');

    // Mock token verification endpoint
    cy.intercept('POST', '**/auth/verify', {
      statusCode: 200,
      body: {
        valid: true,
        user: {
          id: 'test-user-id',
          email: 'test@netrasystems.ai',
          full_name: 'Test User'
        }
      }
    }).as('verifyToken');

    // Fill in login form - development mode uses different login flow
    cy.get('body').then(($body) => {
      if ($body.find('[data-testid="login-button"]').length > 0) {
        // Quick dev login available
        cy.get('[data-testid="login-button"]').click();
      } else {
        // Use form login
        cy.get('input[type="email"]').type('test@netrasystems.ai');
        cy.get('input[type="password"]').type('SecurePassword123!');
        cy.get('button').contains(/sign in|login|submit/i).click();
      }
    });

    // Wait for login to complete and auth config to load
    cy.wait('@authConfig');
    cy.wait('@loginRequest');
    
    // Should redirect to main app
    cy.url().should('include', '/chat');
    
    // Verify token is stored with correct key
    cy.window().its('localStorage.jwt_token').should('equal', 'test-jwt-token');
    
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
    cy.window().its('localStorage.jwt_token').should('be.null');
    
    // Protected route should redirect to login
    cy.visit('/corpus');
    cy.url().should('include', '/login');
  });

  it('should handle authentication errors gracefully', () => {
    cy.visit('/login');
    
    // Mock auth config first
    cy.intercept('GET', '**/auth/config', {
      statusCode: 200,
      body: {
        endpoints: {
          login: '/auth/dev/login'
        }
      }
    }).as('authConfigError');

    // Mock failed login with current structure
    cy.intercept('POST', '**/auth/dev/login', {
      statusCode: 401,
      body: {
        detail: 'Invalid credentials',
        error: 'authentication_failed'
      }
    }).as('failedLogin');

    // Try to login with invalid credentials
    cy.get('input[type="email"]').type('wrong@netrasystems.ai');
    cy.get('input[type="password"]').type('WrongPassword');
    cy.get('button[type="submit"]').contains('Sign In').click();

    cy.wait('@authConfigError');
    cy.wait('@failedLogin');
    
    // Should show error message
    cy.contains('Invalid credentials').should('be.visible');
    
    // Should still be on login page
    cy.url().should('include', '/login');
  });

  it('should handle token expiration and refresh', () => {
    // Setup initial authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'expired-token');
    });

    // Mock auth config for refresh flow
    cy.intercept('GET', '**/auth/config', {
      statusCode: 200,
      body: {
        endpoints: {
          refresh: '/auth/refresh'
        }
      }
    }).as('authConfigRefresh');

    // Mock expired token response from current endpoint
    cy.intercept('GET', '**/auth/me', {
      statusCode: 401,
      body: {
        detail: 'Token expired',
        error: 'token_expired'
      }
    }).as('expiredToken');

    // Mock refresh token failure
    cy.intercept('POST', '**/auth/refresh', {
      statusCode: 401,
      body: {
        detail: 'Refresh token invalid',
        error: 'refresh_failed'
      }
    }).as('refreshFailed');

    // Visit protected route
    cy.visit('/chat');
    
    cy.wait('@authConfigRefresh');
    cy.wait('@expiredToken');
    
    // Should redirect to login
    cy.url().should('include', '/login');
    
    // Token should be cleared
    cy.window().its('localStorage.jwt_token').should('be.null');
  });
});