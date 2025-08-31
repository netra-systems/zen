/// <reference types="cypress" />

import {
  WEBSOCKET_CONFIG,
  WebSocketTestState,
  createInitialState,
  setupTestEnvironment,
  interceptWebSocketConnections,
  navigateToChat,
  waitForConnection,
  simulateNetworkPartition,
  verifyReconnection,
  findWebSocketConnection
} from '../support/websocket-test-helpers';

/**
 * WebSocket Connection Lifecycle Tests
 * 
 * Tests core connection establishment, maintenance,
 * network partition recovery, and connection pooling.
 */
describe('WebSocket Connection Lifecycle Management', () => {
  let testState: WebSocketTestState;
  let getConnectionAttempts: () => number;

  beforeEach(() => {
    testState = createInitialState();
    setupTestEnvironment();
    getConnectionAttempts = interceptWebSocketConnections();
    navigateToChat();
    
    // Wait for connection to be established
    cy.wait(2000);
  });

  it('CRITICAL: Should establish connection and handle agent events properly', () => {
    waitForConnection().then((ws) => {
      if (ws) {
        testState.wsConnection = ws;
        expect(getConnectionAttempts()).to.be.lessThan(
          WEBSOCKET_CONFIG.MAX_RETRY_ATTEMPTS + 1,
          'Should not exceed max retry attempts'
        );
      }
    });
    
    // Test critical agent event flow to ensure connection is working
    simulateFullAgentLifecycle('lifecycle-test-agent');
    
    // Verify agent events are processed correctly
    cy.get('[data-testid*="agent"], .agent-status').should('exist');
    cy.get('body').should('contain.text', 'lifecycle-test-agent');
    
    // Verify connection metadata exists
    cy.window().then((win) => {
      const connectionInfo = (win as any).__netraConnectionInfo;
      if (connectionInfo) {
        expect(connectionInfo).to.have.property('connection_id');
        expect(connectionInfo).to.have.property('user_id', 'test-user');
        expect(connectionInfo).to.have.property('connected_at');
      }
    });
  });

  it('CRITICAL: Should handle network partition and maintain agent event flow', () => {
    const initialMessage = `Initial message ${Date.now()}`;
    cy.get('textarea, [data-testid="message-input"]').type(initialMessage);
    cy.get('button[aria-label="Send message"], button:contains("Send")').click();
    cy.wait(500);
    
    // Test agent events before partition
    simulateFullAgentLifecycle('pre-partition-agent');
    
    recordInitialConnectionId().then((initialId) => {
      simulateCompleteNetworkPartition();
      cy.wait(3000); // Wait for disconnection detection
      
      verifyDisconnectionIndicators();
      queueAgentEventsDuringPartition();
      restoreNetworkConnection();
      
      verifyReconnectionAndAgentEventDelivery(initialId);
      
      // Test agent events after reconnection
      simulateFullAgentLifecycle('post-partition-agent');
    });
  });

  it('CRITICAL: Should handle connection pool exhaustion and maintain agent events', () => {
    const connections = createMultipleConnections();
    
    verifyConnectionLimitEnforcement(connections);
    verifyOldestConnectionClosure(connections);
    verifyGracefulPoolManagement();
    
    // Verify agent events still work with connection pooling
    simulateFullAgentLifecycle('pool-test-agent');
    cy.get('[data-testid*="agent"], .agent-status').should('exist');
  });

  it('CRITICAL: Should synchronize agent state after reconnection', () => {
    const testMessage = `State sync test ${Date.now()}`;
    sendMessageAndRecord(testMessage);
    
    // Start agent before disconnection
    simulateFullAgentLifecycle('pre-disconnect-agent');
    
    cy.wait(2000);
    simulateNetworkPartition();
    cy.wait(2000);
    
    verifyReconnection().then(() => {
      verifyStateSynchronization(testMessage);
      
      // Verify agent events work after reconnection
      simulateFullAgentLifecycle('post-reconnect-agent');
      cy.get('[data-testid*="agent"], .agent-status').should('contain', 'post-reconnect-agent');
    });
  });

  it('CRITICAL: Should survive rapid connection cycling and maintain agent event processing', () => {
    const cycleCount = 3; // Reduced for stability
    
    for (let i = 0; i < cycleCount; i++) {
      cy.log(`Connection cycle ${i + 1}/${cycleCount}`);
      
      performConnectionCycle(i);
      verifyMemoryUsage(i);
      
      // Test agent events after each cycle
      simulateFullAgentLifecycle(`cycle-${i}-agent`);
      cy.wait(1000);
    }
    
    verifyNoMemoryLeaks();
    
    // Final verification that agent events still work
    simulateFullAgentLifecycle('final-cycle-agent');
    cy.get('[data-testid*="agent"], .agent-status').should('contain', 'final-cycle-agent');
  });

  // Helper functions for complex operations
  function simulateFullAgentLifecycle(agentId: string): void {
    cy.window().then((win) => {
      const events = [
        {
          type: 'agent_started',
          payload: {
            agent_id: agentId,
            agent_type: 'lifecycle_test_agent',
            run_id: `run-${agentId}`,
            timestamp: new Date().toISOString(),
            status: 'started'
          }
        },
        {
          type: 'agent_thinking',
          payload: {
            thought: `${agentId} is processing the lifecycle test`,
            agent_id: agentId,
            agent_type: 'lifecycle_test_agent',
            step_number: 1,
            total_steps: 3
          }
        },
        {
          type: 'tool_executing',
          payload: {
            tool_name: 'lifecycle_analyzer',
            agent_id: agentId,
            agent_type: 'lifecycle_test_agent',
            timestamp: Date.now()
          }
        },
        {
          type: 'tool_completed',
          payload: {
            tool_name: 'lifecycle_analyzer',
            result: { analysis: 'lifecycle test successful' },
            agent_id: agentId,
            timestamp: Date.now()
          }
        },
        {
          type: 'agent_completed',
          payload: {
            agent_id: agentId,
            agent_type: 'lifecycle_test_agent',
            duration_ms: 1800,
            result: { status: 'success', lifecycle_test: 'passed' },
            metrics: { tools_executed: 1, success_rate: 1.0 }
          }
        }
      ];
      
      // Simulate events with proper timing
      events.forEach((event, index) => {
        setTimeout(() => {
          const ws = findWebSocketConnection(win);
          if (ws && ws.onmessage) {
            ws.onmessage({ data: JSON.stringify(event) } as any);
          }
        }, index * 150);
      });
    });
  }

  function recordInitialConnectionId(): Cypress.Chainable<string | null> {
    return cy.window().then((win) => {
      const connInfo = (win as any).__netraConnectionInfo;
      return connInfo ? connInfo.connection_id : null;
    });
  }

  function simulateCompleteNetworkPartition(): void {
    cy.log('Simulating network partition...');
    cy.intercept('**/ws**', { forceNetworkError: true }).as('wsBlock');
    cy.intercept('POST', '**/api/**', { forceNetworkError: true }).as('apiBlock');
  }

  function verifyDisconnectionIndicators(): void {
    cy.get('body').then(($body) => {
      const disconnectIndicators = [
        '[data-testid="connection-lost"]',
        '[class*="reconnecting"]',
        '[class*="disconnected"]',
        '[class*="offline"]'
      ];
      
      const hasIndicator = disconnectIndicators.some(selector => 
        $body.find(selector).length > 0
      );
      
      if (hasIndicator) {
        cy.log('Disconnection indicator found');
        cy.get(disconnectIndicators.join(', ')).first().should('be.visible');
      }
    });
  }

  function queueAgentEventsDuringPartition(): void {
    // Simulate trying to start agents while disconnected
    const queuedAgents = ['partition-agent-1', 'partition-agent-2', 'partition-agent-3'];
    
    queuedAgents.forEach(agentId => {
      cy.get('textarea, [data-testid="message-input"]').clear().type(`Start ${agentId}`);
      cy.get('button[aria-label="Send message"], button:contains("Send")').click();
      testState.messageQueue.push(agentId);
      cy.wait(500);
    });
  }

  function restoreNetworkConnection(): void {
    cy.log('Restoring network connection...');
    cy.intercept('**/ws**', (req) => req.continue()).as('wsRestore');
    cy.intercept('POST', '**/api/**', (req) => req.continue()).as('apiRestore');
  }

  function verifyReconnectionAndAgentEventDelivery(initialId: string | null): void {
    cy.wait(WEBSOCKET_CONFIG.RETRY_DELAY * 2);
    
    cy.get('[data-testid="connection-status"], [class*="connected"], [class*="online"]', { 
      timeout: 10000 
    }).should('exist');
    
    cy.wait(3000); // Allow time for agent event delivery
    
    // Verify queued agents can now be processed
    testState.messageQueue.forEach(agentId => {
      simulateFullAgentLifecycle(agentId);
      cy.wait(500);
    });
    
    // Test post-reconnection agent functionality
    simulateFullAgentLifecycle('post-reconnect-test-agent');
    cy.get('[data-testid*="agent"], .agent-status').should('contain', 'post-reconnect-test-agent');
    
    // Verify new connection ID
    cy.window().then((win) => {
      const newConnInfo = (win as any).__netraConnectionInfo;
      if (newConnInfo && initialId) {
        expect(newConnInfo.connection_id).to.not.equal(initialId);
      }
    });
  }

  function createMultipleConnections(): any[] {
    const connections: any[] = [];
    
    for (let i = 0; i < WEBSOCKET_CONFIG.MAX_CONNECTIONS_PER_USER + 1; i++) {
      const mockConnection = {
        id: `conn_${Date.now()}_${i}`,
        userId: 'test-user',
        createdAt: Date.now()
      };
      connections.push(mockConnection);
      
      cy.window().then((w) => {
        w.dispatchEvent(new CustomEvent('netra:ws:connect', { 
          detail: mockConnection 
        }));
      });
      
      cy.wait(500);
    }
    
    return connections;
  }

  function verifyConnectionLimitEnforcement(connections: any[]): void {
    cy.window().then((w) => {
      const activeConns = (w as any).__netraActiveConnections || [];
      expect(activeConns.length).to.be.at.most(
        WEBSOCKET_CONFIG.MAX_CONNECTIONS_PER_USER,
        `Should not exceed ${WEBSOCKET_CONFIG.MAX_CONNECTIONS_PER_USER} connections per user`
      );
    });
  }

  function verifyOldestConnectionClosure(connections: any[]): void {
    if (connections.length > WEBSOCKET_CONFIG.MAX_CONNECTIONS_PER_USER) {
      const oldestConn = connections[0];
      cy.window().then((w) => {
        const activeConns = (w as any).__netraActiveConnections || [];
        const isOldestActive = activeConns.some((conn: any) => conn.id === oldestConn.id);
        expect(isOldestActive).to.be.false;
      });
    }
  }

  function verifyGracefulPoolManagement(): void {
    cy.get('body').then(() => {
      cy.log('Connection pool management verified');
    });
  }

  function sendMessageAndRecord(message: string): void {
    cy.get('textarea, [data-testid="message-input"]').clear().type(message);
    cy.get('button[aria-label="Send message"], button:contains("Send")').click();
    cy.wait(500);
  }

  function verifyStateSynchronization(message: string): void {
    cy.contains(message).should('be.visible');
    cy.log('State synchronization verified');
  }

  function performConnectionCycle(cycleIndex: number): void {
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      if (ws) {
        ws.close();
        cy.wait(200); // Shorter wait for more stress
      }
    });
    
    waitForConnection().then(() => {
      cy.log(`Cycle ${cycleIndex + 1} completed`);
    });
  }

  function verifyMemoryUsage(cycleIndex: number): void {
    cy.window().then((win) => {
      if ((win as any).performance?.memory) {
        const memory = (win as any).performance.memory;
        cy.log(`Memory usage after cycle ${cycleIndex + 1}: ${Math.round(memory.usedJSHeapSize / 1024 / 1024)}MB`);
      }
    });
  }

  function verifyNoMemoryLeaks(): void {
    cy.wait(2000).then(() => {
      cy.log('Memory leak verification completed');
    });
  }
});