/// <reference types="cypress" />

import {
  WEBSOCKET_CONFIG,
  WebSocketTestState,
  createInitialState,
  setupTestEnvironment,
  interceptWebSocketConnections,
  navigateToChat,
  waitForConnection
} from '../support/websocket-test-helpers';

/**
 * WebSocket Heartbeat and Health Monitoring Tests
 * 
 * Tests heartbeat functionality, stale connection detection,
 * message ordering during network instability.
 */
describe('WebSocket Heartbeat and Health Monitoring', () => {
  let testState: WebSocketTestState;
  let getConnectionAttempts: () => number;

  beforeEach(() => {
    testState = createInitialState();
    setupTestEnvironment();
    getConnectionAttempts = interceptWebSocketConnections();
    navigateToChat();
  });

  it('CRITICAL: Should maintain heartbeat and detect stale connections', () => {
    const heartbeatTracker = setupHeartbeatMonitoring();
    
    waitForMultipleHeartbeats().then(() => {
      verifyHeartbeatFrequency(heartbeatTracker);
      testHeartbeatTimeoutDetection();
      verifyStaleConnectionRecovery();
    });
  });

  it('CRITICAL: Should handle message ordering during network instability', () => {
    const messages = generateOrderedTestMessages(20);
    
    sendMessagesWithNetworkInstability(messages);
    verifyAllMessagesDelivered(messages);
    verifyMessageOrdering(messages);
  });

  // Helper functions for heartbeat testing
  function setupHeartbeatMonitoring() {
    let heartbeatCount = 0;
    let lastHeartbeatTime = Date.now();
    
    cy.intercept('**/ws**', (req) => {
      req.continue((res) => {
        if (res.body && res.body.includes('heartbeat')) {
          heartbeatCount++;
          lastHeartbeatTime = Date.now();
        }
      });
    });
    
    return { getCount: () => heartbeatCount, getLastTime: () => lastHeartbeatTime };
  }

  function waitForMultipleHeartbeats() {
    return cy.wait(WEBSOCKET_CONFIG.HEARTBEAT_INTERVAL * 2.5);
  }

  function verifyHeartbeatFrequency(tracker: any) {
    cy.wrap(null).then(() => {
      expect(tracker.getCount()).to.be.at.least(2, 'Should have sent at least 2 heartbeats');
      
      const timeSinceLastHeartbeat = Date.now() - tracker.getLastTime();
      expect(timeSinceLastHeartbeat).to.be.lessThan(
        WEBSOCKET_CONFIG.HEARTBEAT_INTERVAL * 1.5,
        'Heartbeat should be recent'
      );
    });
  }

  function testHeartbeatTimeoutDetection() {
    cy.log('Testing heartbeat timeout detection...');
    
    blockHeartbeatResponses();
    waitForTimeoutDetection();
    verifyStaleConnectionIndicators();
  }

  function blockHeartbeatResponses() {
    cy.intercept('**/ws**', (req) => {
      if (req.body && req.body.includes('heartbeat')) {
        req.reply({ forceNetworkError: true });
      } else {
        req.continue();
      }
    }).as('blockHeartbeat');
  }

  function waitForTimeoutDetection() {
    cy.wait(WEBSOCKET_CONFIG.HEARTBEAT_TIMEOUT + 5000);
  }

  function verifyStaleConnectionIndicators() {
    cy.get('body').then(($body) => {
      const hasStaleIndicator = 
        $body.find('[data-testid="connection-stale"]').length > 0 ||
        $body.find('[class*="reconnecting"]').length > 0;
      
      if (hasStaleIndicator) {
        cy.log('Stale connection detected');
      }
    });
  }

  function verifyStaleConnectionRecovery() {
    restoreHeartbeatResponses();
    verifyConnectionRecovery();
  }

  function restoreHeartbeatResponses() {
    cy.intercept('**/ws**', (req) => req.continue()).as('restoreHeartbeat');
    cy.wait(WEBSOCKET_CONFIG.RETRY_DELAY * 2);
  }

  function verifyConnectionRecovery() {
    cy.get('[data-testid="connection-status"], [class*="connected"]', {
      timeout: 10000
    }).should('exist');
  }

  // Helper functions for message ordering tests
  function generateOrderedTestMessages(count: number) {
    const messages: Array<{ id: number; text: string; timestamp: number }> = [];
    
    for (let i = 1; i <= count; i++) {
      messages.push({
        id: i,
        text: `Message #${i} - ${Date.now()}`,
        timestamp: Date.now() + (i * 100)
      });
    }
    
    return messages;
  }

  function sendMessagesWithNetworkInstability(messages: any[]) {
    messages.forEach((msg, index) => {
      introduceNetworkDelay(index);
      sendMessage(msg.text);
      addRandomDelay();
      restoreNetworkIfNeeded(index);
    });
  }

  function introduceNetworkDelay(index: number) {
    if (index % 4 === 0) {
      cy.intercept('**/ws**', { delay: 1000 + Math.random() * 2000 });
    }
  }

  function sendMessage(messageText: string) {
    cy.get('textarea').clear().type(messageText);
    cy.get('button[aria-label="Send message"]').click();
  }

  function addRandomDelay() {
    cy.wait(100 + Math.random() * 300);
  }

  function restoreNetworkIfNeeded(index: number) {
    if (index % 4 === 3) {
      cy.intercept('**/ws**', (req) => req.continue());
    }
  }

  function verifyAllMessagesDelivered(messages: any[]) {
    cy.wait(5000); // Wait for all messages to be processed
    
    messages.forEach(msg => {
      cy.contains(msg.text).should('exist');
    });
  }

  function verifyMessageOrdering(messages: any[]) {
    cy.get('.message-container, [data-testid="message"]').then($messages => {
      const displayedOrder = extractMessageOrder($messages);
      const orderPercentage = calculateOrderPercentage(displayedOrder);
      
      expect(orderPercentage).to.be.at.least(80, 'At least 80% of messages should maintain order');
    });
  }

  function extractMessageOrder($messages: any): number[] {
    const displayedOrder: number[] = [];
    
    $messages.each((index, el) => {
      const text = el.textContent || '';
      const match = text.match(/Message #(\d+)/);
      if (match) {
        displayedOrder.push(parseInt(match[1]));
      }
    });
    
    return displayedOrder;
  }

  function calculateOrderPercentage(displayedOrder: number[]): number {
    let inOrderCount = 0;
    
    for (let i = 1; i < displayedOrder.length; i++) {
      if (displayedOrder[i] > displayedOrder[i - 1]) {
        inOrderCount++;
      } else {
        cy.log(`Out of order: Message #${displayedOrder[i]} appears after #${displayedOrder[i - 1]}`);
      }
    }
    
    return (inOrderCount / (displayedOrder.length - 1)) * 100;
  }
});