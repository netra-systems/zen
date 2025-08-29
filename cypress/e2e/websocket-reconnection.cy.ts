describe('WebSocket Reconnection after Interruption (L4)', () => {

  const CHAT_URL = '/chat';

  beforeEach(() => {
    // Setup authenticated state first
    cy.window().then((win) => {
      win.localStorage.setItem('authToken', 'test-token-reconnection');
    });
    
    // Mock authentication endpoint
    cy.intercept('GET', '/api/me', {
      statusCode: 200,
      body: {
        id: 1,
        email: 'test@netrasystems.ai',
        full_name: 'Test User Reconnection'
      }
    }).as('userRequest');

    cy.visit(CHAT_URL);
    
    // Wait for authentication to complete
    cy.wait('@userRequest');
    
    // Wait for WebSocket connection to establish and UI to be ready
    cy.get('textarea', { timeout: 10000 }).should('be.visible').and('not.be.disabled');
    
    // Ensure WebSocket connection is established before each test
    cy.window().then((win) => {
      // Wait for WebSocket connection to be available
      const checkConnection = () => {
        const ws = (win as any).webSocketConnection || (win as any).ws;
        return ws && ws.readyState === WebSocket.OPEN;
      };
      
      if (!checkConnection()) {
        cy.wait(2000).then(() => {
          expect(checkConnection(), 'WebSocket should be connected').to.be.true;
        });
      }
    });
  });

  it('should automatically reconnect and restore state after a WebSocket interruption', () => {
    // 1. Start an agent workflow
    cy.get('textarea').first().type('Start a long-running agent workflow.{enter}');
    
    // Wait for message to be sent and appear in chat
    cy.contains('Start a long-running agent workflow.', { timeout: 5000 }).should('be.visible');

    // 2. Verify the WebSocket connection is active
    cy.window().then((win) => {
      // Access the current WebSocket connection through the global window reference
      // The current implementation stores WebSocket reference on window for testing
      const ws = (win as any).webSocketConnection || (win as any).ws;
      expect(ws).to.exist;
      expect(ws.readyState).to.equal(WebSocket.OPEN);
    });

    // 3. Simulate a WebSocket disconnection
    cy.window().then((win) => {
      const ws = (win as any).webSocketConnection || (win as any).ws;
      if (ws) {
        // Simulate connection loss
        ws.close(1006, 'Connection lost');
      }
    });

    // 4. Verify that the application shows reconnection status
    cy.contains('Reconnecting', { timeout: 3000 }).should('be.visible');
    
    // 5. Wait for automatic reconnection
    cy.wait(2000);
    
    // 6. Verify connection is restored by sending another message
    cy.get('textarea').first().clear().type('Test message after reconnection{enter}');
    
    // 7. Verify the message appears (indicating successful reconnection)
    cy.contains('Test message after reconnection', { timeout: 10000 }).should('be.visible');
    
    // 8. Verify connection status is back to normal
    cy.contains('Reconnecting').should('not.exist');
  });
  
  it('should handle multiple reconnection attempts gracefully', () => {
    // Start with a message to establish baseline
    cy.get('textarea').first().type('Initial message before disruption{enter}');
    cy.contains('Initial message before disruption').should('be.visible');
    
    // Simulate multiple connection disruptions
    for (let i = 0; i < 3; i++) {
      cy.window().then((win) => {
        const ws = (win as any).webSocketConnection || (win as any).ws;
        if (ws) {
          ws.close(1006, `Connection lost attempt ${i + 1}`);
        }
      });
      
      // Wait for reconnection indicator
      cy.contains('Reconnecting', { timeout: 3000 }).should('be.visible');
      
      // Wait for reconnection
      cy.wait(1000);
    }
    
    // Verify final reconnection works
    cy.get('textarea').first().clear().type(`Final test message after ${3} disruptions{enter}`);
    cy.contains(`Final test message after ${3} disruptions`, { timeout: 10000 }).should('be.visible');
  });
  
  it('should queue messages during disconnection and send on reconnect', () => {
    // Simulate connection loss
    cy.window().then((win) => {
      const ws = (win as any).webSocketConnection || (win as any).ws;
      if (ws) {
        ws.close(1006, 'Connection lost for queuing test');
      }
    });
    
    // Wait for disconnection to be detected
    cy.wait(1000);
    
    // Try to send messages while disconnected
    cy.get('textarea').first().clear().type('Queued message 1{enter}');
    cy.wait(500);
    cy.get('textarea').first().clear().type('Queued message 2{enter}');
    
    // Wait for reconnection
    cy.wait(3000);
    
    // Verify queued messages appear after reconnection
    cy.contains('Queued message 1', { timeout: 10000 }).should('be.visible');
    cy.contains('Queued message 2', { timeout: 10000 }).should('be.visible');
  });
});