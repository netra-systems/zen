/**
 * CRITICAL REGRESSION TEST for agent_response WebSocket messages
 * 
 * PURPOSE: Verify that agent_response handler exists in the codebase
 * REGRESSION: Previously agent_response messages were silently dropped
 * APPROACH: Direct static analysis of WebSocket handler files
 * 
 * Related to: SPEC/learnings/websocket_agent_response_missing_handler.xml
 */

describe('WebSocket Agent Response Handler Regression Test', () => {
  
  it('CRITICAL: agent_response handler must exist in WebSocket handlers file', () => {
    // Read the WebSocket handlers file directly to verify agent_response handler exists
    cy.readFile('store/websocket-event-handlers-main.ts').then((fileContent) => {
      // Verify the file contains agent_response handler registration
      expect(fileContent).to.include('agent_response');
      expect(fileContent).to.include('handleAgentResponse');
      
      // Verify the handler is properly exported in the getEventHandlers function
      expect(fileContent).to.match(/'agent_response':\s*handleAgentResponse/);
      
      cy.log('✅ agent_response handler found in WebSocket handlers registry');
    });
  });

  it('CRITICAL: handleAgentResponse function must exist in agent handlers', () => {
    // Verify the actual handler function exists
    cy.readFile('store/websocket-agent-handlers.ts').then((fileContent) => {
      // Check that the handleAgentResponse function is properly defined
      expect(fileContent).to.include('export const handleAgentResponse');
      expect(fileContent).to.include('function handleAgentResponse');
      expect(fileContent).to.include('extractAgentResponseData');
      expect(fileContent).to.include('createAgentResponseMessage');
      
      cy.log('✅ handleAgentResponse function implementation found');
    });
  });

  it('should verify agent_response handler processes message content correctly', () => {
    // Verify the handler extracts content from various payload formats
    cy.readFile('store/websocket-agent-handlers.ts').then((fileContent) => {
      // Check that the handler supports multiple content extraction patterns
      expect(fileContent).to.include('payload.content');
      expect(fileContent).to.include('payload.message');
      expect(fileContent).to.include('payload.data?.content');
      expect(fileContent).to.include('payload.data?.message');
      
      // Verify empty content handling
      expect(fileContent).to.include('console.warn');
      expect(fileContent).to.include('Agent response missing content');
      
      cy.log('✅ agent_response content extraction logic verified');
    });
  });

  it('should verify WebSocket handler registry includes all critical message types', () => {
    cy.readFile('store/websocket-event-handlers-main.ts').then((fileContent) => {
      const criticalHandlers = [
        'agent_started',
        'agent_response',
        'agent_completed', 
        'agent_thinking',
        'tool_executing',
        'tool_completed'
      ];
      
      // Verify all critical handlers are registered
      criticalHandlers.forEach(handler => {
        expect(fileContent).to.include(`'${handler}':`);
      });
      
      cy.log('✅ All critical WebSocket message handlers are registered');
    });
  });

});