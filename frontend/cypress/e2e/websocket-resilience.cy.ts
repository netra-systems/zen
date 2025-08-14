import { Message } from '@/types';
import { WebSocketMessage } from '@/types/chat';

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
        email: 'test@netra.ai',
        full_name: 'Test User'
      }
    }).as('userRequest');

    cy.visit('/chat');
    cy.wait('@userRequest');
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
      const reconnectMessage: WebSocketMessage = {
        type: 'message',
        payload: {
          status: 'connected',
          message: 'WebSocket reconnected successfully'
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
      
      // Simulate queued messages being sent
      const queuedMessage1: WebSocketMessage = {
        type: 'message',
        payload: {
          id: 'queued-1',
          created_at: new Date().toISOString(),
          content: 'Message 1 while offline',
          type: 'user',
          displayed_to_user: true
        } as Message
      };
      
      const queuedMessage2: WebSocketMessage = {
        type: 'message',
        payload: {
          id: 'queued-2',
          created_at: new Date().toISOString(),
          content: 'Message 2 while offline',
          type: 'user',
          displayed_to_user: true
        } as Message
      };
      
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(queuedMessage1) });
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(queuedMessage2) });
    });

    // Verify queued messages are displayed
    cy.get('div').should('contain', 'Message 1 while offline');
    cy.get('div').should('contain', 'Message 2 while offline');
    
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
      
      const successMessage: WebSocketMessage = {
        type: 'message',
        payload: {
          status: 'connected',
          message: 'Successfully reconnected'
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(successMessage) });
    });

    // Error message should disappear
    cy.contains('Connection error').should('not.exist');
  });

  it('should handle heartbeat/ping-pong for connection health', () => {
    // Simulate receiving a ping
    cy.window().then((win) => {
      const pingMessage: WebSocketMessage = {
        type: 'message',
        payload: {
          timestamp: Date.now()
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(pingMessage) });
    });

    // Verify pong is sent (checking that send was called)
    cy.window().then((win) => {
      // @ts-ignore
      const sendSpy = cy.spy((win as any).ws, 'send');
      
      // Trigger another ping to capture the pong
      const pingMessage: WebSocketMessage = {
        type: 'message',
        payload: {
          timestamp: Date.now()
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(pingMessage) });
      
      // Verify pong was sent
      expect(sendSpy).to.have.been.calledWith(
        Cypress.sinon.match((value: string) => {
          const parsed = JSON.parse(value);
          return parsed.type === 'pong';
        })
      );
    });
  });

  it('should handle rate limiting and backpressure', () => {
    // Send multiple messages rapidly
    for (let i = 1; i <= 5; i++) {
      cy.get('textarea[aria-label="Message input"]').type(`Rapid message ${i}`);
      cy.get('button').contains('Send').click();
    }

    // Simulate rate limit response
    cy.window().then((win) => {
      const rateLimitMessage: WebSocketMessage = {
        type: 'error',
        payload: {
          error: 'rate_limit_exceeded',
          message: 'Too many requests. Please slow down.',
          retry_after: 5
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
      
      // Messages should arrive in order
      const messageA: WebSocketMessage = {
        type: 'message',
        payload: {
          id: 'msg-a',
          created_at: new Date().toISOString(),
          content: 'Message A',
          type: 'user',
          displayed_to_user: true,
          sequence: 1
        } as Message
      };
      
      const messageB: WebSocketMessage = {
        type: 'message',
        payload: {
          id: 'msg-b',
          created_at: new Date().toISOString(),
          content: 'Message B',
          type: 'user',
          displayed_to_user: true,
          sequence: 2
        } as Message
      };
      
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(messageA) });
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(messageB) });
    });

    // Verify messages appear in correct order
    cy.get('div').eq(0).should('contain', 'Message A');
    cy.get('div').eq(1).should('contain', 'Message B');
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
      
      // Simulate timeout event
      const timeoutMessage: WebSocketMessage = {
        type: 'error',
        payload: {
          error: 'connection_timeout',
          message: 'Connection timed out. Reconnecting...'
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
      
      const reconnectSuccess: WebSocketMessage = {
        type: 'message',
        payload: {
          status: 'connected',
          message: 'Reconnected after timeout'
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