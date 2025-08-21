
describe('Real-time Agent Workflow via WebSockets (L4)', () => {

  const CHAT_URL = '/chat';

  beforeEach(() => {
    cy.visit(CHAT_URL);
    cy.window().then((win) => {
      win.localStorage.clear();
    });
  });

  it('should display real-time agent progress via WebSocket events', () => {
    // 1. Initiate an agent workflow
    // NOTE: Replace with actual selectors and actions to start a workflow
    cy.get('textarea[aria-label="Message input"]').type('Analyze my recent cloud spend for optimization opportunities.');
    cy.get('button[aria-label="Send message"]').click();

    // 2. Listen for WebSocket events and assert UI updates
    cy.window().then((win) => {
      const store = win.useUnifiedChatStore?.getState();
      if (!store) {
        throw new Error('useUnifiedChatStore not found on window');
      }

      // Mock WebSocket events for testing purposes
      // In a real E2E test, these would come from the server
      store.handleWebSocketEvent({
        type: 'agent_started',
        payload: { agent_name: 'SupervisorAgent', run_id: 'run-123', timestamp: Date.now() }
      });

      cy.contains('SupervisorAgent').should('be.visible');

      store.handleWebSocketEvent({
        type: 'step_created',
        payload: { step_name: 'Analyzing spend data', step_number: 1, total_steps: 3, timestamp: Date.now() }
      });

      cy.contains('Step 1/3: Analyzing spend data').should('be.visible');

      store.handleWebSocketEvent({
        type: 'agent_finished',
        payload: { agent_name: 'SupervisorAgent', run_id: 'run-123', timestamp: Date.now(), result: 'Found 3 optimization opportunities.' }
      });

      cy.contains('Found 3 optimization opportunities.').should('be.visible');
    });
  });
});
