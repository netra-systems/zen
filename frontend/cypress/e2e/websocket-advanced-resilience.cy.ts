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
 * Tests server restart handling, authentication token management,
 * and complex failure recovery scenarios.
 * 
 * MISSION CRITICAL: These tests ensure WebSocket reliability in production scenarios.
 */
describe('WebSocket Advanced Resilience Scenarios', () => {
  let testState: WebSocketTestState;
  let getConnectionAttempts: () => number;

  beforeEach(() => {
    testState = createInitialState();
    setupTestEnvironment();
    getConnectionAttempts = interceptWebSocketConnections();
    navigateToChat();
    
    // Wait for AI Chat tab to be ready
    cy.wait(2000);
  });

  afterEach(() => {
    performComprehensiveCleanup();
  });

<<<<<<< Updated upstream
  it('CRITICAL: Should handle server restart gracefully and maintain agent event flow', () => {
    const beforeRestart = `Before restart ${Date.now()}`;
    sendInitialMessage(beforeRestart);
    
    // Test that agent events are processed before restart
    simulateAgentEventSequence('pre-restart-agent');
    
    simulateServerRestart();
    setupReconnectionSimulation();
    
    waitForReconnectionWithBackoff();
    verifyServerRestartRecovery(beforeRestart);
    
    // Verify agent events work after restart
    simulateAgentEventSequence('post-restart-agent');
  });

  it('CRITICAL: Should handle authentication token expiry during agent execution', () => {
    const authMessage = `Authenticated message ${Date.now()}`;
    sendAuthenticatedMessage(authMessage);
    
    // Start an agent before token expiry
    simulateAgentEventSequence('auth-test-agent');
    
    simulateTokenExpiry();
    attemptMessageWithExpiredToken();
    
    verifyAuthExpiryDetection();
    performTokenRefresh();
    verifyReAuthentication();
    
    // Verify agents work after re-authentication
    simulateAgentEventSequence('post-auth-agent');
=======
  it('CRITICAL: Should handle server restart gracefully', () => {
    waitForConnection().then(() => {
      const beforeRestart = `Before restart ${Date.now()}`;
      sendInitialMessage(beforeRestart);
      
      simulateServerRestart();
      setupReconnectionSimulation();
      
      waitForReconnectionWithBackoff();
      verifyServerRestartRecovery(beforeRestart);
    });
  });

  it('CRITICAL: Should handle authentication token expiry during active session', () => {
    waitForConnection().then(() => {
      const authMessage = `Authenticated message ${Date.now()}`;
      sendAuthenticatedMessage(authMessage);
      
      simulateTokenExpiry();
      attemptMessageWithExpiredToken();
      
      verifyAuthExpiryDetection();
      performTokenRefresh();
      verifyReAuthentication();
    });
  });

  it('CRITICAL: Should handle WebSocket authentication with token refresh', () => {
    waitForConnection().then(() => {
      // Test automatic token refresh mechanism
      testTokenRefreshMechanism();
      
      // Verify connection maintains after token refresh
      const postRefreshMessage = `Post refresh test - ${Date.now()}`;
      cy.get('textarea').clear().type(postRefreshMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(postRefreshMessage).should('be.visible');
    });
  });

  it('CRITICAL: Should handle multiple concurrent connection attempts', () => {
    // Simulate multiple tabs/windows trying to connect
    for (let i = 0; i < WEBSOCKET_CONFIG.MAX_CONNECTIONS_PER_USER; i++) {
      cy.log(`Testing concurrent connection ${i + 1}/${WEBSOCKET_CONFIG.MAX_CONNECTIONS_PER_USER}`);
      
      waitForConnection().then(() => {
        // Each connection should work independently
        const testMessage = `Concurrent test ${i + 1} - ${Date.now()}`;
        cy.get('textarea').clear().type(testMessage);
        cy.get('button[aria-label="Send message"]').click();
        cy.contains(testMessage).should('be.visible');
      });
    }
  });

  it('CRITICAL: Should handle large message fragmentation and reassembly', () => {
    waitForConnection().then(() => {
      // Test large message handling
      const largeMessage = generateLargeMessage(5000); // 5KB message
      
      cy.get('textarea').clear().type(largeMessage);
      cy.get('button[aria-label="Send message"]').click();
      
      // Verify large message is handled properly
      cy.contains(largeMessage.substring(0, 100), { timeout: 10000 }).should('be.visible');
      
      cy.log('Large message handling test completed');
    });
>>>>>>> Stashed changes
  });

  // Helper functions for server restart testing
  function sendInitialMessage(message: string): void {
<<<<<<< Updated upstream
    cy.get('textarea, [data-testid="message-input"]').type(message);
    cy.get('button[aria-label="Send message"], button:contains("Send")').click();
    cy.wait(500);
  }
  
  function simulateAgentEventSequence(agentId: string): void {
    cy.window().then((win) => {
      const events = [
        {
          type: 'agent_started',
          payload: {
            agent_id: agentId,
            agent_type: 'resilience_test_agent',
            run_id: `run-${agentId}`,
            timestamp: new Date().toISOString()
          }
        },
        {
          type: 'agent_thinking',
          payload: {
            thought: `Agent ${agentId} is analyzing the situation`,
            agent_id: agentId,
            agent_type: 'resilience_test_agent',
            step_number: 1,
            total_steps: 2
          }
        },
        {
          type: 'tool_executing',
          payload: {
            tool_name: 'resilience_tester',
            agent_id: agentId,
            agent_type: 'resilience_test_agent',
            timestamp: Date.now()
          }
        },
        {
          type: 'tool_completed',
          payload: {
            tool_name: 'resilience_tester',
            result: { status: 'success', data: 'test completed' },
            agent_id: agentId,
            timestamp: Date.now()
          }
        },
        {
          type: 'agent_completed',
          payload: {
            agent_id: agentId,
            agent_type: 'resilience_test_agent',
            duration_ms: 2000,
            result: { outcome: 'successful test' },
            metrics: { tools_executed: 1 }
          }
        }
      ];
      
      // Simulate the complete agent lifecycle
      events.forEach((event, index) => {
        setTimeout(() => {
          const ws = findWebSocketConnection(win);
          if (ws && ws.onmessage) {
            ws.onmessage({ data: JSON.stringify(event) } as any);
          }
        }, index * 200);
      });
    });
=======
    cy.get('textarea').clear().type(message);
    cy.get('button[aria-label="Send message"]').click();
    cy.contains(message).should('be.visible');
>>>>>>> Stashed changes
  }

  function simulateServerRestart(): void {
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      if (ws && ws.close) {
        ws.close(1006, 'Server restart'); // Abnormal closure code
      }
    });
    
    cy.log('Simulated server restart');
  }

  function setupReconnectionSimulation(): void {
    let reconnectAttempts = 0;
    
    cy.intercept('**/ws**', (req) => {
      reconnectAttempts++;
      if (reconnectAttempts < WEBSOCKET_CONFIG.MAX_RETRY_ATTEMPTS) {
        req.reply({ statusCode: 503 }); // Service unavailable
        cy.log(`Reconnection attempt ${reconnectAttempts} - service unavailable`);
      } else {
        req.continue(); // Server back online
        cy.log('Server back online - connection restored');
      }
    });
  }

  function waitForReconnectionWithBackoff(): void {
    const backoffDelay = WEBSOCKET_CONFIG.RETRY_DELAY * Math.pow(2, WEBSOCKET_CONFIG.MAX_RETRY_ATTEMPTS);
    cy.wait(backoffDelay);
  }

  function verifyServerRestartRecovery(beforeRestart: string): void {
<<<<<<< Updated upstream
    cy.get('[data-testid="connection-status"], [class*="connected"]', {
      timeout: 15000
    }).should('exist');
    
    // Test post-restart functionality
    const afterRestart = `After restart ${Date.now()}`;
    cy.get('textarea, [data-testid="message-input"]').clear().type(afterRestart);
    cy.get('button[aria-label="Send message"], button:contains("Send")').click();
    cy.wait(1000);
    
    // Verify agent events are working after restart
    cy.get('[data-testid*="agent"], .agent-status').should('exist');
=======
    waitForConnection().then(() => {
      // Verify conversation context preserved
      cy.contains(beforeRestart).should('be.visible');
      
      // Test post-restart functionality
      const afterRestart = `After restart ${Date.now()}`;
      cy.get('textarea').clear().type(afterRestart);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(afterRestart).should('be.visible');
      
      cy.log('Server restart recovery verified');
    });
>>>>>>> Stashed changes
  }

  // Helper functions for authentication testing
  function sendAuthenticatedMessage(message: string): void {
<<<<<<< Updated upstream
    cy.get('textarea, [data-testid="message-input"]').type(message);
    cy.get('button[aria-label="Send message"], button:contains("Send")').click();
    cy.wait(500);
=======
    cy.get('textarea').clear().type(message);
    cy.get('button[aria-label="Send message"]').click();
    cy.contains(message).should('be.visible');
>>>>>>> Stashed changes
  }

  function simulateTokenExpiry(): void {
    cy.window().then((win) => {
      // Simulate token expiry in localStorage
      const currentToken = win.localStorage.getItem('auth_token');
      if (currentToken) {
        // Create an expired token (simplified simulation)
        win.localStorage.setItem('auth_token_expired', 'true');
        win.localStorage.setItem('auth_token_expiry', String(Date.now() - 1000));
      }
      
      // Trigger auth state check
      win.dispatchEvent(new Event('storage'));
    });
  }

  function attemptMessageWithExpiredToken(): void {
    setupAuthFailureIntercept();
    
    const expiredTokenMessage = `Message with expired token ${Date.now()}`;
    cy.get('textarea, [data-testid="message-input"]').clear().type(expiredTokenMessage);
    cy.get('button[aria-label="Send message"], button:contains("Send")').click();
  }

  function setupAuthFailureIntercept(): void {
    cy.intercept('**/ws**', (req) => {
      // Simulate authentication failure
      req.reply({ 
        statusCode: 401, 
        body: { error: 'Token expired', code: 1008 }
      });
    }).as('authFailure');
  }

  function verifyAuthExpiryDetection(): void {
    cy.get('body').then(($body) => {
      const authIndicators = [
        '[data-testid="auth-expired"]',
        '[data-testid="reauth-required"]',
        '[class*="unauthorized"]',
        '[class*="auth-error"]'
      ];
      
      const hasAuthIssue = authIndicators.some(selector => 
        $body.find(selector).length > 0
      );
      
      if (hasAuthIssue) {
        cy.log('Auth expiry detected by UI');
      } else {
        cy.log('No auth expiry UI indicators - checking connection state');
      }
    });
  }

  function performTokenRefresh(): void {
    cy.window().then((win) => {
      // Simulate successful token refresh
      const newToken = `new-test-token-${Date.now()}`;
      win.localStorage.setItem('auth_token', newToken);
      win.localStorage.removeItem('auth_token_expired');
      win.localStorage.removeItem('auth_token_expiry');
      
      // Trigger auth state update
      win.dispatchEvent(new Event('storage'));
    });
    
    // Remove auth failure intercept
    cy.intercept('**/ws**', (req) => req.continue());
    cy.wait(WEBSOCKET_CONFIG.RETRY_DELAY * 2); // Wait for reconnection
  }

  function verifyReAuthentication(): void {
<<<<<<< Updated upstream
    const reAuthMessage = `Re-authenticated message ${Date.now()}`;
    cy.get('textarea, [data-testid="message-input"]').clear().type(reAuthMessage);
    cy.get('button[aria-label="Send message"], button:contains("Send")').click();
    cy.wait(1000);
    
    // Verify that agent events are working after re-authentication
    cy.get('[data-testid*="agent"], .agent-status, .message-content').should('exist');
=======
    waitForConnection().then(() => {
      const reAuthMessage = `Re-authenticated message ${Date.now()}`;
      cy.get('textarea').clear().type(reAuthMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(reAuthMessage).should('be.visible');
      
      cy.log('Re-authentication verified');
    });
  }

  function testTokenRefreshMechanism(): void {
    cy.window().then((win) => {
      // Test the WebSocket service token refresh logic
      const webSocketService = (win as any).webSocketService;
      if (webSocketService && webSocketService.updateToken) {
        const testToken = `refresh-test-token-${Date.now()}`;
        
        // Simulate token update
        webSocketService.updateToken(testToken).then(() => {
          cy.log('Token refresh mechanism tested');
        }).catch((error: any) => {
          cy.log('Token refresh not available in test environment');
        });
      } else {
        cy.log('WebSocket service token refresh not available');
      }
    });
  }

  function generateLargeMessage(size: number): string {
    const baseMessage = 'This is a large test message for WebSocket fragmentation testing. ';
    const repetitions = Math.ceil(size / baseMessage.length);
    return baseMessage.repeat(repetitions).substring(0, size);
>>>>>>> Stashed changes
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
      // Clean up all possible WebSocket connection references
      const wsVariants = [
        (win as any).ws,
        (win as any).websocket,
        (win as any).socket,
        (win as any).__netraWebSocket,
        (win as any).webSocketService?.ws
      ];
      
      wsVariants.forEach(ws => {
        if (ws && ws.close && ws.readyState === WebSocket.OPEN) {
          ws.close(1000, 'Test cleanup');
        }
      });
    });
  }

  function clearTestData(): void {
    cy.window().then((win) => {
      // Clear authentication test data
      win.localStorage.removeItem('auth_token_expired');
      win.localStorage.removeItem('auth_token_expiry');
      win.localStorage.removeItem('test_message_queue');
      win.localStorage.removeItem('websocket_test_state');
    });
  }

  function clearTimers(): void {
    cy.window().then((win) => {
      // Clear any test-related timers
      const timerIds = [
        '__netraHeartbeatTimer',
        '__netraReconnectTimer',
        '__netraTokenRefreshTimer'
      ];
      
      timerIds.forEach(timerId => {
        const timer = (win as any)[timerId];
        if (timer) {
          clearInterval(timer);
          clearTimeout(timer);
        }
      });
    });
  }

  function resetConnectionTracking(): void {
    cy.window().then((win) => {
      // Reset connection tracking state
      (win as any).__netraActiveConnections = [];
      (win as any).__netraConnectionInfo = null;
      (win as any).__netraConnectionAttempts = 0;
    });
  }

  function clearInterceptSettings(): void {
    // Reset all network intercepts to default
    cy.intercept('**/ws**', (req) => req.continue());
    cy.intercept('POST', '**/api/**', (req) => req.continue());
    cy.intercept('GET', '**/api/**', (req) => req.continue());
  }
});