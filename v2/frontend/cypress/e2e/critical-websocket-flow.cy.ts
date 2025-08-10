describe('Critical WebSocket Communication Flow', () => {
  const testUser = {
    email: 'test@netra.ai',
    password: 'TestPassword123!'
  };

  beforeEach(() => {
    // Login first
    cy.clearLocalStorage();
    cy.clearCookies();
    cy.visit('/auth/login');
    cy.get('input[type="email"]').type(testUser.email);
    cy.get('input[type="password"]').type(testUser.password);
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/chat');
  });

  it('should establish WebSocket connection and handle messages', () => {
    // 1. Verify WebSocket connection is established
    cy.window().its('WebSocket').should('exist');
    
    // 2. Wait for connection to be ready
    cy.wait(1000); // Give WebSocket time to connect
    
    // 3. Find chat input and send button
    cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
      .should('be.visible')
      .as('chatInput');
    
    cy.get('button').contains(/send|submit/i)
      .should('be.visible')
      .as('sendButton');
    
    // 4. Send a simple message
    const testMessage = 'What are the key optimization strategies for reducing LLM latency?';
    cy.get('@chatInput').type(testMessage);
    cy.get('@sendButton').click();
    
    // 5. Verify message appears in chat
    cy.contains(testMessage).should('be.visible');
    
    // 6. Wait for and verify agent response
    cy.contains(/analyzing|processing|thinking/i, { timeout: 10000 }).should('be.visible');
    
    // 7. Verify response is received
    cy.contains(/latency|optimization|strategy/i, { timeout: 30000 }).should('be.visible');
    
    // 8. Send another message to test message flow
    const followUpMessage = 'Can you provide specific examples?';
    cy.get('@chatInput').clear().type(followUpMessage);
    cy.get('@sendButton').click();
    
    // 9. Verify follow-up message and response
    cy.contains(followUpMessage).should('be.visible');
    cy.contains(/example|specific|implementation/i, { timeout: 30000 }).should('be.visible');
  });

  it('should handle WebSocket reconnection after disconnect', () => {
    // 1. Establish initial connection
    cy.window().its('WebSocket').should('exist');
    cy.wait(1000);
    
    // 2. Send initial message to verify connection
    const initialMessage = 'Test connection message';
    cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
      .type(initialMessage);
    cy.get('button').contains(/send|submit/i).click();
    cy.contains(initialMessage).should('be.visible');
    
    // 3. Simulate network disconnect
    cy.window().then((win) => {
      const ws = (win as any).ws || (win as any).websocket || (win as any).socket;
      if (ws && ws.close) {
        ws.close();
      }
    });
    
    // 4. Wait for reconnection indicator
    cy.contains(/reconnecting|disconnected|connecting/i, { timeout: 5000 }).should('be.visible');
    
    // 5. Wait for automatic reconnection
    cy.contains(/connected|online/i, { timeout: 15000 }).should('be.visible');
    
    // 6. Verify functionality after reconnection
    const reconnectMessage = 'Message after reconnection';
    cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
      .clear()
      .type(reconnectMessage);
    cy.get('button').contains(/send|submit/i).click();
    
    // 7. Verify message is sent and response received
    cy.contains(reconnectMessage).should('be.visible');
    cy.contains(/processing|analyzing|response/i, { timeout: 30000 }).should('be.visible');
  });

  it('should handle rapid message sending and queuing', () => {
    // 1. Prepare multiple messages
    const messages = [
      'First optimization query',
      'Second optimization query', 
      'Third optimization query'
    ];
    
    // 2. Send messages rapidly
    messages.forEach((message) => {
      cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
        .clear()
        .type(message);
      cy.get('button').contains(/send|submit/i).click();
      cy.wait(100); // Small delay between messages
    });
    
    // 3. Verify all messages appear in chat
    messages.forEach((message) => {
      cy.contains(message).should('be.visible');
    });
    
    // 4. Verify responses are received for each message
    cy.get('[class*="message"], [class*="response"], [class*="agent"]', { timeout: 60000 })
      .should('have.length.at.least', messages.length * 2); // User messages + agent responses
  });

  it('should maintain WebSocket connection during long operations', () => {
    // 1. Send a complex query that takes time to process
    const complexQuery = 'Perform a comprehensive analysis of all optimization strategies for transformer models including attention mechanisms, KV cache optimization, quantization techniques, and deployment strategies';
    
    cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
      .type(complexQuery);
    cy.get('button').contains(/send|submit/i).click();
    
    // 2. Verify message is sent
    cy.contains(complexQuery).should('be.visible');
    
    // 3. Verify processing indicators appear
    cy.contains(/analyzing|processing|generating/i, { timeout: 10000 }).should('be.visible');
    
    // 4. Monitor for heartbeat/keep-alive (connection should stay active)
    let disconnectDetected = false;
    cy.on('window:alert', (text) => {
      if (text.includes('disconnect') || text.includes('offline')) {
        disconnectDetected = true;
      }
    });
    
    // 5. Wait for response (long timeout for complex query)
    cy.contains(/optimization|transformer|attention/i, { timeout: 90000 }).should('be.visible');
    
    // 6. Verify no disconnect occurred
    cy.wrap(null).then(() => {
      expect(disconnectDetected).to.be.false;
    });
    
    // 7. Send follow-up to verify connection still active
    const followUp = 'Summarize the key points';
    cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
      .clear()
      .type(followUp);
    cy.get('button').contains(/send|submit/i).click();
    
    // 8. Verify follow-up works
    cy.contains(followUp).should('be.visible');
    cy.contains(/summary|key point/i, { timeout: 30000 }).should('be.visible');
  });
});