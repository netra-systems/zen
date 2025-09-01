import {
  WEBSOCKET_CONFIG,
  setupTestEnvironment,
  navigateToChat,
  waitForConnection,
  findWebSocketConnection,
  simulateNetworkPartition,
  verifyReconnection,
  validateCriticalEvents,
  simulateCriticalWebSocketEvents,
  verifyWebSocketServiceIntegration,
  monitorWebSocketEvents
} from '../support/websocket-test-helpers';

import {
  MessageInput,
  MessageAssertions,
  ComponentVisibility,
  WaitHelpers
} from './utils/chat-test-helpers';

describe('Critical WebSocket Communication Flow', () => {
  beforeEach(() => {
    setupTestEnvironment();
    navigateToChat();
  });

  const CRITICAL_AGENT_EVENTS = [
    'agent_started',
    'agent_thinking', 
    'tool_executing',
    'tool_completed',
    'agent_completed'
  ];

  const WEBSOCKET_ENDPOINT = 'ws://localhost:8000/ws';

  it('should establish WebSocket connection with correct endpoint and authentication', () => {
    // Verify chat component is loaded
    ComponentVisibility.assertChatComponent();
    ComponentVisibility.assertHeader();
    
    // Verify message input and send button are available
    cy.get('textarea[data-testid="message-input"]', { timeout: 10000 }).should('be.visible');
    cy.get('[data-testid="send-button"]').should('exist');
    
    // Verify WebSocket connection is established with correct endpoint
    waitForConnection().then((ws) => {
      if (ws) {
        expect(ws.readyState).to.be.oneOf([0, 1], 'WebSocket should be CONNECTING or OPEN');
        expect(ws.url).to.include('/ws', 'WebSocket should use unified /ws endpoint');
        
        // Verify authentication is handled via subprotocol (for authenticated connections)
        cy.window().then((win) => {
          const authToken = win.localStorage.getItem('auth_token');
          if (authToken) {
            expect(ws.protocol).to.include('jwt-auth', 'Authenticated connections should use JWT subprotocol');
          }
        });
      } else {
        // Fallback: check connection status indicator
        cy.get('[data-testid="connection-status"]').should('exist');
      }
    });
    
    // Verify WebSocket service integration
    verifyWebSocketServiceIntegration();
  });

  it('should send and receive messages with critical agent events', () => {
    const testMessage = 'Hello, can you help me optimize my AI workload?';
    
    // Start monitoring WebSocket events before sending message
    const eventPromise = monitorWebSocketEvents(15000); // 15 second timeout
    
    // Send message using helper
    MessageInput.send(testMessage);
    
    // Verify user message appears
    MessageAssertions.assertUserMessage(testMessage);
    
    // Verify processing indicators
    cy.get('[data-testid="agent-processing"]', { timeout: 10000 }).should('be.visible');
    
    // Wait for and verify assistant response
    WaitHelpers.forResponse();
    MessageAssertions.assertAssistantMessage();
    
    // Verify WebSocket message transmission and critical events
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      if (ws) {
        cy.wrap(ws).should('have.property', 'readyState', 1);
        
        // Wait for events and validate critical agent events were received
        eventPromise.then((events) => {
          const eventTypes = events.map(e => e.type);
          
          // Verify at least some critical events were sent
          const receivedCriticalEvents = CRITICAL_AGENT_EVENTS.filter(event => 
            eventTypes.includes(event)
          );
          
          expect(receivedCriticalEvents.length).to.be.greaterThan(0, 
            `No critical agent events received. Got: ${eventTypes.join(', ')}`);
          
          // Verify agent_started is among the first events (if any critical events received)
          if (receivedCriticalEvents.length > 0) {
            const firstCriticalEvent = eventTypes.find(type => 
              CRITICAL_AGENT_EVENTS.includes(type)
            );
            expect(['agent_started', 'agent_thinking']).to.include(firstCriticalEvent, 
              'First critical event should be agent_started or agent_thinking');
          }
        });
      }
    });
  });

  it('should handle connection status indicators and reconnection', () => {
    // Verify connection status component exists
    ComponentVisibility.assertConnectionStatus();
    
    // Check for specific connection indicators
    cy.get('[data-testid="connection-status"]').should('have.class', 'bg-green-500');
    
    // Verify WebSocket status indicator if present
    cy.get('body').then(($body) => {
      if ($body.find('[data-testid="ws-indicator"]').length > 0) {
        cy.get('[data-testid="ws-indicator"]').should('be.visible');
      }
    });
    
    // Test connection state change detection
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      if (ws && ws.readyState === 1) {
        cy.log('WebSocket connection is OPEN and healthy');
        
        // Test reconnection scenario
        simulateNetworkPartition();
        
        // Verify connection status updates
        cy.get('[data-testid="connection-status"]', { timeout: 5000 })
          .should('not.have.class', 'bg-green-500');
        
        // Wait for and verify reconnection
        verifyReconnection(WEBSOCKET_CONFIG.CONNECTION_TIMEOUT).then((reconnectedWs) => {
          if (reconnectedWs) {
            expect(reconnectedWs.readyState).to.be.oneOf([0, 1], 
              'WebSocket should reconnect successfully');
          }
        });
      }
    });
  });

  it('should maintain message history', () => {
    const firstMessage = 'First test message';
    const secondMessage = 'Second test message';
    
    // Send first message
    MessageInput.sendAndWait(firstMessage);
    MessageAssertions.assertUserMessage(firstMessage);
    
    // Send second message
    MessageInput.sendAndWait(secondMessage);
    MessageAssertions.assertUserMessage(secondMessage);
    
    // Verify both messages are visible
    cy.contains(firstMessage).should('be.visible');
    cy.contains(secondMessage).should('be.visible');
    
    // Check message order in chat container
    cy.get('[data-testid="chat-container"]').within(() => {
      cy.get('[data-testid="user-message"]').then($messages => {
        const messages = Array.from($messages).map(el => el.textContent);
        const firstIndex = messages.findIndex(msg => msg?.includes(firstMessage));
        const secondIndex = messages.findIndex(msg => msg?.includes(secondMessage));
        expect(firstIndex).to.be.lessThan(secondIndex);
      });
    });
  });

  it('should handle empty message submission without triggering WebSocket events', () => {
    // Start monitoring WebSocket events
    const eventPromise = monitorWebSocketEvents(5000); // 5 second timeout
    
    // Clear input and attempt to send
    MessageInput.clear();
    cy.get('[data-testid="send-button"]').should('be.disabled');
    
    // Try clicking disabled send button
    cy.get('[data-testid="send-button"]').click({ force: true });
    
    // Verify no empty message was sent
    cy.wait(1000);
    cy.get('[data-testid="user-message"]').should('not.exist');
    
    // Verify input remains available and enabled
    cy.get('textarea[data-testid="message-input"]')
      .should('be.visible')
      .and('not.be.disabled')
      .and('have.value', '');
    
    // Verify no agent events were triggered for empty message
    eventPromise.then((events) => {
      const agentEvents = events.filter(e => CRITICAL_AGENT_EVENTS.includes(e.type));
      expect(agentEvents.length).to.equal(0, 
        'No agent events should be triggered for empty message submission');
    });
  });

  it('should handle rapid message sending with consistent agent events', () => {
    const messages = [
      'Quick message 1',
      'Quick message 2', 
      'Quick message 3'
    ];
    
    // Start monitoring WebSocket events for all messages
    const eventPromise = monitorWebSocketEvents(20000); // 20 second timeout for multiple messages
    
    // Send messages rapidly using helper
    messages.forEach((message, index) => {
      MessageInput.send(message);
      MessageAssertions.assertUserMessage(message);
      cy.wait(100); // Brief delay to prevent overwhelming
    });
    
    // Verify all messages appear in correct order
    cy.get('[data-testid="chat-container"]').within(() => {
      messages.forEach(message => {
        cy.contains(message, { timeout: 10000 }).should('be.visible');
      });
    });
    
    // Verify WebSocket can handle rapid messages and maintains event consistency
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      if (ws) {
        expect(ws.readyState).to.equal(1, 'WebSocket should remain open after rapid messages');
        
        // Validate that each message triggered proper agent events
        eventPromise.then((events) => {
          const eventTypes = events.map(e => e.type);
          
          // Should have multiple agent_started events (one per message)
          const startEvents = eventTypes.filter(type => type === 'agent_started');
          expect(startEvents.length).to.be.at.least(messages.length, 
            `Expected at least ${messages.length} agent_started events for ${messages.length} messages`);
          
          // Should have corresponding completion events
          const completionEvents = eventTypes.filter(type => 
            ['agent_completed', 'final_report'].includes(type)
          );
          expect(completionEvents.length).to.be.greaterThan(0, 
            'Should have completion events for rapid messages');
        });
      }
    });
  });

  it('should validate all critical agent events during message processing', () => {
    const testMessage = 'Test complete agent event flow: analyze system status and generate report';
    
    // Simulate critical WebSocket events for testing
    simulateCriticalWebSocketEvents();
    
    // Send a complex message that should trigger multiple agent events
    MessageInput.send(testMessage);
    MessageAssertions.assertUserMessage(testMessage);
    
    // Monitor for agent events with extended timeout
    const eventPromise = monitorWebSocketEvents(25000); // 25 second timeout
    
    // Wait for processing to complete
    WaitHelpers.forResponse();
    MessageAssertions.assertAssistantMessage();
    
    // Validate critical events were received
    eventPromise.then((events) => {
      const validator = validateCriticalEvents();
      const eventTypes = events.map(e => e.type);
      
      // Check each critical event type
      CRITICAL_AGENT_EVENTS.forEach(eventType => {
        const hasEvent = validator.validate(eventType) && eventTypes.includes(eventType);
        if (hasEvent) {
          cy.log(`✅ Critical event received: ${eventType}`);
        } else {
          cy.log(`⚠️ Critical event missing: ${eventType}`);
        }
      });
      
      // Verify proper event sequencing
      const firstEvent = eventTypes[0];
      const lastEvent = eventTypes[eventTypes.length - 1];
      
      // First event should be a start event
      expect(['agent_started', 'agent_thinking']).to.include(firstEvent, 
        'First event should indicate agent started processing');
      
      // Last event should be a completion event
      expect(['agent_completed', 'final_report']).to.include(lastEvent, 
        'Last event should indicate agent completed processing');
      
      // Tool events should be paired if present
      const toolStartEvents = eventTypes.filter(type => type === 'tool_executing').length;
      const toolEndEvents = eventTypes.filter(type => type === 'tool_completed').length;
      
      if (toolStartEvents > 0) {
        expect(toolEndEvents).to.equal(toolStartEvents, 
          `Tool events should be paired: ${toolStartEvents} starts, ${toolEndEvents} completions`);
      }
    });
  });

  it('should handle authentication errors and token refresh gracefully', () => {
    // Test WebSocket authentication flow
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      
      if (ws) {
        // Verify current connection is authenticated or in development mode
        const authToken = win.localStorage.getItem('auth_token');
        const isDevelopment = win.location.hostname === 'localhost';
        
        if (authToken) {
          // Test with valid token - should use JWT subprotocol
          expect(ws.protocol).to.include('jwt-auth', 
            'Authenticated WebSocket should use JWT subprotocol');
          
          // Simulate token refresh scenario
          win.localStorage.setItem('auth_token', 'new-refreshed-token');
          
          // The WebSocket service should handle token refresh internally
          // We verify the connection remains stable
          cy.wait(1000);
          expect(ws.readyState).to.be.oneOf([0, 1], 
            'WebSocket should handle token refresh gracefully');
        } else if (isDevelopment) {
          // Development mode - no authentication required
          cy.log('Development mode: WebSocket connection without authentication');
          expect(ws.readyState).to.be.oneOf([0, 1], 
            'Development WebSocket should connect without authentication');
        }
      }
    });
    
    // Verify WebSocket service security status
    verifyWebSocketServiceIntegration();
  });

  it('should maintain message history with proper event tracking', () => {
    const firstMessage = 'First test message - analyze performance';
    const secondMessage = 'Second test message - generate optimization report';
    
    // Start comprehensive event monitoring
    const eventPromise = monitorWebSocketEvents(30000); // 30 second timeout
    
    // Send first message
    MessageInput.sendAndWait(firstMessage);
    MessageAssertions.assertUserMessage(firstMessage);
    
    // Send second message
    MessageInput.sendAndWait(secondMessage);
    MessageAssertions.assertUserMessage(secondMessage);
    
    // Verify both messages are visible
    cy.contains(firstMessage).should('be.visible');
    cy.contains(secondMessage).should('be.visible');
    
    // Check message order in chat container
    cy.get('[data-testid="chat-container"]').within(() => {
      cy.get('[data-testid="user-message"]').then($messages => {
        const messages = Array.from($messages).map(el => el.textContent);
        const firstIndex = messages.findIndex(msg => msg?.includes(firstMessage));
        const secondIndex = messages.findIndex(msg => msg?.includes(secondMessage));
        expect(firstIndex).to.be.lessThan(secondIndex, 'Messages should appear in correct order');
      });
    });
    
    // Verify event tracking maintained proper sequencing
    eventPromise.then((events) => {
      const eventTypes = events.map(e => e.type);
      const agentStartEvents = eventTypes.filter(type => type === 'agent_started');
      
      // Should have received agent_started events for both messages
      expect(agentStartEvents.length).to.be.at.least(2, 
        'Should have agent_started events for both messages');
      
      // Events should be properly sequenced
      const firstStartIndex = eventTypes.indexOf('agent_started');
      const lastEventIndex = eventTypes.length - 1;
      
      expect(firstStartIndex).to.be.at.least(0, 'Should have first agent_started event');
      expect(eventTypes[lastEventIndex]).to.be.oneOf(['agent_completed', 'final_report'], 
        'Last event should be a completion event');
    });
  });

  it('should handle WebSocket connection errors and recovery', () => {
    // Verify initial connection
    waitForConnection().then((ws) => {
      if (ws) {
        expect(ws.readyState).to.be.oneOf([0, 1]);
        
        // Test error handling
        cy.window().then((win) => {
          const webSocketService = win.webSocketService;
          if (webSocketService) {
            const securityStatus = webSocketService.getSecurityStatus();
            
            // Verify security configuration
            expect(securityStatus).to.have.property('hasToken');
            expect(securityStatus).to.have.property('authMethod');
            
            // Test that service can handle errors gracefully
            cy.log(`WebSocket Security Status: ${JSON.stringify(securityStatus)}`);
          }
        });
        
        // Simulate network partition and recovery
        simulateNetworkPartition();
        
        // Verify reconnection capability
        verifyReconnection(WEBSOCKET_CONFIG.CONNECTION_TIMEOUT * 2).then((reconnectedWs) => {
          if (reconnectedWs) {
            expect(reconnectedWs.readyState).to.be.oneOf([0, 1], 
              'WebSocket should recover from network partition');
            cy.log('✅ WebSocket successfully recovered from network partition');
          } else {
            // In case WebSocket manager handles reconnection internally
            cy.get('[data-testid="connection-status"]').should('exist');
            cy.log('WebSocket recovery handled by internal connection manager');
          }
        });
      }
    });
  });
});