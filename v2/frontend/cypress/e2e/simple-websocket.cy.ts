describe('Simple WebSocket Tests', () => {
  beforeEach(() => {
    // Setup auth
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });
    cy.visit('/chat');
  });

  it('should load chat interface', () => {
    // Wait for chat elements to be visible
    cy.get('input[placeholder*="message"]', { timeout: 10000 }).should('be.visible');
    cy.get('button[aria-label="Send"]').should('be.visible');
  });

  it('should send and display user messages', () => {
    // Type and send multiple messages
    const messages = ['First message', 'Second message', 'Third message'];
    
    messages.forEach(msg => {
      cy.get('input[placeholder*="message"]').type(msg);
      cy.get('button[aria-label="Send"]').click();
      cy.contains(msg).should('be.visible');
    });
  });

  it('should clear input after sending message', () => {
    // Type message
    cy.get('input[placeholder*="message"]').type('Test message');
    
    // Send message
    cy.get('button[aria-label="Send"]').click();
    
    // Input should be cleared
    cy.get('input[placeholder*="message"]').should('have.value', '');
  });

  it('should disable input while processing', () => {
    // Send a message
    cy.get('input[placeholder*="message"]').type('Process this');
    cy.get('button[aria-label="Send"]').click();
    
    // Check if input gets disabled (may depend on implementation)
    cy.get('input[placeholder*="message"]').then($input => {
      // Input might be disabled or have a different placeholder
      const isDisabled = $input.prop('disabled');
      const placeholder = $input.attr('placeholder');
      
      // Assert one of the expected states during processing
      expect(isDisabled || placeholder?.includes('thinking')).to.be.true;
    });
  });
});