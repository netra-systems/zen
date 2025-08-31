import {
  setupThreadTestEnvironment,
  mockNewThreadCreation,
  MockThread
} from './thread-test-helpers';

describe('Thread Management - Simplified', () => {
  beforeEach(() => {
    setupThreadTestEnvironment();
  });

  it('should allow sending messages in chat', () => {
    // Wait for chat interface to load - updated selector to match current implementation
    cy.get('[data-testid="message-input"]', { timeout: 10000 }).should('exist');
    
    // Type and send a message with correct selectors
    const testMessage = 'Test thread message';
    cy.get('[data-testid="message-input"] textarea').type(testMessage, { force: true });
    cy.get('[data-testid="send-button"]').click({ force: true });
    
    // Verify message appears
    cy.contains(testMessage, { timeout: 5000 }).should('be.visible');
  });

  it('should handle multiple messages in sequence', () => {
    // Wait for input to be ready - using correct selector
    cy.get('[data-testid="message-input"]', { timeout: 10000 }).should('exist');
    
    // Send first message
    const firstMessage = 'First message in thread';
    cy.get('[data-testid="message-input"] textarea').type(firstMessage, { force: true });
    cy.get('[data-testid="send-button"]').click({ force: true });
    
    cy.contains(firstMessage, { timeout: 5000 }).should('be.visible');
    
    // Send second message
    const secondMessage = 'Second message in thread';
    cy.get('[data-testid="message-input"] textarea').clear({ force: true }).type(secondMessage, { force: true });
    cy.get('[data-testid="send-button"]').click({ force: true });
    
    cy.contains(secondMessage, { timeout: 5000 }).should('be.visible');
    
    // Both messages should be visible
    cy.contains(firstMessage).should('be.visible');
    cy.contains(secondMessage).should('be.visible');
  });

  it('should create and switch to new thread', () => {
    // Mock new thread creation
    const newThread: MockThread = {
      id: 'thread-new',
      title: 'New Chat',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      user_id: 1,
      message_count: 0
    };
    mockNewThreadCreation(newThread);
    
    // Verify chat sidebar is visible (it's automatically shown in the layout)
    cy.get('[data-testid="chat-sidebar"]', { timeout: 10000 }).should('be.visible');
    
    // Create new thread using the actual "New Chat" button
    cy.get('[data-testid="new-chat-button"]').should('be.visible').click();
    
    // Send a message in new thread
    const testMessage = 'Start new conversation';
    cy.get('[data-testid="message-input"] textarea', { timeout: 10000 }).type(testMessage, { force: true });
    cy.get('[data-testid="send-button"]').click({ force: true });
    
    // Verify message appears
    cy.contains(testMessage, { timeout: 5000 }).should('be.visible');
  });

  it('should maintain conversation context with WebSocket events', () => {
    // Setup WebSocket mock
    cy.window().then((win: any) => {
      if (!(win as any).ws) {
        (win as any).ws = {
          readyState: 1,
          send: cy.stub(),
          close: cy.stub(),
          onmessage: null
        };
      }
    });
    
    // Send an optimization request
    const request = 'Optimize my LLM pipeline';
    cy.get('[data-testid="message-input"] textarea', { timeout: 10000 }).type(request, { force: true });
    cy.get('[data-testid="send-button"]').click({ force: true });
    
    cy.contains(request, { timeout: 5000 }).should('be.visible');
    
    // Simulate agent response using WebSocket
    cy.window().then((win) => {
      const response = {
        type: 'message',
        payload: {
          id: 'msg-1',
          content: 'I can help optimize your LLM pipeline. Let me analyze your requirements.',
          type: 'agent',
          sub_agent_name: 'OptimizationsCoreSubAgent',
          displayed_to_user: true,
          thread_id: 'current-thread',
          created_at: new Date().toISOString()
        }
      };
      
      // Trigger message handler if WebSocket exists
      if ((win as any).ws && (win as any).ws.onmessage) {
        (win as any).ws.onmessage({ data: JSON.stringify(response) });
      }
    });
    
    // Check if agent response appears
    cy.contains('optimize your LLM pipeline', { timeout: 5000 }).should('exist');
  });
});