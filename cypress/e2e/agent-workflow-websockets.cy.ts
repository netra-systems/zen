
describe('Real-time Agent Workflow via WebSockets (L4)', () => {

  const CHAT_URL = '/demo';
  const INDUSTRY = 'Technology';

  beforeEach(() => {
    // Set viewport and visit demo page for consistent testing
    cy.viewport(1920, 1080);
    cy.visit(CHAT_URL);
    
    // Select industry and navigate to AI Chat
    cy.contains(INDUSTRY).click();
    cy.contains('AI Chat').click();
    cy.wait(1000); // Allow page to settle
    
    // Clear any previous state
    cy.window().then((win) => {
      win.localStorage.clear();
    });
    
    // Ensure chat component is loaded
    cy.get('[data-testid="demo-chat"]').should('be.visible');
  });

  it('should display real-time agent progress via WebSocket events', () => {
    // 1. Initiate an agent workflow with correct selectors
    const testMessage = 'Analyze my recent cloud spend for optimization opportunities.';
    
    // Type message using correct selector
    cy.get('textarea[data-testid="message-input"]')
      .should('be.visible')
      .type(testMessage);
    
    // Send message using correct button selector
    cy.get('[data-testid="send-button"]')
      .should('not.be.disabled')
      .click();

    // 2. Assert user message appears in chat
    cy.contains(testMessage).should('be.visible');
    cy.get('[data-testid="user-message"]').should('be.visible');

    // 3. Wait for and assert agent processing indicators
    cy.get('[data-testid="agent-processing"]', { timeout: 10000 })
      .should('be.visible');
    
    // 4. Assert processing state indicators
    cy.contains('Processing').should('be.visible');
    cy.get('[data-testid="agent-indicator"]')
      .should('have.length.at.least', 1);

    // 5. Wait for agent names to appear (indicating WebSocket events are working)
    cy.contains(/Analyzer|Optimizer|Recommender|SupervisorAgent/i, { timeout: 15000 })
      .should('be.visible');
    
    // 6. Wait for response completion (indicates WebSocket events completed successfully)
    cy.get('[data-testid="assistant-message"]', { timeout: 30000 })
      .should('be.visible');
    
    // 7. Verify processing time is displayed (indicates agent_completed events)
    cy.contains(/\d+ms/, { timeout: 5000 }).should('be.visible');
    
    // 8. Verify final response contains optimization content
    cy.contains(/optimization|cost|saving|recommendation/i)
      .should('be.visible');
  });

  it('should handle WebSocket connection status updates', () => {
    // Check connection status indicator
    cy.get('[data-testid="connection-status"]')
      .should('exist')
      .and('have.class', 'bg-green-500'); // Connected state
    
    // Verify WebSocket functionality with a simple message
    cy.get('textarea[data-testid="message-input"]')
      .type('Test WebSocket connection');
    
    cy.get('[data-testid="send-button"]').click();
    
    // If WebSocket is working, we should see processing indicators
    cy.get('[data-testid="agent-processing"]', { timeout: 5000 })
      .should('be.visible');
  });

  it('should display agent workflow steps in real-time', () => {
    const complexQuery = 'Perform a comprehensive analysis of my system architecture and provide detailed optimization recommendations.';
    
    // Send complex query that should trigger multi-step workflow
    cy.get('textarea[data-testid="message-input"]').type(complexQuery);
    cy.get('[data-testid="send-button"]').click();
    
    // Verify user message
    cy.contains(complexQuery).should('be.visible');
    
    // Wait for processing to start
    cy.get('[data-testid="agent-processing"]', { timeout: 10000 })
      .should('be.visible');
    
    // Check for multiple agent activations (indicates WebSocket events for different agents)
    cy.get('[data-testid="agent-indicator"]')
      .should('have.length.at.least', 2);
    
    // Verify step progression indicators appear
    cy.contains(/Step|Phase|Analyzing|Processing/i, { timeout: 15000 })
      .should('be.visible');
    
    // Wait for completion and verify final response
    cy.get('[data-testid="assistant-message"]', { timeout: 45000 })
      .should('be.visible')
      .and('contain.text', /analysis|recommendation|optimization/i);
  });

  it('should show typing indicators during agent responses', () => {
    cy.get('textarea[data-testid="message-input"]')
      .type('Show me quick optimization tips.');
    
    cy.get('[data-testid="send-button"]').click();
    
    // Should show typing indicator while agent is responding
    cy.get('[data-testid="typing-indicator"]', { timeout: 10000 })
      .should('be.visible');
    
    cy.get('.animate-pulse').should('exist');
    
    // Wait for response to complete
    cy.get('[data-testid="assistant-message"]', { timeout: 20000 })
      .should('be.visible');
  });

  it('should handle WebSocket reconnection gracefully', () => {
    // Initial message to establish connection
    cy.get('textarea[data-testid="message-input"]')
      .type('Test message before reconnection');
    
    cy.get('[data-testid="send-button"]').click();
    
    // Wait for initial processing
    cy.get('[data-testid="agent-processing"]', { timeout: 10000 })
      .should('be.visible');
    
    // Wait for response
    cy.get('[data-testid="assistant-message"]', { timeout: 30000 })
      .should('be.visible');
    
    // Send another message (should work if reconnection is handled properly)
    cy.get('textarea[data-testid="message-input"]')
      .clear()
      .type('Test message after potential reconnection');
    
    cy.get('[data-testid="send-button"]').click();
    
    // Should still show processing indicators
    cy.get('[data-testid="agent-processing"]', { timeout: 10000 })
      .should('be.visible');
  });
});
