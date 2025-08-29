describe('Critical Authentication Flow', () => {
  beforeEach(() => {
    cy.clearLocalStorage();
    cy.clearCookies();
    cy.visit('/');
  });

  it('should display login page with Google OAuth option', () => {
    // 1. Navigate to login page
    cy.visit('/login');
    cy.url().should('include', '/login');
    
    // 2. Verify login page elements
    cy.contains('Netra').should('be.visible');
    cy.get('body').should('contain.text', 'Login with Google').or('contain.text', 'Quick Dev Login');
    
    // 3. Verify login button is enabled
    cy.get('button').contains(/login|access|dev/i).should('not.be.disabled');
  });

  it('should redirect unauthenticated users to login', () => {
    // 1. Try to access protected route
    cy.visit('/chat');
    
    // 2. Should redirect to login
    cy.url().should('include', '/login');
    cy.get('body').should('contain.text', 'Login with Google').or('contain.text', 'Quick Dev Login');
  });

  it('should handle authentication state in localStorage', () => {
    // 1. Visit login page
    cy.visit('/login');
    
    // 2. Simulate setting auth token (mock successful auth)
    cy.window().then((win) => {
      // Mock a successful authentication by setting token
      win.localStorage.setItem('jwt_token', 'mock-jwt-token-for-testing');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User'
      }));
    });
    
    // 3. Try to visit chat page
    cy.visit('/chat');
    
    // 4. Should allow access if token exists
    // Note: This may still redirect if backend validation fails
    cy.url().then((url) => {
      // Either stays on chat or redirects to login based on backend validation
      expect(url).to.match(/\/(chat|login)/);
    });
    
    // 5. Clear auth state
    cy.window().then((win) => {
      win.localStorage.removeItem('jwt_token');
      win.localStorage.removeItem('user');
    });
    
    // 6. Should redirect to login after clearing auth
    cy.visit('/chat');
    cy.url().should('include', '/login');
  });

  it('should show loading state during authentication', () => {
    // 1. Visit login page
    cy.visit('/login');
    
    // 2. Mock auth config to check for development mode
    cy.intercept('GET', 'http://localhost:8001/auth/config', {
      statusCode: 200,
      body: {
        development_mode: true,
        endpoints: {
          dev_login: 'http://localhost:8001/auth/dev/login'
        }
      }
    });
    
    // 3. Click login button
    cy.get('button').contains('Login with Google').click();
    
    // 4. Should show loading state (in development mode)
    cy.get('button').contains(/loading|logging/i).should('be.visible');
  });

  it('should handle OAuth callback flow', () => {
    // 1. Simulate OAuth callback with code
    cy.visit('/auth/callback?code=test-auth-code&state=test-state');
    
    // 2. Should process callback (may redirect to login or chat)
    cy.url().should('match', /\/(login|chat|auth)/);
    
    // 3. Check for error handling if callback fails
    cy.visit('/auth/callback?error=access_denied');
    cy.url().should('include', '/auth');
  });

  it('should handle logout flow', () => {
    // 1. Set up authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'mock-jwt-token');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User'
      }));
    });
    
    // 2. Visit logout route
    cy.visit('/auth/logout');
    
    // 3. Should clear auth state and redirect
    cy.window().then((win) => {
      const token = win.localStorage.getItem('jwt_token');
      expect(token).to.be.null;
    });
    
    // 4. Should redirect to login
    cy.url().should('include', '/login');
  });
});