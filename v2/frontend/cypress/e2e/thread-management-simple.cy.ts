describe('Thread Management - Simplified', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    cy.visit('/chat');
  });

  it('should allow sending messages in chat', () => {
    // Wait for chat interface to load
    cy.get('input[placeholder*="message"]', { timeout: 10000 }).should('exist');
    
    // Type and send a message with force option
    const testMessage = 'Test thread message';
    cy.get('input[placeholder*="message"]').type(testMessage, { force: true });
    cy.get('button[aria-label="Send"]').click({ force: true });
    
    // Verify message appears
    cy.contains(testMessage, { timeout: 5000 }).should('be.visible');
  });

  it('should handle multiple messages in sequence', () => {
    // Wait for input to be ready
    cy.get('input[placeholder*="message"]', { timeout: 10000 }).should('exist');
    
    // Send first message
    const firstMessage = 'First message in thread';
    cy.get('input[placeholder*="message"]').type(firstMessage, { force: true });
    cy.get('button[aria-label="Send"]').click({ force: true });
    
    cy.contains(firstMessage, { timeout: 5000 }).should('be.visible');
    
    // Send second message
    const secondMessage = 'Second message in thread';
    cy.get('input[placeholder*="message"]').clear({ force: true }).type(secondMessage, { force: true });
    cy.get('button[aria-label="Send"]').click({ force: true });
    
    cy.contains(secondMessage, { timeout: 5000 }).should('be.visible');
    
    // Both messages should be visible
    cy.contains(firstMessage).should('be.visible');
    cy.contains(secondMessage).should('be.visible');
  });

  it('should maintain conversation context', () => {
    // Simulate WebSocket connection
    cy.window().then((win: any) => {
      // Mock WebSocket if needed
      if (!win.ws) {
        win.ws = {
          readyState: 1,
          send: cy.stub(),
          close: cy.stub()
        };
      }
    });
    
    // Send an optimization request
    const request = 'Optimize my LLM pipeline';
    cy.get('input[placeholder*="message"]', { timeout: 10000 }).type(request, { force: true });
    cy.get('button[aria-label="Send"]').click({ force: true });
    
    cy.contains(request, { timeout: 5000 }).should('be.visible');
    
    // Simulate agent response
    cy.window().then((win) => {
      const response = {
        type: 'message',
        payload: {
          id: 'msg-1',
          content: 'I can help optimize your LLM pipeline. Let me analyze your requirements.',
          type: 'agent',
          sub_agent_name: 'OptimizationAgent',
          displayed_to_user: true
        }
      };
      
      // Trigger message handler if WebSocket exists
      if ((win as any).ws && (win as any).ws.onmessage) {
        (win as any).ws.onmessage({ data: JSON.stringify(response) });
      }
    });
    
    // Check if agent response appears (if WebSocket is connected)
    cy.contains('optimize your LLM pipeline', { timeout: 5000 }).should('exist');
  });
});