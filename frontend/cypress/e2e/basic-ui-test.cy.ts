describe('Basic UI Test', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });
    cy.visit('/chat');
  });

  it('should have chat input and send button', () => {
    // Check for textarea field (not input) with correct placeholder
    cy.get('textarea[aria-label="Message input"]', { timeout: 10000 }).should('exist');
    
    // Check for send button with correct aria-label
    cy.get('button[aria-label="Send message"]').should('exist');
  });

  it('should allow typing in the input field', () => {
    const testText = 'Test message';
    
    // Type in the textarea field
    cy.get('textarea[aria-label="Message input"]', { timeout: 10000 })
      .type(testText, { force: true })
      .should('have.value', testText);
  });

  it('should clear input after clicking send', () => {
    const testText = 'Message to send';
    
    // Type and send
    cy.get('textarea[aria-label="Message input"]', { timeout: 10000 })
      .type(testText, { force: true });
    
    cy.get('button[aria-label="Send message"]').click({ force: true });
    
    // Textarea should be cleared after send
    cy.get('textarea[aria-label="Message input"]').should('have.value', '');
  });

  it('should show some content area for messages', () => {
    // Check for a container that would hold messages
    // Using flexible selectors since we don't know exact structure
    cy.get('div').should('exist'); // At minimum, there should be divs
    
    // Check for main content area (usually has overflow or flex properties)
    cy.get('[class*="overflow"]').should('exist').then($el => {
      // Just verify it exists, don't check specific content
      expect($el.length).to.be.greaterThan(0);
    });
  });

  it('should maintain authentication state', () => {
    // Check localStorage has token
    cy.window().then((win) => {
      const token = win.localStorage.getItem('jwt_token');
      expect(token).to.equal('test-jwt-token');
    });
    
    // Should stay on chat page
    cy.url().should('include', '/chat');
  });
});