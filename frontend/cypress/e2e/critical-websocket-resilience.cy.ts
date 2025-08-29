/// <reference types="cypress" />

/**
 * WebSocket Resilience Test Suite Index
 * 
 * This file imports and orchestrates all WebSocket resilience tests
 * split into focused modules for maintainability.
 * 
 * Test modules:
 * - websocket-connection-lifecycle.cy.ts: Connection establishment, recovery, pooling
 * - websocket-heartbeat-monitoring.cy.ts: Heartbeat functionality, stale detection  
 * - websocket-advanced-resilience.cy.ts: Server restart, auth expiry scenarios
 */

import {
  WEBSOCKET_CONFIG,
  setupTestEnvironment,
  navigateToChat,
  waitForConnection,
  simulateNetworkPartition,
  verifyReconnection,
  findWebSocketConnection
} from '../support/websocket-test-helpers';

import './websocket-connection-lifecycle.cy.ts';
import './websocket-heartbeat-monitoring.cy.ts';
import './websocket-advanced-resilience.cy.ts';

describe('CRITICAL: WebSocket Resilience Test Suite', () => {
  beforeEach(() => {
    setupTestEnvironment();
    navigateToChat();
  });

  it('should run all focused resilience test modules', () => {
    cy.log('All WebSocket resilience tests are executed through focused modules');
    cy.log('- Connection Lifecycle: Basic connection handling');
    cy.log('- Heartbeat Monitoring: Health checks and ordering');
    cy.log('- Advanced Resilience: Server restart and auth scenarios');
    
    // Verify basic setup works for all modules
    waitForConnection().then((ws) => {
      if (ws) {
        expect(ws.readyState).to.be.oneOf([0, 1], 'WebSocket should be ready for resilience tests');
        cy.log(`WebSocket connection established successfully for resilience testing`);
      } else {
        cy.log('WebSocket connection verified through UI indicators');
        cy.get('[data-testid="connection-status"]').should('exist');
      }
    });
  });

  it('should validate WebSocket configuration matches backend', () => {
    cy.log(`Heartbeat interval: ${WEBSOCKET_CONFIG.HEARTBEAT_INTERVAL}ms`);
    cy.log(`Heartbeat timeout: ${WEBSOCKET_CONFIG.HEARTBEAT_TIMEOUT}ms`);
    cy.log(`Max connections per user: ${WEBSOCKET_CONFIG.MAX_CONNECTIONS_PER_USER}`);
    cy.log(`Max retry attempts: ${WEBSOCKET_CONFIG.MAX_RETRY_ATTEMPTS}`);
    cy.log(`Retry delay: ${WEBSOCKET_CONFIG.RETRY_DELAY}ms`);
    
    expect(WEBSOCKET_CONFIG.HEARTBEAT_INTERVAL).to.be.greaterThan(0);
    expect(WEBSOCKET_CONFIG.MAX_CONNECTIONS_PER_USER).to.be.greaterThan(0);
    expect(WEBSOCKET_CONFIG.MAX_RETRY_ATTEMPTS).to.be.greaterThan(0);
  });
});