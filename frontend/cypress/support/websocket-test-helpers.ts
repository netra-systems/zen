/// <reference types="cypress" />

/**
 * WebSocket Test Helpers and Shared Utilities
 * 
 * Provides common setup, configuration, and helper functions
 * for WebSocket resilience testing across all test modules.
 */

// Configuration constants from ws_manager.py
export const WEBSOCKET_CONFIG = {
  HEARTBEAT_INTERVAL: 30000, // 30 seconds
  HEARTBEAT_TIMEOUT: 60000, // 60 seconds
  MAX_CONNECTIONS_PER_USER: 5,
  MAX_RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // 1 second
};

// Global test state
export interface WebSocketTestState {
  wsConnection: WebSocket | null;
  messageQueue: string[];
  connectionAttempts: number;
  lastHeartbeat: number;
}

export const createInitialState = (): WebSocketTestState => ({
  wsConnection: null,
  messageQueue: [],
  connectionAttempts: 0,
  lastHeartbeat: Date.now(),
});

export const setupTestEnvironment = () => {
  cy.viewport(1920, 1080);
  
  // Set up auth for chat access
  cy.window().then((win) => {
    win.localStorage.setItem('auth_token', 'test-token');
    win.localStorage.setItem('user', JSON.stringify({
      id: 'test-user',
      email: 'test@netrasystems.ai',
      name: 'Test User'
    }));
  });
};

export const interceptWebSocketConnections = () => {
  let connectionAttempts = 0;
  
  cy.intercept('/ws*', (req) => {
    connectionAttempts++;
    req.continue();
  }).as('wsConnect');
  
  return () => connectionAttempts;
};

export const navigateToChat = () => {
  cy.visit('/demo');
  cy.contains('Technology').click();
  cy.contains('AI Chat').click({ force: true });
  cy.wait(1000);
};

export const findWebSocketConnection = (win: any): WebSocket | null => {
  const possibleWS = [
    win.ws,
    win.websocket,
    win.socket,
    win.__netraWebSocket,
    win.WebSocketManager?.activeConnection
  ].find(ws => ws !== undefined);
  
  return possibleWS || null;
};

export const verifyConnectionState = (ws: WebSocket, maxRetries: number) => {
  expect(ws.readyState).to.be.oneOf([0, 1], 'WebSocket should be CONNECTING or OPEN');
  expect(ws).to.have.property('url');
};

export const waitForConnection = (maxAttempts: number = 10): Cypress.Chainable => {
  return cy.window().then((win) => {
    return cy.wrap(null).then(() => {
      return new Cypress.Promise((resolve, reject) => {
        let attempts = 0;
        
        const checkConnection = () => {
          attempts++;
          const ws = findWebSocketConnection(win);
          
          if (ws && ws.readyState !== undefined) {
            verifyConnectionState(ws, WEBSOCKET_CONFIG.MAX_RETRY_ATTEMPTS);
            resolve(ws);
          } else if (attempts < maxAttempts) {
            setTimeout(checkConnection, 500);
          } else {
            // Fallback: check for UI indicators
            cy.get('[data-testid="connection-status"], [class*="connected"], [class*="online"]')
              .should('exist')
              .then(() => resolve(null));
          }
        };
        
        checkConnection();
      });
    });
  });
};

export const simulateNetworkPartition = () => {
  cy.window().then((win) => {
    const ws = findWebSocketConnection(win);
    if (ws) {
      // Simulate network disconnection
      ws.close(1006, 'Network partition simulated');
    }
  });
};

export const verifyReconnection = (timeoutMs: number = 5000) => {
  cy.wait(timeoutMs, { timeout: timeoutMs + 1000 });
  return waitForConnection();
};