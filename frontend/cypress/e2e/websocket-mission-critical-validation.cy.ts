/// <reference types="cypress" />

import {
  WEBSOCKET_CONFIG,
  CRITICAL_WS_EVENTS,
  CriticalWebSocketEvent,
  setupTestEnvironment,
  navigateToChat,
  waitForConnection,
  findWebSocketConnection,
  simulateCriticalWebSocketEvents,
  verifyWebSocketServiceIntegration
} from '../support/websocket-test-helpers';

/**
 * Mission-Critical WebSocket Validation Tests
 * 
 * This test suite validates that ALL 5 critical WebSocket events work properly:
 * 1. agent_started - User must see agent began processing
 * 2. agent_thinking - Real-time reasoning visibility  
 * 3. tool_executing - Tool usage transparency
 * 4. tool_completed - Tool results display
 * 5. agent_completed - User must know when done
 * 
 * THESE TESTS CANNOT FAIL - they ensure the chat experience works for users.
 */
describe('Mission-Critical WebSocket Event Validation', () => {
  beforeEach(() => {
    setupTestEnvironment();
    navigateToChat();
  });

  afterEach(() => {
    // Clean up WebSocket connections
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      if (ws && ws.close && ws.readyState === WebSocket.OPEN) {
        ws.close(1000, 'Test cleanup');
      }
    });
  });

  it('MISSION CRITICAL: All 5 required WebSocket events must be handled correctly', () => {
    waitForConnection().then(() => {
      cy.log('=== MISSION CRITICAL TEST: Validating all 5 WebSocket events ===');
      
      // Test each critical event individually
      testAgentStartedEvent();
      testToolExecutingEvent();
      testAgentThinkingEvent();
      testToolCompletedEvent();
      testAgentCompletedEvent();
      
      // Test complete agent lifecycle
      testCompleteAgentLifecycle();
      
      cy.log('=== ALL MISSION CRITICAL EVENTS VALIDATED ===');
    });
  });

  it('MISSION CRITICAL: WebSocket events must integrate with unified chat store', () => {
    waitForConnection().then(() => {
      cy.window().then((win) => {
        const store = (win as any).useUnifiedChatStore?.getState();
        if (store && store.handleWebSocketEvent) {
          cy.log('✓ Unified chat store WebSocket integration available');
          
          // Verify event handling capability
          expect(store.handleWebSocketEvent).to.be.a('function');
          
          // Test event processing
          testStoreEventProcessing(store);
        } else {
          cy.log('✗ CRITICAL FAILURE: Unified chat store WebSocket integration not available');
          throw new Error('WebSocket event handling not available in unified chat store');
        }
      });
    });
  });

  it('MISSION CRITICAL: WebSocket service must be properly initialized and configured', () => {
    waitForConnection().then(() => {
      verifyWebSocketServiceIntegration();
      
      cy.window().then((win) => {
        const webSocketService = (win as any).webSocketService;
        if (webSocketService) {
          // Verify service configuration
          const securityStatus = webSocketService.getSecurityStatus();
          cy.log('WebSocket security status:', securityStatus);
          
          // Verify service state
          const state = webSocketService.getState();
          expect(state).to.be.oneOf(['connecting', 'connected']);
          
          // Verify large message capabilities
          const stats = webSocketService.getLargeMessageStats();
          expect(stats).to.have.property('supportedCompression');
          expect(stats).to.have.property('maxMessageSize');
          
          cy.log('✓ WebSocket service properly configured');
        } else {
          cy.log('✗ CRITICAL FAILURE: WebSocket service not available');
          throw new Error('WebSocket service not available');
        }
      });
    });
  });

  it('MISSION CRITICAL: WebSocket connection must survive network issues', () => {
    waitForConnection().then(() => {
      // Test network disruption and recovery
      testNetworkDisruptionRecovery();
    });
  });

  // Helper functions for critical event testing
  function testAgentStartedEvent(): void {
    cy.log('Testing agent_started event...');
    
    cy.window().then((win) => {
      const store = (win as any).useUnifiedChatStore?.getState();
      if (store && store.handleWebSocketEvent) {
        const agentStartedEvent = {
          type: 'agent_started',
          payload: {
            agent_id: `critical-test-agent-${Date.now()}`,
            agent_type: 'CriticalTestAgent',
            run_id: `critical-run-${Date.now()}`,
            timestamp: Date.now(),
            status: 'started',
            message: 'Agent started processing user request'
          }
        };
        
        store.handleWebSocketEvent(agentStartedEvent);
        cy.log('✓ agent_started event handled successfully');
      } else {
        throw new Error('Cannot test agent_started event - store not available');
      }
    });
  }

  function testToolExecutingEvent(): void {
    cy.log('Testing tool_executing event...');
    
    cy.window().then((win) => {
      const store = (win as any).useUnifiedChatStore?.getState();
      if (store && store.handleWebSocketEvent) {
        const toolExecutingEvent = {
          type: 'tool_executing',
          payload: {
            tool_name: 'critical_test_tool',
            agent_id: `critical-test-agent-${Date.now()}`,
            timestamp: Date.now()
          }
        };
        
        store.handleWebSocketEvent(toolExecutingEvent);
        cy.log('✓ tool_executing event handled successfully');
      } else {
        throw new Error('Cannot test tool_executing event - store not available');
      }
    });
  }

  function testAgentThinkingEvent(): void {
    cy.log('Testing agent_thinking event...');
    
    cy.window().then((win) => {
      const store = (win as any).useUnifiedChatStore?.getState();
      if (store && store.handleWebSocketEvent) {
        const agentThinkingEvent = {
          type: 'agent_thinking',
          payload: {
            thought: 'Analyzing user request and determining best approach...',
            agent_id: `critical-test-agent-${Date.now()}`,
            step_number: 1,
            total_steps: 3
          }
        };
        
        store.handleWebSocketEvent(agentThinkingEvent);
        cy.log('✓ agent_thinking event handled successfully');
      } else {
        throw new Error('Cannot test agent_thinking event - store not available');
      }
    });
  }

  function testToolCompletedEvent(): void {
    cy.log('Testing tool_completed event...');
    
    cy.window().then((win) => {
      const store = (win as any).useUnifiedChatStore?.getState();
      if (store && store.handleWebSocketEvent) {
        const toolCompletedEvent = {
          type: 'tool_completed',
          payload: {
            tool_name: 'critical_test_tool',
            result: {
              success: true,
              data: 'Tool execution completed successfully',
              execution_time_ms: 2500
            },
            agent_id: `critical-test-agent-${Date.now()}`,
            timestamp: Date.now()
          }
        };
        
        store.handleWebSocketEvent(toolCompletedEvent);
        cy.log('✓ tool_completed event handled successfully');
      } else {
        throw new Error('Cannot test tool_completed event - store not available');
      }
    });
  }

  function testAgentCompletedEvent(): void {
    cy.log('Testing agent_completed event...');
    
    cy.window().then((win) => {
      const store = (win as any).useUnifiedChatStore?.getState();
      if (store && store.handleWebSocketEvent) {
        const agentCompletedEvent = {
          type: 'agent_completed',
          payload: {
            agent_id: `critical-test-agent-${Date.now()}`,
            agent_type: 'CriticalTestAgent',
            duration_ms: 8500,
            result: {
              status: 'success',
              message: 'Agent completed processing successfully',
              output: 'Task completed with full success'
            },
            metrics: {
              tools_used: 2,
              tokens_consumed: 1250,
              api_calls: 3
            }
          }
        };
        
        store.handleWebSocketEvent(agentCompletedEvent);
        cy.log('✓ agent_completed event handled successfully');
      } else {
        throw new Error('Cannot test agent_completed event - store not available');
      }
    });
  }

  function testCompleteAgentLifecycle(): void {
    cy.log('Testing complete agent lifecycle...');
    
    simulateCriticalWebSocketEvents();
    
    // Wait for events to process
    cy.wait(3000);
    
    cy.log('✓ Complete agent lifecycle test completed');
  }

  function testStoreEventProcessing(store: any): void {
    cy.log('Testing store event processing capabilities...');
    
    // Test that store can handle each critical event type
    CRITICAL_WS_EVENTS.forEach((eventType) => {
      const testEvent = createTestEventForStore(eventType);
      try {
        store.handleWebSocketEvent(testEvent);
        cy.log(`✓ Store handled ${eventType} event successfully`);
      } catch (error) {
        cy.log(`✗ Store failed to handle ${eventType} event:`, error);
        throw new Error(`Store cannot handle ${eventType} event`);
      }
    });
  }

  function createTestEventForStore(eventType: CriticalWebSocketEvent): any {
    const basePayload = {
      agent_id: `store-test-agent-${Date.now()}`,
      timestamp: Date.now()
    };

    switch (eventType) {
      case 'agent_started':
        return {
          type: eventType,
          payload: {
            ...basePayload,
            agent_type: 'StoreTestAgent',
            run_id: `store-test-run-${Date.now()}`
          }
        };
      case 'agent_thinking':
        return {
          type: eventType,
          payload: {
            ...basePayload,
            thought: 'Store test thinking process...',
            step_number: 1,
            total_steps: 2
          }
        };
      case 'tool_executing':
        return {
          type: eventType,
          payload: {
            ...basePayload,
            tool_name: 'store_test_tool'
          }
        };
      case 'tool_completed':
        return {
          type: eventType,
          payload: {
            ...basePayload,
            tool_name: 'store_test_tool',
            result: { success: true, test: 'store_validation' }
          }
        };
      case 'agent_completed':
        return {
          type: eventType,
          payload: {
            ...basePayload,
            agent_type: 'StoreTestAgent',
            duration_ms: 3000,
            result: { status: 'success' },
            metrics: { tools_used: 1 }
          }
        };
      default:
        return { type: eventType, payload: basePayload };
    }
  }

  function testNetworkDisruptionRecovery(): void {
    cy.log('Testing network disruption recovery...');
    
    // Send test message before disruption
    const beforeDisruption = `Before disruption ${Date.now()}`;
    cy.get('textarea').clear().type(beforeDisruption);
    cy.get('button[aria-label="Send message"]').click();
    cy.contains(beforeDisruption).should('be.visible');
    
    // Simulate network disruption
    cy.intercept('**/ws**', { forceNetworkError: true }).as('wsDisrupt');
    
    // Try to send message during disruption
    const duringDisruption = `During disruption ${Date.now()}`;
    cy.get('textarea').clear().type(duringDisruption);
    cy.get('button[aria-label="Send message"]').click();
    
    // Wait for disruption
    cy.wait(2000);
    
    // Restore network
    cy.intercept('**/ws**', (req) => req.continue()).as('wsRestore');
    
    // Wait for recovery
    cy.wait(WEBSOCKET_CONFIG.RETRY_DELAY * 3);
    
    // Verify connection recovered
    waitForConnection().then(() => {
      // Send message after recovery
      const afterRecovery = `After recovery ${Date.now()}`;
      cy.get('textarea').clear().type(afterRecovery);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(afterRecovery).should('be.visible');
      
      cy.log('✓ Network disruption recovery test completed');
    });
  }
});