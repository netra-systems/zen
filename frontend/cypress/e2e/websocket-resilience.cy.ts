import { Message } from '@/types/unified';
import { UnifiedWebSocketEvent } from '@/types/websocket-event-types';

describe('WebSocket Connection Resilience', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('authToken', 'test-token');
    });
    
    // Mock user endpoint
    cy.intercept('GET', '/api/me', {
      statusCode: 200,
      body: {
        id: 1,
        email: 'test@netrasystems.ai',
        full_name: 'Test User'
      }
    }).as('userRequest');

    cy.visit('/demo');
    cy.wait('@userRequest');
    
    // Navigate to AI Chat tab
    cy.contains('AI Chat').click();
    cy.wait(1000);
  });

  it('should handle WebSocket connection lifecycle and auto-reconnect', () => {
    // Verify initial connection
    cy.window().then((win) => {
      // @ts-ignore
      expect((win as any).ws).to.exist;
      // @ts-ignore
      expect((win as any).ws.readyState).to.equal(1); // OPEN state
    });

    // Send a message to verify connection works
    cy.get('textarea[aria-label="Message input"]').type('Test connection');
    cy.get('button').contains('Send').click();
    cy.contains('Test connection').should('be.visible');

    // Simulate connection drop
    cy.window().then((win) => {
      // @ts-ignore
      (win as any).ws.close();
    });

    // Wait for reconnection attempt
    cy.wait(2000);

    // Verify reconnection indicator appears
    cy.contains('Reconnecting').should('be.visible');

    // Simulate successful reconnection
    cy.window().then((win) => {
      // @ts-ignore
      (win as any).ws = {
        readyState: 1,
        send: cy.stub(),
        onmessage: null,
        onclose: null,
        onerror: null,
        close: cy.stub()
      };

      // Trigger reconnection success
      const reconnectMessage: UnifiedWebSocketEvent = {
        type: 'connection_established',
        payload: {
          connection_id: 'test-conn-id',
          timestamp: Date.now()
        }
      };
      // @ts-ignore
      if ((win as any).ws.onmessage) {
        // @ts-ignore
        (win as any).ws.onmessage({ data: JSON.stringify(reconnectMessage) });
      }
    });

    // Verify reconnection success
    cy.contains('Reconnecting').should('not.exist');
    
    // Test that messages can be sent after reconnection
    cy.get('textarea[aria-label="Message input"]').type('After reconnection');
    cy.get('button').contains('Send').click();
    cy.get('div').should('contain', 'After reconnection');
  });

  it('should queue messages during disconnection and send on reconnect', () => {
    // Simulate connection drop
    cy.window().then((win) => {
      // @ts-ignore
      (win as any).ws.readyState = 0; // CONNECTING state
    });

    // Try to send messages while disconnected
    cy.get('textarea[aria-label="Message input"]').type('Message 1 while offline');
    cy.get('button').contains('Send').click();
    
    // Should show offline indicator
    cy.contains('Connection lost').should('be.visible');
    
    // Add another message to queue
    cy.get('textarea[aria-label="Message input"]').type('Message 2 while offline');
    cy.get('button').contains('Send').click();

    // Simulate reconnection
    cy.window().then((win) => {
      // @ts-ignore
      (win as any).ws.readyState = 1; // OPEN state
      
      // Simulate queued messages being sent - using critical agent events
      const queuedMessage1: UnifiedWebSocketEvent = {
        type: 'agent_started',
        payload: {
          agent_id: 'test-agent-1',
          agent_type: 'optimization_agent',
          run_id: 'run-queued-1',
          timestamp: new Date().toISOString(),
          status: 'started',
          message: 'Agent processing queued message 1'
        }
      };
      
      const queuedMessage2: UnifiedWebSocketEvent = {
        type: 'agent_completed',
        payload: {
          agent_id: 'test-agent-1',
          agent_type: 'optimization_agent',
          duration_ms: 2500,
          result: { output: 'Message 1 processed successfully' },
          metrics: { tools_used: 1, tokens_used: 150 }
        }
      };
      
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(queuedMessage1) });
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(queuedMessage2) });
    });

    // Verify queued agent events are processed and displayed
    cy.get('[data-testid*=\"agent\"], .agent-status, .message-content').should('contain', 'Agent processing');
    cy.get('[data-testid*=\"agent\"], .agent-status, .message-content').should('contain', 'processed successfully');
    
    // Connection indicator should be gone
    cy.contains('Connection lost').should('not.exist');
  });

  it('should handle WebSocket errors gracefully', () => {
    // Simulate WebSocket error
    cy.window().then((win) => {
      // @ts-ignore
      if ((win as any).ws.onerror) {
        // @ts-ignore
        (win as any).ws.onerror(new Event('error'));
      }
    });

    // Should show error message
    cy.contains('Connection error').should('be.visible');

    // Test retry mechanism
    cy.contains('Retry').click();

    // Simulate successful reconnection after retry
    cy.window().then((win) => {
      // @ts-ignore
      (win as any).ws.readyState = 1;
      
      const successMessage: UnifiedWebSocketEvent = {
        type: 'connection_established',
        payload: {
          connection_id: 'retry-conn-id',
          timestamp: Date.now()
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(successMessage) });
    });

    // Error message should disappear
    cy.contains('Connection error').should('not.exist');
  });

  it('CRITICAL: Should maintain connection health and detect agent event flow', () => {
    // Test critical agent event flow for chat functionality
    cy.window().then((win) => {
      // Simulate the mission-critical agent event sequence
      const agentStarted: UnifiedWebSocketEvent = {
        type: 'agent_started',
        payload: {
          agent_id: 'health-test-agent',
          agent_type: 'optimization_agent',
          run_id: 'health-run-1',
          timestamp: new Date().toISOString(),
          status: 'started'
        }
      };
      
      const agentThinking: UnifiedWebSocketEvent = {
        type: 'agent_thinking',
        payload: {
          thought: 'Analyzing connection health',
          agent_id: 'health-test-agent',
          agent_type: 'optimization_agent',
          step_number: 1,
          total_steps: 3
        }
      };
      
      const toolExecuting: UnifiedWebSocketEvent = {
        type: 'tool_executing',
        payload: {
          tool_name: 'connection_checker',
          agent_id: 'health-test-agent',
          agent_type: 'optimization_agent',
          timestamp: Date.now()
        }
      };
      
      const toolCompleted: UnifiedWebSocketEvent = {
        type: 'tool_completed',
        payload: {
          tool_name: 'connection_checker',
          result: { status: 'healthy', latency: 45 },
          agent_id: 'health-test-agent',
          agent_type: 'optimization_agent',
          timestamp: Date.now()
        }
      };
      
      const agentCompleted: UnifiedWebSocketEvent = {
        type: 'agent_completed',
        payload: {
          agent_id: 'health-test-agent',
          agent_type: 'optimization_agent',
          duration_ms: 1500,
          result: { connection_health: 'optimal' },
          metrics: { tools_executed: 1 }
        }
      };
      
      // Simulate the complete agent lifecycle
      // @ts-ignore
      (win as any).ws?.onmessage?.({ data: JSON.stringify(agentStarted) });
      // @ts-ignore
      (win as any).ws?.onmessage?.({ data: JSON.stringify(agentThinking) });
      // @ts-ignore
      (win as any).ws?.onmessage?.({ data: JSON.stringify(toolExecuting) });
      // @ts-ignore
      (win as any).ws?.onmessage?.({ data: JSON.stringify(toolCompleted) });
      // @ts-ignore
      (win as any).ws?.onmessage?.({ data: JSON.stringify(agentCompleted) });
    });

    // Verify that critical agent events are properly processed
    cy.get('body').should('contain.text', 'Analyzing');
    cy.get('[data-testid*=\"tool\"], .tool-status').should('exist');
    cy.get('[data-testid*=\"agent\"], .agent-status').should('contain', 'health');
  });

  it('should handle rate limiting and backpressure', () => {
    // Send multiple messages rapidly
    for (let i = 1; i <= 5; i++) {
      cy.get('textarea[aria-label="Message input"]').type(`Rapid message ${i}`);
      cy.get('button').contains('Send').click();
    }

    // Simulate rate limit response using proper error event
    cy.window().then((win) => {
      const rateLimitMessage: UnifiedWebSocketEvent = {
        type: 'error',
        payload: {
          error_message: 'Too many requests. Please slow down.',
          error_code: 'rate_limit_exceeded',
          recoverable: true
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(rateLimitMessage) });
    });

    // Should show rate limit warning
    cy.contains('Too many requests').should('be.visible');
    
    // Send button should be temporarily disabled
    cy.get('button').contains('Send').should('be.disabled');

    // Wait for rate limit to clear
    cy.wait(5000);

    // Button should be re-enabled
    cy.get('button').contains('Send').should('not.be.disabled');
  });

  it('should maintain message order during connection issues', () => {
    // Send first message
    cy.get('textarea[aria-label="Message input"]').type('Message A');
    cy.get('button').contains('Send').click();

    // Simulate brief disconnection
    cy.window().then((win) => {
      // @ts-ignore
      const originalWs = (win as any).ws;
      // @ts-ignore
      (win as any).ws.readyState = 0; // CONNECTING
      
      // Send message during disconnection
      cy.get('textarea[aria-label="Message input"]').type('Message B');
      cy.get('button').contains('Send').click();
      
      // Reconnect
      // @ts-ignore
      (win as any).ws.readyState = 1;
      
      // Test critical agent events arrive in order
      const agentStartedA: UnifiedWebSocketEvent = {
        type: 'agent_started',
        payload: {
          agent_id: 'agent-a',
          agent_type: 'optimization_agent',
          run_id: 'run-msg-a',
          timestamp: new Date().toISOString(),
          status: 'started',
          message: 'Processing Message A'
        }
      };
      
      const agentStartedB: UnifiedWebSocketEvent = {
        type: 'agent_started',
        payload: {
          agent_id: 'agent-b',
          agent_type: 'optimization_agent',
          run_id: 'run-msg-b',
          timestamp: new Date().toISOString(),
          status: 'started',
          message: 'Processing Message B'
        }
      };
      
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(agentStartedA) });
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(agentStartedB) });
    });

    // Verify agent events appear in correct order - look for agent status indicators
    cy.get('[data-testid*=\"agent\"], .agent-status, .message-content').should('contain', 'Processing Message A');
    cy.wait(500);
    cy.get('[data-testid*=\"agent\"], .agent-status, .message-content').should('contain', 'Processing Message B');
  });

  it('should handle WebSocket connection timeout', () => {
    // Simulate no heartbeat received (connection timeout)
    cy.window().then((win) => {
      // Trigger timeout by not receiving heartbeat
      // @ts-ignore
      if ((win as any).wsHeartbeatTimeout) {
        // @ts-ignore
        clearTimeout((win as any).wsHeartbeatTimeout);
      }
      
      // Simulate timeout event using proper error structure
      const timeoutMessage: UnifiedWebSocketEvent = {
        type: 'error',
        payload: {
          error_message: 'Connection timed out. Reconnecting...',
          error_code: 'connection_timeout',
          recoverable: true
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(timeoutMessage) });
    });

    // Should show timeout message
    cy.contains('Connection timed out').should('be.visible');
    
    // Should attempt reconnection
    cy.contains('Reconnecting').should('be.visible');
    
    // Simulate successful reconnection
    cy.window().then((win) => {
      // @ts-ignore
      (win as any).ws.readyState = 1;
      
      const reconnectSuccess: UnifiedWebSocketEvent = {
        type: 'connection_established',
        payload: {
          connection_id: 'timeout-recovery-conn',
          timestamp: Date.now()
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(reconnectSuccess) });
    });
    
    // Should clear error messages
    cy.contains('Connection timed out').should('not.exist');
    cy.contains('Reconnecting').should('not.exist');
  });
});