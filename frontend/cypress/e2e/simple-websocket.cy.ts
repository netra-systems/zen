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
    cy.get('textarea[aria-label="Message input"]', { timeout: 10000 }).should('be.visible');
    cy.get('button[aria-label="Send message"]').should('be.visible');
  });

  it('should send and display user messages', () => {
    // Type and send multiple messages
    const messages = ['First message', 'Second message', 'Third message'];
    
    messages.forEach(msg => {
      cy.get('textarea[aria-label="Message input"]').type(msg);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(msg).should('be.visible');
    });
  });

  it('should clear input after sending message', () => {
    // Type message
    cy.get('textarea[aria-label="Message input"]').type('Test message');
    
    // Send message
    cy.get('button[aria-label="Send message"]').click();
    
    // Input should be cleared
    cy.get('textarea[aria-label="Message input"]').should('have.value', '');
  });

  it('should disable input while processing', () => {
    // Send a message
    cy.get('textarea[aria-label="Message input"]').type('Process this');
    cy.get('button[aria-label="Send message"]').click();
    
    // Check if input gets disabled (may depend on implementation)
    cy.get('textarea[aria-label="Message input"]').then($input => {
      // Input might be disabled or have a different placeholder
      const isDisabled = $input.prop('disabled');
      const placeholder = $input.attr('placeholder');
      
      // Assert one of the expected states during processing
      expect(isDisabled || placeholder?.includes('thinking')).to.be.true;
    });
  });
});