describe('Simple Authentication Flow', () => {
  it('should display login page and handle authentication', () => {
    // Visit login page
    cy.visit('/login');
    
    // Verify login page elements - updated for current implementation
    cy.contains('Netra').should('be.visible');
    // In development mode, should show the Quick Dev Login button
    cy.contains('button', 'Quick Dev Login').should('be.visible');
    
    // Use the Quick Dev Login button instead of manually setting localStorage
    cy.contains('button', 'Quick Dev Login').click();
    
    // Should redirect to chat page after login
    cy.url().should('include', '/chat');
    
    // Check for chat elements with updated selectors
    cy.get('textarea[data-testid="message-input"]', { timeout: 15000 }).should('be.visible');
    cy.get('button[data-testid="send-button"]').should('be.visible');
  });

  it('should allow message sending in chat', () => {
    // Use login flow instead of manually setting token
    cy.visit('/login');
    cy.contains('button', 'Quick Dev Login').click();
    
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