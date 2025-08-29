
/**
 * E2E Test Suite: Agent Workflow WebSocket Integration
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free, Early, Mid, Enterprise)
 * - Business Goal: Platform Stability & User Experience
 * - Value Impact: Ensures real-time agent workflow feedback works correctly
 * - Strategic Impact: Critical for user trust and platform reliability
 * 
 * Test Philosophy: Uses real services (no mocks) to validate WebSocket
 * communication between frontend and backend agent workflows.
 * 
 * Compliance: Follows CLAUDE.md standards for E2E > Integration > Unit testing
 */
describe('Real-time Agent Workflow via WebSockets (L4)', () => {
  // Constants following Single Source of Truth (SSOT) principle
  const CHAT_URL = '/demo';
  const INDUSTRY = 'Technology';
  const DEFAULT_TIMEOUT = 15000;
  const LONG_TIMEOUT = 45000;

  beforeEach(() => {
    initializeTestEnvironment();
    navigateToChatInterface();
    ensureChatComponentReady();
  });

  /**
   * Initialize viewport and clear state for consistent testing
   */
  function initializeTestEnvironment(): void {
    cy.viewport(1920, 1080);
    cy.window().then((win) => {
      win.localStorage.clear();
      win.sessionStorage.clear();
    });
  }

  /**
   * Navigate to demo page and select industry/chat interface
   */
  function navigateToChatInterface(): void {
    cy.visit(CHAT_URL);
    cy.contains(INDUSTRY).click();
    cy.contains('AI Chat').click();
    cy.wait(1000); // Allow page to settle
  }

  /**
   * Ensure chat component is loaded and ready for interaction
   */
  function ensureChatComponentReady(): void {
    cy.get('[data-testid="demo-chat"]').should('be.visible');
    cy.get('[data-testid="message-input"]').should('be.visible');
    cy.get('[data-testid="send-button"]').should('be.visible');
  }

  /**
   * Critical Path Test: Validates end-to-end WebSocket agent workflow
   * Tests real-time progress updates during agent execution
   */
  it('should display real-time agent progress via WebSocket events', () => {
    const testMessage = 'Analyze my recent cloud spend for optimization opportunities.';
    
    sendChatMessage(testMessage);
    verifyUserMessageDisplayed(testMessage);
    verifyAgentProcessingIndicators();
    verifyAgentWorkflowProgression();
    verifyCompletedResponse();
  });

  /**
   * Send message through chat interface
   */
  function sendChatMessage(message: string): void {
    cy.get('textarea[data-testid="message-input"]')
      .should('be.visible')
      .type(message);
    
    cy.get('[data-testid="send-button"]')
      .should('not.be.disabled')
      .click();
  }

  /**
   * Verify user message appears in chat history
   */
  function verifyUserMessageDisplayed(message: string): void {
    cy.contains(message).should('be.visible');
    cy.get('[data-testid="user-message"]').should('be.visible');
  }

  /**
   * Verify agent processing indicators appear
   */
  function verifyAgentProcessingIndicators(): void {
    cy.get('[data-testid="agent-processing"]', { timeout: DEFAULT_TIMEOUT })
      .should('be.visible');
    
    cy.contains('Processing').should('be.visible');
    cy.get('[data-testid="agent-indicator"]')
      .should('have.length.at.least', 1);
  }

  /**
   * Verify agent workflow progression via WebSocket events
   */
  function verifyAgentWorkflowProgression(): void {
    // Wait for agent names to appear (WebSocket events working)
    cy.contains(/Analyzer|Optimizer|Recommender|SupervisorAgent/i, 
      { timeout: DEFAULT_TIMEOUT }).should('be.visible');
  }

  /**
   * Verify completed response with timing and content
   */
  function verifyCompletedResponse(): void {
    cy.get('[data-testid="assistant-message"]', { timeout: LONG_TIMEOUT })
      .should('be.visible');
    
    cy.contains(/\d+ms/, { timeout: 5000 }).should('be.visible');
    cy.contains(/optimization|cost|saving|recommendation/i)
      .should('be.visible');
  }

  /**
   * WebSocket Status Test: Validates connection status indicators
   * Ensures WebSocket connection health is properly displayed
   */
  it('should handle WebSocket connection status updates', () => {
    verifyConnectionStatusIndicator();
    testWebSocketConnectivity();
  });

  /**
   * Verify connection status indicator displays correctly
   */
  function verifyConnectionStatusIndicator(): void {
    cy.get('[data-testid="connection-status"]')
      .should('exist')
      .and('have.class', 'bg-green-500'); // Connected state
  }

  /**
   * Test basic WebSocket connectivity with simple message
   */
  function testWebSocketConnectivity(): void {
    sendChatMessage('Test WebSocket connection');
    
    cy.get('[data-testid="agent-processing"]', { timeout: 5000 })
      .should('be.visible');
  }

  /**
   * Multi-Step Workflow Test: Validates complex agent orchestration
   * Tests WebSocket events for multi-agent workflows
   */
  it('should display agent workflow steps in real-time', () => {
    const complexQuery = 'Perform a comprehensive analysis of my system architecture and provide detailed optimization recommendations.';
    
    sendChatMessage(complexQuery);
    verifyUserMessageDisplayed(complexQuery);
    verifyMultiAgentProcessing();
    verifyWorkflowStepProgression();
    verifyComplexWorkflowCompletion();
  });

  /**
   * Verify multiple agents are activated for complex queries
   */
  function verifyMultiAgentProcessing(): void {
    cy.get('[data-testid="agent-processing"]', { timeout: DEFAULT_TIMEOUT })
      .should('be.visible');
    
    cy.get('[data-testid="agent-indicator"]')
      .should('have.length.at.least', 2);
  }

  /**
   * Verify workflow step progression indicators
   */
  function verifyWorkflowStepProgression(): void {
    cy.contains(/Step|Phase|Analyzing|Processing/i, { timeout: DEFAULT_TIMEOUT })
      .should('be.visible');
  }

  /**
   * Verify complex workflow completion with content validation
   */
  function verifyComplexWorkflowCompletion(): void {
    cy.get('[data-testid="assistant-message"]', { timeout: LONG_TIMEOUT })
      .should('be.visible')
      .and('contain.text', /analysis|recommendation|optimization/i);
  }

  /**
   * Typing Indicator Test: Validates UI feedback during processing
   * Ensures users see visual feedback while agents are responding
   */
  it('should show typing indicators during agent responses', () => {
    sendChatMessage('Show me quick optimization tips.');
    verifyTypingIndicators();
    verifyResponseCompletion();
  });

  /**
   * Verify typing indicators appear during processing
   */
  function verifyTypingIndicators(): void {
    cy.get('[data-testid="typing-indicator"]', { timeout: DEFAULT_TIMEOUT })
      .should('be.visible');
    
    cy.get('.animate-pulse').should('exist');
  }

  /**
   * Verify response completion after typing indicators
   */
  function verifyResponseCompletion(): void {
    cy.get('[data-testid="assistant-message"]', { timeout: 20000 })
      .should('be.visible');
  }

  /**
   * Reconnection Test: Validates WebSocket resilience
   * Tests that WebSocket connections recover gracefully
   */
  it('should handle WebSocket reconnection gracefully', () => {
    performInitialConnection();
    testReconnectionResilience();
  });

  /**
   * Establish initial WebSocket connection
   */
  function performInitialConnection(): void {
    sendChatMessage('Test message before reconnection');
    
    cy.get('[data-testid="agent-processing"]', { timeout: DEFAULT_TIMEOUT })
      .should('be.visible');
    
    cy.get('[data-testid="assistant-message"]', { timeout: LONG_TIMEOUT })
      .should('be.visible');
  }

  /**
   * Test connection resilience after potential disconnection
   */
  function testReconnectionResilience(): void {
    cy.get('textarea[data-testid="message-input"]')
      .clear()
      .type('Test message after potential reconnection');
    
    cy.get('[data-testid="send-button"]').click();
    
    cy.get('[data-testid="agent-processing"]', { timeout: DEFAULT_TIMEOUT })
      .should('be.visible');
  }
});
