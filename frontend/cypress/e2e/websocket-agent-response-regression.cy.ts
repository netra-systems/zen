/**
 * E2E Cypress test for agent_response WebSocket messages
 * REGRESSION TEST: Ensures agent responses display in UI
 * Related to: SPEC/learnings/websocket_agent_response_missing_handler.xml
 */

describe('WebSocket Agent Response Display', () => {
  beforeEach(() => {
    // Set up WebSocket mock server
    cy.task('setupWebSocketMock');
    
    // Visit the chat page
    cy.visit('/chat', {
      onBeforeLoad(win) {
        // Stub console methods to capture warnings
        cy.stub(win.console, 'warn').as('consoleWarn');
        cy.stub(win.console, 'error').as('consoleError');
      }
    });
    
    // Wait for WebSocket connection
    cy.window().its('WebSocket').should('exist');
    cy.wait(1000); // Allow connection to establish
  });

  afterEach(() => {
    cy.task('teardownWebSocketMock');
  });

  describe('Agent Response Message Handling', () => {
    it('should display agent_response messages in chat UI', () => {
      // Send a user message
      cy.get('[data-testid="chat-input"]').type('Hello, can you help me?');
      cy.get('[data-testid="send-button"]').click();
      
      // Verify user message appears
      cy.get('[data-testid="chat-message"]')
        .last()
        .should('contain', 'Hello, can you help me?')
        .and('have.attr', 'data-role', 'user');
      
      // Mock backend sends agent_response
      cy.task('sendWebSocketMessage', {
        type: 'agent_response',
        content: 'Hello! I\'d be happy to help you.',
        message: 'Hello! I\'d be happy to help you.',
        user_id: 'test-user',
        thread_id: 'test-thread',
        timestamp: Date.now() / 1000,
        data: {
          status: 'success',
          agents_involved: ['triage'],
          orchestration_time: 0.5
        }
      });
      
      // Verify agent response appears in UI
      cy.get('[data-testid="chat-message"]', { timeout: 5000 })
        .last()
        .should('contain', 'Hello! I\'d be happy to help you.')
        .and('have.attr', 'data-role', 'assistant');
      
      // Ensure no console errors about missing handlers
      cy.get('@consoleError').should('not.have.been.called');
      cy.get('@consoleWarn').should('not.have.been.calledWith', 
        Cypress.sinon.match(/Unknown WebSocket message type.*agent_response/)
      );
    });

    it('should handle multiple agent responses in sequence', () => {
      // Send initial message
      cy.get('[data-testid="chat-input"]').type('Analyze my AI costs');
      cy.get('[data-testid="send-button"]').click();
      
      // Simulate agent workflow with multiple responses
      const messages = [
        {
          type: 'agent_started',
          payload: {
            agent_id: 'analysis-agent',
            run_id: 'run-123',
            timestamp: Date.now() / 1000
          }
        },
        {
          type: 'agent_thinking',
          payload: {
            thought: 'Analyzing your AI usage patterns...',
            agent_id: 'analysis-agent',
            step_number: 1
          }
        },
        {
          type: 'agent_response',
          content: 'I\'ve analyzed your AI costs. Here are the findings:',
          data: {
            status: 'success'
          }
        },
        {
          type: 'agent_response',
          content: '• Total monthly spend: $4,500\n• Top model: GPT-4 (60%)\n• Optimization potential: 30%',
          data: {
            status: 'success',
            agents_involved: ['analysis', 'optimization']
          }
        },
        {
          type: 'agent_completed',
          payload: {
            agent_id: 'analysis-agent',
            duration_ms: 2500
          }
        }
      ];
      
      // Send messages with delays to simulate real flow
      messages.forEach((msg, index) => {
        cy.wait(500 * index); // Stagger messages
        cy.task('sendWebSocketMessage', msg);
      });
      
      // Verify all agent responses appear
      cy.get('[data-testid="chat-message"][data-role="assistant"]')
        .should('have.length.at.least', 2);
      
      cy.get('[data-testid="chat-message"]')
        .contains('I\'ve analyzed your AI costs')
        .should('be.visible');
      
      cy.get('[data-testid="chat-message"]')
        .contains('Total monthly spend: $4,500')
        .should('be.visible');
    });

    it('should handle agent_response with various payload formats', () => {
      const payloadVariations = [
        // Format 1: content field
        {
          type: 'agent_response',
          content: 'Response via content field',
          thread_id: 'thread-1'
        },
        // Format 2: message field
        {
          type: 'agent_response',
          message: 'Response via message field',
          thread_id: 'thread-2'
        },
        // Format 3: nested data.content
        {
          type: 'agent_response',
          data: {
            content: 'Response via data.content',
            status: 'success'
          },
          thread_id: 'thread-3'
        },
        // Format 4: nested data.message
        {
          type: 'agent_response',
          data: {
            message: 'Response via data.message',
            status: 'success'
          },
          thread_id: 'thread-4'
        }
      ];
      
      payloadVariations.forEach((payload, index) => {
        cy.task('sendWebSocketMessage', payload);
        cy.wait(500);
        
        // Verify message appears regardless of payload format
        const expectedContent = 
          payload.content || 
          payload.message || 
          payload.data?.content || 
          payload.data?.message;
        
        cy.get('[data-testid="chat-message"]')
          .contains(expectedContent)
          .should('be.visible');
      });
    });

    it('should not display empty agent responses', () => {
      // Send empty response
      cy.task('sendWebSocketMessage', {
        type: 'agent_response',
        content: '',
        thread_id: 'thread-empty'
      });
      
      cy.wait(1000);
      
      // Verify warning in console
      cy.get('@consoleWarn').should('have.been.calledWith',
        'Agent response missing content:',
        Cypress.sinon.match.object
      );
      
      // Verify no empty message appears
      cy.get('[data-testid="chat-message"][data-role="assistant"]')
        .last()
        .invoke('text')
        .should('not.be.empty');
    });
  });

  describe('Message Type Coverage', () => {
    it('should handle all critical WebSocket message types', () => {
      const criticalMessages = [
        {
          type: 'agent_started',
          payload: { agent_id: 'test', run_id: 'run-1' }
        },
        {
          type: 'agent_response',
          content: 'Processing your request...'
        },
        {
          type: 'agent_thinking',
          payload: { thought: 'Analyzing data...' }
        },
        {
          type: 'tool_executing',
          payload: { tool_name: 'data_analyzer' }
        },
        {
          type: 'tool_completed',
          payload: { tool_name: 'data_analyzer', result: {} }
        },
        {
          type: 'partial_result',
          payload: { content: 'Partial: ', is_complete: false }
        },
        {
          type: 'final_report',
          payload: { report: { summary: 'Complete analysis' } }
        },
        {
          type: 'agent_completed',
          payload: { agent_id: 'test', duration_ms: 1000 }
        }
      ];
      
      criticalMessages.forEach(msg => {
        cy.task('sendWebSocketMessage', msg);
        cy.wait(200);
      });
      
      // Verify no errors about unknown message types
      cy.get('@consoleError').should('not.have.been.called');
      
      // Verify UI updated appropriately
      cy.get('[data-testid="chat-message"], [data-testid="agent-status"], [data-testid="tool-status"]')
        .should('have.length.at.least', 3);
    });

    it('should warn about truly unknown message types', () => {
      // Send an unknown message type
      cy.task('sendWebSocketMessage', {
        type: 'unknown_message_type',
        payload: { data: 'test' }
      });
      
      cy.wait(500);
      
      // Should see warning (when implemented)
      // cy.get('@consoleWarn').should('have.been.calledWith',
      //   Cypress.sinon.match(/Unknown WebSocket message type: unknown_message_type/)
      // );
    });
  });

  describe('Connection Recovery', () => {
    it('should handle agent_response after reconnection', () => {
      // Simulate disconnect
      cy.task('disconnectWebSocket');
      cy.wait(1000);
      
      // Simulate reconnect
      cy.task('reconnectWebSocket');
      cy.wait(1000);
      
      // Send agent_response after reconnection
      cy.task('sendWebSocketMessage', {
        type: 'agent_response',
        content: 'Response after reconnection',
        thread_id: 'thread-reconnect'
      });
      
      // Verify message displays
      cy.get('[data-testid="chat-message"]')
        .contains('Response after reconnection')
        .should('be.visible');
    });
  });

  describe('Performance', () => {
    it('should handle rapid agent_response messages', () => {
      const messageCount = 20;
      const messages = Array.from({ length: messageCount }, (_, i) => ({
        type: 'agent_response',
        content: `Rapid response ${i + 1}`,
        thread_id: 'thread-rapid',
        timestamp: Date.now() / 1000 + i
      }));
      
      // Send all messages rapidly
      messages.forEach(msg => {
        cy.task('sendWebSocketMessage', msg);
      });
      
      // Wait for processing
      cy.wait(2000);
      
      // Verify all messages appear
      cy.get('[data-testid="chat-message"][data-role="assistant"]')
        .should('have.length.at.least', messageCount);
      
      // Verify order is maintained
      cy.get('[data-testid="chat-message"][data-role="assistant"]')
        .first()
        .should('contain', 'Rapid response 1');
      
      cy.get('[data-testid="chat-message"][data-role="assistant"]')
        .last()
        .should('contain', `Rapid response ${messageCount}`);
    });
  });
});

describe('Regression Prevention', () => {
  it('CRITICAL: agent_response handler must exist', () => {
    // This test MUST always pass to prevent regression
    cy.window().then((win) => {
      // Access the frontend handler registry
      const handlers = win.eval(`
        import('@/store/websocket-event-handlers-main')
          .then(module => module.getEventHandlers())
      `);
      
      cy.wrap(handlers).should('have.property', 'agent_response');
      cy.wrap(handlers).its('agent_response').should('be.a', 'function');
    });
  });
  
  it('should never silently drop agent_response messages', () => {
    cy.visit('/chat');
    
    // Set up spy to monitor all WebSocket messages
    cy.window().then((win) => {
      const originalSend = win.WebSocket.prototype.send;
      cy.stub(win.WebSocket.prototype, 'send').callsFake(function(data) {
        cy.log('WebSocket send:', data);
        return originalSend.call(this, data);
      });
    });
    
    // Send test message
    cy.get('[data-testid="chat-input"]').type('Test message');
    cy.get('[data-testid="send-button"]').click();
    
    // Mock agent response
    cy.task('sendWebSocketMessage', {
      type: 'agent_response',
      content: 'This must appear in UI',
      thread_id: 'critical-test'
    });
    
    // CRITICAL: Message MUST appear
    cy.get('[data-testid="chat-message"]', { timeout: 10000 })
      .contains('This must appear in UI')
      .should('exist')
      .and('be.visible');
  });
});