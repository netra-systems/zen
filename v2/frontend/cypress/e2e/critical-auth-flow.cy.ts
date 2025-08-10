describe('Critical Authentication Flow', () => {
  const testUser = {
    email: 'test@netra.ai',
    password: 'TestPassword123!',
    name: 'Test User'
  };

  beforeEach(() => {
    cy.clearLocalStorage();
    cy.clearCookies();
    cy.visit('/');
  });

  it('should complete full authentication lifecycle', () => {
    // 1. Navigate to login page
    cy.visit('/auth/login');
    cy.url().should('include', '/auth/login');
    
    // 2. Verify login form is present
    cy.get('input[type="email"]').should('be.visible');
    cy.get('input[type="password"]').should('be.visible');
    cy.get('button[type="submit"]').should('be.visible');
    
    // 3. Attempt login with invalid credentials
    cy.get('input[type="email"]').type('invalid@email.com');
    cy.get('input[type="password"]').type('wrongpassword');
    cy.get('button[type="submit"]').click();
    
    // Should show error message
    cy.contains(/invalid credentials|authentication failed/i).should('be.visible');
    
    // 4. Login with valid credentials
    cy.get('input[type="email"]').clear().type(testUser.email);
    cy.get('input[type="password"]').clear().type(testUser.password);
    cy.get('button[type="submit"]').click();
    
    // 5. Verify successful login and redirect
    cy.url().should('include', '/chat');
    cy.contains(/welcome|dashboard|chat/i).should('be.visible');
    
    // 6. Verify auth token is stored
    cy.window().then((win) => {
      const token = win.localStorage.getItem('auth_token') || 
                    win.localStorage.getItem('token') ||
                    win.localStorage.getItem('access_token');
      expect(token).to.not.be.null;
    });
    
    // 7. Test protected route access
    cy.visit('/chat');
    cy.url().should('include', '/chat');
    cy.contains(/welcome|chat|optimize/i).should('be.visible');
    
    // 8. Refresh page and verify session persistence
    cy.reload();
    cy.url().should('include', '/chat');
    cy.contains(/welcome|chat|optimize/i).should('be.visible');
    
    // 9. Test logout functionality
    cy.get('button').contains(/logout|sign out/i).click();
    
    // 10. Verify logout redirects to login
    cy.url().should('include', '/auth/login');
    
    // 11. Verify token is cleared
    cy.window().then((win) => {
      const token = win.localStorage.getItem('auth_token') || 
                    win.localStorage.getItem('token') ||
                    win.localStorage.getItem('access_token');
      expect(token).to.be.null;
    });
    
    // 12. Attempt to access protected route after logout
    cy.visit('/chat');
    cy.url().should('include', '/auth/login');
  });

  it('should handle session expiration gracefully', () => {
    // Login first
    cy.visit('/auth/login');
    cy.get('input[type="email"]').type(testUser.email);
    cy.get('input[type="password"]').type(testUser.password);
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/chat');
    
    // Simulate expired token by clearing it
    cy.window().then((win) => {
      win.localStorage.removeItem('auth_token');
      win.localStorage.removeItem('token');
      win.localStorage.removeItem('access_token');
    });
    
    // Try to navigate to protected route
    cy.visit('/chat');
    
    // Should redirect to login
    cy.url().should('include', '/auth/login');
    cy.contains(/session expired|please login/i).should('be.visible');
  });

  it('should maintain authentication state across multiple tabs', () => {
    // Login in first tab
    cy.visit('/auth/login');
    cy.get('input[type="email"]').type(testUser.email);
    cy.get('input[type="password"]').type(testUser.password);
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/chat');
    
    // Store auth token
    let authToken: string | null;
    cy.window().then((win) => {
      authToken = win.localStorage.getItem('auth_token') || 
                  win.localStorage.getItem('token') ||
                  win.localStorage.getItem('access_token');
    });
    
    // Open new tab simulation (visit same page in new context)
    cy.visit('/chat');
    
    // Verify authentication persists
    cy.url().should('include', '/chat');
    cy.window().then((win) => {
      const currentToken = win.localStorage.getItem('auth_token') || 
                          win.localStorage.getItem('token') ||
                          win.localStorage.getItem('access_token');
      expect(currentToken).to.equal(authToken);
    });
  });
});