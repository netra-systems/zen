describe('Simple Authentication Flow', () => {
  it('should display login page and handle authentication', () => {
    // Visit login page
    cy.visit('/login');
    
    // Verify login page elements
    cy.contains('h1', 'Netra').should('be.visible');
    cy.contains('button', 'Login with Google').should('be.visible');
    
    // Simulate authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });
    
    // Visit chat page with token
    cy.visit('/chat');
    
    // Should be on chat page
    cy.url().should('include', '/chat');
    
    // Check for chat elements
    cy.get('input[placeholder*="message"]', { timeout: 10000 }).should('be.visible');
    cy.get('button[aria-label="Send"]').should('be.visible');
  });

  it('should allow message sending in chat', () => {
    // Setup auth
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });
    
    cy.visit('/chat');
    
    // Type and send a message
    const testMessage = 'Test optimization request';
    cy.get('input[placeholder*="message"]', { timeout: 10000 }).type(testMessage);
    cy.get('button[aria-label="Send"]').click();
    
    // Verify message appears in chat
    cy.contains(testMessage).should('be.visible');
  });
});