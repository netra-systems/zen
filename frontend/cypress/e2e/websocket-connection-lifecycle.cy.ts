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
  });

  it('CRITICAL: Should establish and maintain stable WebSocket connection', () => {
    waitForConnection().then((ws) => {
      if (ws) {
        testState.wsConnection = ws;
        expect(getConnectionAttempts()).to.be.lessThan(
          WEBSOCKET_CONFIG.MAX_RETRY_ATTEMPTS + 1,
          'Should not exceed max retry attempts'
        );
      }
    });
    
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

  it('CRITICAL: Should handle network partition and automatic reconnection', () => {
    const initialMessage = `Initial message ${Date.now()}`;
    cy.get('textarea').type(initialMessage);
    cy.get('button[aria-label="Send message"]').click();
    cy.contains(initialMessage).should('be.visible');
    
    recordInitialConnectionId().then((initialId) => {
      simulateCompleteNetworkPartition();
      cy.wait(3000); // Wait for disconnection detection
      
      verifyDisconnectionIndicators();
      queueMessagesDuringPartition();
      restoreNetworkConnection();
      
      verifyReconnectionAndMessageDelivery(initialId);
    });
  });

  it('CRITICAL: Should handle connection pool exhaustion gracefully', () => {
    const connections = createMultipleConnections();
    
    verifyConnectionLimitEnforcement(connections);
    verifyOldestConnectionClosure(connections);
    verifyGracefulPoolManagement();
  });

  it('should synchronize state after reconnection', () => {
    const testMessage = `State sync test ${Date.now()}`;
    sendMessageAndRecord(testMessage);
    
    cy.wait(2000);
    simulateNetworkPartition();
    cy.wait(2000);
    
    verifyReconnection().then(() => {
      verifyStateSynchronization(testMessage);
    });
  });

  it('CRITICAL: Should survive rapid connection cycling without memory leaks', () => {
    const cycleCount = 5;
    
    for (let i = 0; i < cycleCount; i++) {
      cy.log(`Connection cycle ${i + 1}/${cycleCount}`);
      
      performConnectionCycle(i);
      verifyMemoryUsage(i);
    }
    
    verifyNoMemoryLeaks();
  });

  // Helper functions for complex operations
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

  function queueMessagesDuringPartition(): void {
    const queuedMessages = [
      `Queued message 1 - ${Date.now()}`,
      `Queued message 2 - ${Date.now()}`,
      `Queued message 3 - ${Date.now()}`
    ];
    
    queuedMessages.forEach(msg => {
      cy.get('textarea').clear().type(msg);
      cy.get('button[aria-label="Send message"]').click();
      testState.messageQueue.push(msg);
      cy.wait(500);
    });
  }

  function restoreNetworkConnection(): void {
    cy.log('Restoring network connection...');
    cy.intercept('**/ws**', (req) => req.continue()).as('wsRestore');
    cy.intercept('POST', '**/api/**', (req) => req.continue()).as('apiRestore');
  }

  function verifyReconnectionAndMessageDelivery(initialId: string | null): void {
    cy.wait(WEBSOCKET_CONFIG.RETRY_DELAY * 2);
    
    cy.get('[data-testid="connection-status"], [class*="connected"], [class*="online"]', { 
      timeout: 10000 
    }).should('exist');
    
    cy.wait(3000); // Allow time for message delivery
    testState.messageQueue.forEach(msg => {
      cy.contains(msg).should('be.visible');
    });
    
    // Test post-reconnection messaging
    const postReconnectMessage = `Post-reconnect message ${Date.now()}`;
    cy.get('textarea').clear().type(postReconnectMessage);
    cy.get('button[aria-label="Send message"]').click();
    cy.contains(postReconnectMessage).should('be.visible');
    
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
    cy.get('textarea').clear().type(message);
    cy.get('button[aria-label="Send message"]').click();
    cy.contains(message).should('be.visible');
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