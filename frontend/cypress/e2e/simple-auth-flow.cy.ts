describe('Simple Authentication Flow', () => {
  beforeEach(() => {
    cy.clearLocalStorage();
    cy.clearCookies();
  });

  it('should display login page and handle authentication', () => {
    // Use SSOT cy.login() command for authentication
    cy.login();
    
    // Should redirect to chat page after login
    cy.url().should('include', '/chat');
    
    // Check for chat elements with updated selectors
    cy.get('textarea[data-testid="message-input"]', { timeout: 15000 }).should('be.visible');
    cy.get('button[data-testid="send-button"]').should('be.visible');
  });

  it('should allow message sending in chat', () => {
    // Use SSOT cy.login() command for authentication
    cy.login();
    
    // Should be on chat page
    cy.url().should('include', '/chat');
    
    // Type and send a message - updated selectors for current implementation
    const testMessage = 'Test optimization request';
    cy.get('textarea[data-testid="message-input"]', { timeout: 15000 }).should('be.visible');
    cy.get('textarea[data-testid="message-input"]').type(testMessage);
    cy.get('button[data-testid="send-button"]').should('not.be.disabled');
    cy.get('button[data-testid="send-button"]').click();
    
    // Verify message appears in chat - check for the message in the UI
    cy.contains(testMessage, { timeout: 10000 }).should('be.visible');
  });
});