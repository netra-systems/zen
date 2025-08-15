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

import './websocket-connection-lifecycle.cy.ts';
import './websocket-heartbeat-monitoring.cy.ts';
import './websocket-advanced-resilience.cy.ts';

describe('CRITICAL: WebSocket Resilience Test Suite', () => {
  it('should run all focused resilience test modules', () => {
    cy.log('All WebSocket resilience tests are executed through focused modules');
    cy.log('- Connection Lifecycle: Basic connection handling');
    cy.log('- Heartbeat Monitoring: Health checks and ordering');
    cy.log('- Advanced Resilience: Server restart and auth scenarios');
  });
});