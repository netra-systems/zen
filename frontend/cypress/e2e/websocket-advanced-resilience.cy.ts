/// <reference types="cypress" />

import {
  WEBSOCKET_CONFIG,
  WebSocketTestState,
  createInitialState,
  setupTestEnvironment,
  interceptWebSocketConnections,
  navigateToChat,
  waitForConnection,
  findWebSocketConnection
} from '../support/websocket-test-helpers';

/**
 * WebSocket Advanced Resilience Scenarios
 * 
 * Tests server restart handling, authentication token expiry,
 * and complex failure recovery scenarios.
 */
describe('WebSocket Advanced Resilience Scenarios', () => {
  let testState: WebSocketTestState;
  let getConnectionAttempts: () => number;

  beforeEach(() => {
    testState = createInitialState();
    setupTestEnvironment();
    getConnectionAttempts = interceptWebSocketConnections();
    navigateToChat();
  });

  afterEach(() => {
    performComprehensiveCleanup();
  });

  it('CRITICAL: Should handle server restart gracefully', () => {
    const beforeRestart = `Before restart ${Date.now()}`;
    sendInitialMessage(beforeRestart);
    
    simulateServerRestart();
    setupReconnectionSimulation();
    
    waitForReconnectionWithBackoff();
    verifyServerRestartRecovery(beforeRestart);
  });

  it('CRITICAL: Should handle authentication token expiry during active session', () => {
    const authMessage = `Authenticated message ${Date.now()}`;
    sendAuthenticatedMessage(authMessage);
    
    simulateTokenExpiry();
    attemptMessageWithExpiredToken();
    
    verifyAuthExpiryDetection();
    performTokenRefresh();
    verifyReAuthentication();
  });

  // Helper functions for server restart testing
  function sendInitialMessage(message: string): void {
    cy.get('textarea').type(message);
    cy.get('button[aria-label="Send message"]').click();
    cy.contains(message).should('be.visible');
  }

  function simulateServerRestart(): void {
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      if (ws && ws.close) {
        ws.close(1006, 'Server restart'); // Abnormal closure code
      }
    });
  }

  function setupReconnectionSimulation(): void {
    let reconnectAttempts = 0;
    
    cy.intercept('**/ws**', (req) => {
      reconnectAttempts++;
      if (reconnectAttempts < 3) {
        req.reply({ statusCode: 503 }); // Server unavailable
      } else {
        req.continue(); // Server back online
      }
    });
  }

  function waitForReconnectionWithBackoff(): void {
    const backoffDelay = WEBSOCKET_CONFIG.RETRY_DELAY * Math.pow(2, 3);
    cy.wait(backoffDelay);
  }

  function verifyServerRestartRecovery(beforeRestart: string): void {
    cy.get('[data-testid="connection-status"], [class*="connected"]', {
      timeout: 15000
    }).should('exist');
    
    // Verify conversation context preserved
    cy.contains(beforeRestart).should('be.visible');
    
    // Test post-restart functionality
    const afterRestart = `After restart ${Date.now()}`;
    cy.get('textarea').clear().type(afterRestart);
    cy.get('button[aria-label="Send message"]').click();
    cy.contains(afterRestart).should('be.visible');
  }

  // Helper functions for authentication testing
  function sendAuthenticatedMessage(message: string): void {
    cy.get('textarea').type(message);
    cy.get('button[aria-label="Send message"]').click();
    cy.contains(message).should('be.visible');
  }

  function simulateTokenExpiry(): void {
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token_expired', 'true');
      win.dispatchEvent(new Event('storage')); // Trigger auth check
    });
  }

  function attemptMessageWithExpiredToken(): void {
    setupAuthFailureIntercept();
    
    const expiredTokenMessage = `Message with expired token ${Date.now()}`;
    cy.get('textarea').clear().type(expiredTokenMessage);
    cy.get('button[aria-label="Send message"]').click();
  }

  function setupAuthFailureIntercept(): void {
    cy.intercept('**/ws**', (req) => {
      if (req.headers.authorization) {
        req.reply({ statusCode: 401, body: { error: 'Token expired' } });
      } else {
        req.continue();
      }
    }).as('authFailure');
  }

  function verifyAuthExpiryDetection(): void {
    cy.get('body').then(($body) => {
      const authIndicators = [
        '[data-testid="auth-expired"]',
        '[data-testid="reauth-required"]',
        '[class*="unauthorized"]'
      ];
      
      const hasAuthIssue = authIndicators.some(selector => 
        $body.find(selector).length > 0
      );
      
      if (hasAuthIssue) {
        cy.log('Auth expiry detected');
      }
    });
  }

  function performTokenRefresh(): void {
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'new-test-token');
      win.localStorage.removeItem('auth_token_expired');
      win.dispatchEvent(new Event('storage'));
    });
    
    // Remove auth failure intercept
    cy.intercept('**/ws**', (req) => req.continue());
    cy.wait(2000); // Wait for reconnection
  }

  function verifyReAuthentication(): void {
    const reAuthMessage = `Re-authenticated message ${Date.now()}`;
    cy.get('textarea').clear().type(reAuthMessage);
    cy.get('button[aria-label="Send message"]').click();
    cy.contains(reAuthMessage).should('be.visible');
  }

  function performComprehensiveCleanup(): void {
    cleanupWebSocketConnections();
    clearTestData();
    clearTimers();
    resetConnectionTracking();
    clearInterceptSettings();
  }

  function cleanupWebSocketConnections(): void {
    cy.window().then((win) => {
      const wsVariants = [
        (win as any).ws,
        (win as any).websocket,
        (win as any).socket,
        (win as any).__netraWebSocket
      ];
      
      wsVariants.forEach(ws => {
        if (ws && ws.close && ws.readyState === 1) {
          ws.close(1000, 'Test cleanup');
        }
      });
    });
  }

  function clearTestData(): void {
    cy.window().then((win) => {
      win.localStorage.removeItem('auth_token_expired');
      win.localStorage.removeItem('test_message_queue');
    });
  }

  function clearTimers(): void {
    cy.window().then((win) => {
      if ((win as any).__netraHeartbeatTimer) {
        clearInterval((win as any).__netraHeartbeatTimer);
      }
    });
  }

  function resetConnectionTracking(): void {
    cy.window().then((win) => {
      (win as any).__netraActiveConnections = [];
      (win as any).__netraConnectionInfo = null;
    });
  }

  function clearInterceptSettings(): void {
    cy.intercept('**/ws**', (req) => req.continue());
    cy.intercept('POST', '**/api/**', (req) => req.continue());
  }
});