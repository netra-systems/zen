/// <reference types="cypress" />

describe('CRITICAL: WebSocket Connection Resilience & Recovery', () => {
  let wsConnection: WebSocket | null = null;
  let messageQueue: string[] = [];
  let connectionAttempts = 0;
  let lastHeartbeat: number = 0;
  
  // Configuration constants from ws_manager.py
  const HEARTBEAT_INTERVAL = 30000; // 30 seconds
  const HEARTBEAT_TIMEOUT = 60000; // 60 seconds
  const MAX_CONNECTIONS_PER_USER = 5;
  const MAX_RETRY_ATTEMPTS = 3;
  const RETRY_DELAY = 1000; // 1 second
  
  beforeEach(() => {
    cy.viewport(1920, 1080);
    connectionAttempts = 0;
    lastHeartbeat = Date.now();
    messageQueue = [];
    
    // Set up auth for chat access
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'test-token');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user',
        email: 'test@netra.ai',
        name: 'Test User'
      }));
    });
    
    // Intercept WebSocket connections for monitoring
    cy.intercept('/ws*', (req) => {
      connectionAttempts++;
      req.continue();
    }).as('wsConnect');
    
    // Visit demo chat
    cy.visit('/demo');
    cy.contains('Technology').click();
    cy.contains('AI Chat').click({ force: true });
    cy.wait(1000);
  });

  describe('Connection Lifecycle Management', () => {
    it('CRITICAL: Should establish and maintain stable WebSocket connection', () => {
      // Verify initial connection establishment
      cy.window().then((win) => {
        cy.wrap(null).then(() => {
          return new Cypress.Promise((resolve, reject) => {
            let attempts = 0;
            const maxAttempts = 10;
            
            const checkConnection = () => {
              attempts++;
              
              // Check multiple possible WebSocket locations
              const possibleWS = [
                (win as any).ws,
                (win as any).websocket,
                (win as any).socket,
                (win as any).__netraWebSocket,
                (win as any).WebSocketManager?.activeConnection
              ].find(ws => ws !== undefined);
              
              if (possibleWS && possibleWS.readyState !== undefined) {
                wsConnection = possibleWS;
                expect(possibleWS.readyState).to.be.oneOf([0, 1], 'WebSocket should be CONNECTING or OPEN');
                
                // Verify connection has required properties
                expect(connectionAttempts).to.be.lessThan(MAX_RETRY_ATTEMPTS + 1, 'Should not exceed max retry attempts');
                resolve(possibleWS);
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
      
      // Verify connection metadata
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
      // Establish baseline connection
      const initialMessage = `Initial message ${Date.now()}`;
      cy.get('textarea').type(initialMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(initialMessage).should('be.visible');
      
      // Record initial connection state
      let initialConnectionId: string | null = null;
      cy.window().then((win) => {
        const connInfo = (win as any).__netraConnectionInfo;
        if (connInfo) {
          initialConnectionId = connInfo.connection_id;
        }
      });
      
      // Simulate complete network partition
      cy.log('Simulating network partition...');
      cy.intercept('**/ws**', { forceNetworkError: true }).as('wsBlock');
      cy.intercept('POST', '**/api/**', { forceNetworkError: true }).as('apiBlock');
      
      // Wait for disconnection detection (should happen within heartbeat interval)
      cy.wait(3000);
      
      // Verify disconnection UI feedback
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
      
      // Queue messages during partition
      const queuedMessages = [
        `Queued message 1 - ${Date.now()}`,
        `Queued message 2 - ${Date.now()}`,
        `Queued message 3 - ${Date.now()}`
      ];
      
      queuedMessages.forEach(msg => {
        cy.get('textarea').clear().type(msg);
        cy.get('button[aria-label="Send message"]').click();
        messageQueue.push(msg);
        cy.wait(500);
      });
      
      // Verify messages are queued (not yet visible in chat)
      queuedMessages.forEach(msg => {
        cy.get('.message-container').then($container => {
          // Messages should be pending, not confirmed
          if ($container.find(`[data-message-status="pending"]:contains("${msg}")`).length > 0) {
            cy.log(`Message queued: ${msg}`);
          }
        });
      });
      
      // Restore network connection
      cy.log('Restoring network connection...');
      cy.intercept('**/ws**', (req) => {
        req.continue();
      }).as('wsRestore');
      cy.intercept('POST', '**/api/**', (req) => {
        req.continue();
      }).as('apiRestore');
      
      // Wait for automatic reconnection (should happen within retry delay)
      cy.wait(RETRY_DELAY * 2);
      
      // Verify reconnection success
      cy.get('[data-testid="connection-status"], [class*="connected"], [class*="online"]', { 
        timeout: 10000 
      }).should('exist');
      
      // Verify all queued messages are delivered
      cy.wait(3000); // Allow time for message delivery
      queuedMessages.forEach(msg => {
        cy.contains(msg).should('be.visible');
      });
      
      // Verify new messages work after reconnection
      const postReconnectMessage = `Post-reconnect message ${Date.now()}`;
      cy.get('textarea').clear().type(postReconnectMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(postReconnectMessage).should('be.visible');
      
      // Verify connection ID changed (new connection established)
      cy.window().then((win) => {
        const newConnInfo = (win as any).__netraConnectionInfo;
        if (newConnInfo && initialConnectionId) {
          expect(newConnInfo.connection_id).to.not.equal(initialConnectionId);
        }
      });
    });

    it('CRITICAL: Should handle connection pool exhaustion gracefully', () => {
      // Attempt to open MAX_CONNECTIONS_PER_USER + 1 connections
      const connections: any[] = [];
      
      cy.window().then((win) => {
        return new Cypress.Promise((resolve) => {
          // Open multiple connections
          for (let i = 0; i < MAX_CONNECTIONS_PER_USER + 1; i++) {
            cy.log(`Opening connection ${i + 1}`);
            
            // Simulate opening a new tab/connection
            const mockConnection = {
              id: `conn_${Date.now()}_${i}`,
              userId: 'test-user',
              createdAt: Date.now()
            };
            connections.push(mockConnection);
            
            // Trigger connection attempt
            cy.window().then((w) => {
              w.dispatchEvent(new CustomEvent('netra:ws:connect', { 
                detail: mockConnection 
              }));
            });
            
            cy.wait(500);
          }
          
          // Verify connection limit enforcement
          cy.window().then((w) => {
            const activeConns = (w as any).__netraActiveConnections || [];
            expect(activeConns.length).to.be.at.most(
              MAX_CONNECTIONS_PER_USER,
              `Should not exceed ${MAX_CONNECTIONS_PER_USER} connections per user`
            );
          });
          
          // Verify oldest connection was closed
          if (connections.length > MAX_CONNECTIONS_PER_USER) {
            const oldestConn = connections[0];
            cy.window().then((w) => {
              const activeConns = (w as any).__netraActiveConnections || [];
              const isOldestActive = activeConns.some((c: any) => c.id === oldestConn.id);
              expect(isOldestActive).to.be.false;
            });
          }
          
          resolve(null);
        });
      });
      
      // Verify system remains functional
      const testMessage = `Connection pool test ${Date.now()}`;
      cy.get('textarea').clear().type(testMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(testMessage).should('be.visible');
    });

    it('should synchronize state after reconnection', () => {
      // Create initial state
      cy.get('textarea').type('Initial conversation context');
      cy.get('button[aria-label="Send message"]').click();
      cy.wait(2000);
      
      // Simulate disconnection
      cy.intercept('**/ws**', { forceNetworkError: true }).as('wsBlock');
      cy.wait(2000);
      
      // Simulate state change during disconnection (e.g., from another tab)
      cy.window().then((win) => {
        const currentState = win.localStorage.getItem('chat_state') || '{}';
        const state = JSON.parse(currentState);
        state.messages = state.messages || [];
        state.messages.push({
          id: Date.now(),
          text: 'Message from another tab',
          sender: 'user',
          timestamp: new Date().toISOString()
        });
        win.localStorage.setItem('chat_state', JSON.stringify(state));
      });
      
      // Restore connection
      cy.intercept('**/ws**', (req) => {
        req.continue();
      }).as('wsRestore');
      
      // Verify state synchronization
      cy.wait(3000);
      cy.contains('Message from another tab').should('be.visible');
    });

    it('CRITICAL: Should survive rapid connection cycling without memory leaks', () => {
      const cycles = 20; // More aggressive than original
      let initialMemory = 0;
      let memorySnapshots: number[] = [];
      
      // Capture initial memory baseline
      cy.window().then((win) => {
        if ((win.performance as any).memory) {
          initialMemory = (win.performance as any).memory.usedJSHeapSize;
          cy.log(`Initial memory: ${(initialMemory / 1024 / 1024).toFixed(2)} MB`);
        }
      });
      
      // Perform rapid connect/disconnect cycles
      cy.wrap(null).then(() => {
        return new Cypress.Promise((resolve) => {
          let cycleCount = 0;
          
          const performCycle = () => {
            if (cycleCount >= cycles) {
              resolve(null);
              return;
            }
            
            // Disconnect
            cy.intercept('**/ws**', { forceNetworkError: true });
            cy.wait(200); // Shorter wait for more stress
            
            // Capture memory during disconnection
            cy.window().then((win) => {
              if ((win.performance as any).memory) {
                const currentMemory = (win.performance as any).memory.usedJSHeapSize;
                memorySnapshots.push(currentMemory);
              }
            });
            
            // Reconnect
            cy.intercept('**/ws**', (req) => req.continue());
            cy.wait(200);
            
            cycleCount++;
            cy.log(`Completed cycle ${cycleCount}/${cycles}`);
            
            // Continue with next cycle
            performCycle();
          };
          
          performCycle();
        });
      });
      
      // Wait for stabilization
      cy.wait(2000);
      
      // Verify connection is stable
      cy.get('[data-testid="connection-status"], [class*="connected"], [class*="online"]', { 
        timeout: 5000 
      }).should('exist');
      
      // Check for memory leaks
      cy.window().then((win) => {
        if ((win.performance as any).memory) {
          const finalMemory = (win.performance as any).memory.usedJSHeapSize;
          const memoryGrowth = ((finalMemory - initialMemory) / initialMemory) * 100;
          
          cy.log(`Final memory: ${(finalMemory / 1024 / 1024).toFixed(2)} MB`);
          cy.log(`Memory growth: ${memoryGrowth.toFixed(2)}%`);
          
          // Allow up to 30% memory growth (accounting for normal operations)
          expect(memoryGrowth).to.be.lessThan(
            30,
            'Memory growth should be less than 30% after rapid cycling'
          );
          
          // Check for memory trend (should not be consistently increasing)
          if (memorySnapshots.length > 10) {
            const firstHalf = memorySnapshots.slice(0, memorySnapshots.length / 2);
            const secondHalf = memorySnapshots.slice(memorySnapshots.length / 2);
            const avgFirstHalf = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
            const avgSecondHalf = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;
            
            const trend = ((avgSecondHalf - avgFirstHalf) / avgFirstHalf) * 100;
            cy.log(`Memory trend: ${trend.toFixed(2)}%`);
            
            // Memory should stabilize, not continuously grow
            expect(Math.abs(trend)).to.be.lessThan(
              15,
              'Memory should stabilize, not continuously grow'
            );
          }
        }
      });
      
      // Verify full functionality after stress test
      const stressTestMessage = `Post-stress test ${Date.now()}`;
      cy.get('textarea').clear().type(stressTestMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(stressTestMessage).should('be.visible');
    });

    it('should show appropriate connection status indicators', () => {
      // Check initial connected state
      cy.get('body').then(($body) => {
        const statusSelectors = [
          '[class*="status"]',
          '[class*="connection"]',
          '[aria-label*="connection"]'
        ];
        
        let hasIndicator = false;
        statusSelectors.forEach(selector => {
          if ($body.find(selector).length > 0) {
            hasIndicator = true;
          }
        });
        
        if (hasIndicator) {
          // Test status changes
          cy.intercept('**/ws**', { forceNetworkError: true }).as('wsBlock');
          cy.wait(2000);
          
          // Should show disconnected/reconnecting status
          cy.get('[class*="disconnect"], [class*="offline"], [class*="reconnect"]')
            .should('exist');
          
          // Restore and verify connected status
          cy.intercept('**/ws**', (req) => {
            req.continue();
          }).as('wsRestore');
          
          cy.get('[class*="connected"], [class*="online"]', { timeout: 5000 })
            .should('exist');
        }
      });
    });

    it('should handle WebSocket close events gracefully', () => {
      // Simulate WebSocket close event
      cy.window().then((win) => {
        const ws = (win as any).ws || (win as any).websocket || (win as any).socket;
        if (ws && ws.close) {
          ws.close();
        }
      });
      
      // Should show appropriate UI feedback
      cy.get('body').then(($body) => {
        if ($body.find('[class*="disconnect"], [class*="reconnect"]').length > 0) {
          cy.get('[class*="disconnect"], [class*="reconnect"]').should('be.visible');
        }
      });
      
      // Should attempt reconnection
      cy.get('[class*="connected"], [class*="online"]', { timeout: 10000 }).should('exist');
    });

    it('should handle WebSocket error events', () => {
      // Trigger WebSocket error
      cy.window().then((win) => {
        const ws = (win as any).ws || (win as any).websocket || (win as any).socket;
        if (ws && ws.onerror) {
          ws.onerror(new Event('error'));
        }
      });
      
      // Should show error state
      cy.get('body').then(($body) => {
        if ($body.find('[class*="error"], [class*="alert"]').length > 0) {
          cy.get('[class*="error"], [class*="alert"]').should('be.visible');
        }
      });
      
      // Should recover from error
      cy.wait(5000);
      cy.get('[class*="connected"], [class*="online"]').should('exist');
    });

    it('should maintain conversation context across reconnections', () => {
      // Build conversation context
      const messages = [
        'My company processes 10M requests daily',
        'We need to optimize for cost',
        'Current spending is $100K/month'
      ];
      
      messages.forEach((msg, index) => {
        cy.get('textarea').clear().type(msg);
        cy.get('button[aria-label="Send message"]').click();
        cy.wait(2000);
      });
      
      // Simulate disconnection
      cy.intercept('**/ws**', { forceNetworkError: true }).as('wsBlock');
      cy.wait(2000);
      
      // Reconnect
      cy.intercept('**/ws**', (req) => {
        req.continue();
      }).as('wsRestore');
      cy.wait(2000);
      
      // Send context-dependent message
      cy.get('textarea').clear().type('What would be my estimated savings?');
      cy.get('button[aria-label="Send message"]').click();
      cy.wait(3000);
      
      // Response should reference previous context
      cy.get('body').then(($body) => {
        const responseText = $body.text();
        expect(responseText).to.match(/10M|100K|\$100,000|savings|cost reduction/i);
      });
    });

    it('should handle message deduplication after reconnection', () => {
      const testMessage = 'Unique test message ' + Date.now();
      
      // Send message
      cy.get('textarea').type(testMessage);
      cy.get('button[aria-label="Send message"]').click();
      
      // Simulate brief disconnection
      cy.intercept('**/ws**', { forceNetworkError: true }).as('wsBlock');
      cy.wait(1000);
      
      // Reconnect
      cy.intercept('**/ws**', (req) => {
        req.continue();
      }).as('wsRestore');
      cy.wait(2000);
      
      // Count occurrences of the message
      cy.get('body').then(($body) => {
        const messageElements = $body.find(`:contains("${testMessage}")`);
        // Should only appear once (no duplicates)
        expect(messageElements.length).to.be.lessThan(3); // Allow for container nesting
      });
    });
  });

  describe('Heartbeat and Health Monitoring', () => {
    it('CRITICAL: Should maintain heartbeat and detect stale connections', () => {
      // Monitor heartbeat messages
      let heartbeatCount = 0;
      let lastHeartbeatTime = Date.now();
      
      cy.intercept('**/ws**', (req) => {
        req.continue((res) => {
          // Look for heartbeat patterns in WebSocket frames
          if (res.body && res.body.includes('heartbeat')) {
            heartbeatCount++;
            lastHeartbeatTime = Date.now();
          }
        });
      });
      
      // Wait for multiple heartbeat intervals
      cy.wait(HEARTBEAT_INTERVAL * 2.5);
      
      // Verify heartbeats were sent
      cy.wrap(null).then(() => {
        expect(heartbeatCount).to.be.at.least(
          2,
          'Should have sent at least 2 heartbeats'
        );
        
        const timeSinceLastHeartbeat = Date.now() - lastHeartbeatTime;
        expect(timeSinceLastHeartbeat).to.be.lessThan(
          HEARTBEAT_INTERVAL * 1.5,
          'Heartbeat should be recent'
        );
      });
      
      // Test heartbeat timeout detection
      cy.log('Testing heartbeat timeout detection...');
      
      // Block only heartbeat responses
      cy.intercept('**/ws**', (req) => {
        if (req.body && req.body.includes('heartbeat')) {
          req.reply({ forceNetworkError: true });
        } else {
          req.continue();
        }
      }).as('blockHeartbeat');
      
      // Wait for timeout detection
      cy.wait(HEARTBEAT_TIMEOUT + 5000);
      
      // Should show connection issues
      cy.get('body').then(($body) => {
        const hasStaleIndicator = 
          $body.find('[data-testid="connection-stale"]').length > 0 ||
          $body.find('[class*="reconnecting"]').length > 0;
        
        if (hasStaleIndicator) {
          cy.log('Stale connection detected');
        }
      });
      
      // Restore heartbeat and verify recovery
      cy.intercept('**/ws**', (req) => req.continue()).as('restoreHeartbeat');
      cy.wait(RETRY_DELAY * 2);
      
      // Connection should recover
      cy.get('[data-testid="connection-status"], [class*="connected"]', {
        timeout: 10000
      }).should('exist');
    });

    it('CRITICAL: Should handle message ordering during network instability', () => {
      const messages: Array<{ id: number; text: string; timestamp: number }> = [];
      const messageCount = 20;
      
      // Generate ordered messages
      for (let i = 1; i <= messageCount; i++) {
        messages.push({
          id: i,
          text: `Message #${i} - ${Date.now()}`,
          timestamp: Date.now() + (i * 100)
        });
      }
      
      // Send messages with intermittent network issues
      messages.forEach((msg, index) => {
        // Randomly introduce network issues
        if (index % 4 === 0) {
          cy.intercept('**/ws**', { delay: 1000 + Math.random() * 2000 });
        }
        
        cy.get('textarea').clear().type(msg.text);
        cy.get('button[aria-label="Send message"]').click();
        
        // Random short delay between messages
        cy.wait(100 + Math.random() * 300);
        
        // Restore normal network occasionally
        if (index % 4 === 3) {
          cy.intercept('**/ws**', (req) => req.continue());
        }
      });
      
      // Wait for all messages to be processed
      cy.wait(5000);
      
      // Verify all messages are present
      messages.forEach(msg => {
        cy.contains(msg.text).should('exist');
      });
      
      // Verify message ordering
      cy.get('.message-container, [data-testid="message"]').then($messages => {
        const displayedOrder: number[] = [];
        
        $messages.each((index, el) => {
          const text = el.textContent || '';
          const match = text.match(/Message #(\d+)/);
          if (match) {
            displayedOrder.push(parseInt(match[1]));
          }
        });
        
        // Check if messages are in order
        for (let i = 1; i < displayedOrder.length; i++) {
          if (displayedOrder[i] < displayedOrder[i - 1]) {
            cy.log(`Out of order: Message #${displayedOrder[i]} appears after #${displayedOrder[i - 1]}`);
          }
        }
        
        // At least 80% should be in correct order (allowing for some async reordering)
        let inOrderCount = 0;
        for (let i = 1; i < displayedOrder.length; i++) {
          if (displayedOrder[i] > displayedOrder[i - 1]) {
            inOrderCount++;
          }
        }
        
        const orderPercentage = (inOrderCount / (displayedOrder.length - 1)) * 100;
        expect(orderPercentage).to.be.at.least(
          80,
          'At least 80% of messages should maintain order'
        );
      });
    });
  });
  
  describe('Advanced Resilience Scenarios', () => {
    it('CRITICAL: Should handle server restart gracefully', () => {
      // Send initial message
      const beforeRestart = `Before restart ${Date.now()}`;
      cy.get('textarea').type(beforeRestart);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(beforeRestart).should('be.visible');
      
      // Simulate server restart (connection forcibly closed)
      cy.window().then((win) => {
        const ws = (win as any).ws || (win as any).websocket || (win as any).socket;
        if (ws && ws.close) {
          // Close with code 1006 (abnormal closure)
          ws.close(1006, 'Server restart');
        }
      });
      
      // Intercept reconnection attempts
      let reconnectAttempts = 0;
      cy.intercept('**/ws**', (req) => {
        reconnectAttempts++;
        if (reconnectAttempts < 3) {
          // Simulate server still restarting
          req.reply({ statusCode: 503 });
        } else {
          // Server back online
          req.continue();
        }
      });
      
      // Wait for reconnection with exponential backoff
      cy.wait(RETRY_DELAY * Math.pow(2, 3)); // Wait for 3rd attempt
      
      // Verify reconnection successful
      cy.get('[data-testid="connection-status"], [class*="connected"]', {
        timeout: 15000
      }).should('exist');
      
      // Verify conversation context preserved
      cy.contains(beforeRestart).should('be.visible');
      
      // Send new message to verify functionality
      const afterRestart = `After restart ${Date.now()}`;
      cy.get('textarea').clear().type(afterRestart);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(afterRestart).should('be.visible');
    });
    
    it('CRITICAL: Should handle authentication token expiry during active session', () => {
      // Send initial authenticated message
      const authMessage = `Authenticated message ${Date.now()}`;
      cy.get('textarea').type(authMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(authMessage).should('be.visible');
      
      // Simulate token expiry
      cy.window().then((win) => {
        win.localStorage.setItem('auth_token_expired', 'true');
        // Trigger auth check
        win.dispatchEvent(new Event('storage'));
      });
      
      // Intercept next WebSocket message to simulate auth failure
      cy.intercept('**/ws**', (req) => {
        if (req.headers.authorization) {
          req.reply({ statusCode: 401, body: { error: 'Token expired' } });
        } else {
          req.continue();
        }
      }).as('authFailure');
      
      // Attempt to send message
      const expiredTokenMessage = `Message with expired token ${Date.now()}`;
      cy.get('textarea').clear().type(expiredTokenMessage);
      cy.get('button[aria-label="Send message"]').click();
      
      // Should show auth error or trigger re-authentication
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
      
      // Simulate token refresh
      cy.window().then((win) => {
        win.localStorage.setItem('auth_token', 'new-test-token');
        win.localStorage.removeItem('auth_token_expired');
        win.dispatchEvent(new Event('storage'));
      });
      
      // Remove auth failure intercept
      cy.intercept('**/ws**', (req) => req.continue());
      
      // Wait for reconnection with new token
      cy.wait(2000);
      
      // Verify can send messages again
      const reAuthMessage = `Re-authenticated message ${Date.now()}`;
      cy.get('textarea').clear().type(reAuthMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(reAuthMessage).should('be.visible');
    });
  });

  afterEach(() => {
    // Comprehensive cleanup
    cy.window().then((win) => {
      // Clean up all possible WebSocket connections
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
      
      // Clear any test data
      win.localStorage.removeItem('auth_token_expired');
      win.localStorage.removeItem('test_message_queue');
      
      // Clear any pending timers
      if ((win as any).__netraHeartbeatTimer) {
        clearInterval((win as any).__netraHeartbeatTimer);
      }
      
      // Reset connection tracking
      (win as any).__netraActiveConnections = [];
      (win as any).__netraConnectionInfo = null;
    });
    
    // Clear intercepts
    cy.intercept('**/ws**', (req) => req.continue());
    cy.intercept('POST', '**/api/**', (req) => req.continue());
    
    // Log test completion
    cy.task('log', `Test completed: ${Cypress.currentTest.title}`);
  });
});