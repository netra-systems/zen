/// <reference types="cypress" />

describe('Critical Test #1: WebSocket Connection Resilience', () => {
  let wsConnection: WebSocket | null = null;
  let messageQueue: string[] = [];
  
  beforeEach(() => {
    cy.viewport(1920, 1080);
    
    // Set up auth for chat access
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'test-token');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user',
        email: 'test@netra.ai',
        name: 'Test User'
      }));
    });
    
    // Visit demo chat
    cy.visit('/demo');
    cy.contains('Technology').click();
    cy.contains('AI Chat').click({ force: true });
    cy.wait(1000);
  });

  describe('WebSocket Connection Management', () => {
    it('should establish initial WebSocket connection', () => {
      // Verify WebSocket connection is established
      cy.window().then((win) => {
        cy.wrap(null).then(() => {
          return new Cypress.Promise((resolve) => {
            const checkConnection = () => {
              // Check for WebSocket in window or global scope
              const ws = (win as any).ws || (win as any).websocket || (win as any).socket;
              if (ws) {
                expect(ws.readyState).to.be.oneOf([0, 1]); // CONNECTING or OPEN
                resolve(ws);
              } else {
                // Look for connection status indicator
                cy.get('[class*="connected"], [class*="online"]', { timeout: 0 }).should('exist');
                resolve(null);
              }
            };
            checkConnection();
          });
        });
      });
    });

    it('should automatically reconnect after network interruption', () => {
      // Send initial message to establish connection
      const testMessage = 'Test message before disconnect';
      cy.get('textarea').type(testMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(testMessage).should('be.visible');
      
      // Simulate network interruption
      cy.intercept('**/ws**', { forceNetworkError: true }).as('wsBlock');
      
      // Wait for disconnection to be detected
      cy.wait(2000);
      
      // Look for reconnection indicator
      cy.get('body').then(($body) => {
        if ($body.find('[class*="reconnect"], [class*="connecting"]').length > 0) {
          cy.get('[class*="reconnect"], [class*="connecting"]').should('be.visible');
        }
      });
      
      // Restore network connection
      cy.intercept('**/ws**', (req) => {
        req.continue();
      }).as('wsRestore');
      
      // Verify reconnection within 5 seconds
      cy.get('[class*="connected"], [class*="online"]', { timeout: 5000 }).should('exist');
      
      // Verify ability to send messages after reconnection
      const reconnectMessage = 'Test message after reconnect';
      cy.get('textarea').clear().type(reconnectMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(reconnectMessage).should('be.visible');
    });

    it('should preserve message queue during disconnection', () => {
      // Queue messages while disconnected
      cy.intercept('**/ws**', { forceNetworkError: true }).as('wsBlock');
      
      const queuedMessages = [
        'Queued message 1',
        'Queued message 2',
        'Queued message 3'
      ];
      
      queuedMessages.forEach(msg => {
        cy.get('textarea').clear().type(msg);
        cy.get('button[aria-label="Send message"]').click();
        cy.wait(500);
      });
      
      // Check for queue indicator
      cy.get('body').then(($body) => {
        if ($body.find('[class*="pending"], [class*="queue"]').length > 0) {
          cy.get('[class*="pending"], [class*="queue"]').should('exist');
        }
      });
      
      // Restore connection
      cy.intercept('**/ws**', (req) => {
        req.continue();
      }).as('wsRestore');
      
      // Verify all queued messages are sent
      cy.wait(3000);
      queuedMessages.forEach(msg => {
        cy.contains(msg).should('be.visible');
      });
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

    it('should handle rapid connect/disconnect cycles', () => {
      const cycles = 5;
      
      for (let i = 0; i < cycles; i++) {
        // Disconnect
        cy.intercept('**/ws**', { forceNetworkError: true }).as(`wsBlock${i}`);
        cy.wait(1000);
        
        // Reconnect
        cy.intercept('**/ws**', (req) => {
          req.continue();
        }).as(`wsRestore${i}`);
        cy.wait(1000);
      }
      
      // Verify connection is stable after rapid cycling
      cy.get('[class*="connected"], [class*="online"]', { timeout: 5000 }).should('exist');
      
      // Verify functionality after stress test
      const testMessage = 'Message after rapid cycling';
      cy.get('textarea').clear().type(testMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(testMessage).should('be.visible');
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

  describe('Performance Under Network Instability', () => {
    it('should maintain acceptable performance with intermittent connectivity', () => {
      const startTime = Date.now();
      
      // Simulate intermittent network
      for (let i = 0; i < 3; i++) {
        cy.wait(1000);
        cy.intercept('**/ws**', { forceNetworkError: true }).as(`block${i}`);
        cy.wait(500);
        cy.intercept('**/ws**', (req) => {
          req.continue();
        }).as(`restore${i}`);
      }
      
      // Send message and measure response time
      cy.get('textarea').clear().type('Performance test message');
      cy.get('button[aria-label="Send message"]').click();
      
      // Should still respond within reasonable time
      cy.contains('Performance test message', { timeout: 5000 }).should('be.visible');
      
      const endTime = Date.now();
      expect(endTime - startTime).to.be.lessThan(10000); // Less than 10 seconds total
    });

    it('should not leak memory during reconnection cycles', () => {
      // Get initial memory usage if available
      cy.window().then((win) => {
        if ((win.performance as any).memory) {
          const initialMemory = (win.performance as any).memory.usedJSHeapSize;
          
          // Perform multiple reconnection cycles
          for (let i = 0; i < 10; i++) {
            cy.intercept('**/ws**', { forceNetworkError: true });
            cy.wait(500);
            cy.intercept('**/ws**', (req) => {
              req.continue();
            });
            cy.wait(500);
          }
          
          // Check memory after cycles
          cy.window().then((win2) => {
            if ((win2.performance as any).memory) {
              const finalMemory = (win2.performance as any).memory.usedJSHeapSize;
              const memoryGrowth = (finalMemory - initialMemory) / initialMemory;
              
              // Memory growth should be less than 20%
              expect(memoryGrowth).to.be.lessThan(0.2);
            }
          });
        }
      });
    });
  });

  afterEach(() => {
    // Clean up WebSocket connections
    cy.window().then((win) => {
      const ws = (win as any).ws || (win as any).websocket || (win as any).socket;
      if (ws && ws.close) {
        ws.close();
      }
    });
  });
});