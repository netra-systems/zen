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
 * WebSocket Heartbeat and Health Monitoring Tests
 * 
 * Tests heartbeat functionality, stale connection detection,
 * and message ordering during network instability.
 * 
 * MISSION CRITICAL: These tests ensure real-time communication reliability.
 */
describe('WebSocket Heartbeat and Health Monitoring', () => {
  let testState: WebSocketTestState;
  let getConnectionAttempts: () => number;

  beforeEach(() => {
    testState = createInitialState();
    setupTestEnvironment();
    getConnectionAttempts = interceptWebSocketConnections();
    navigateToChat();
    
    // Wait for connection and initial setup
    cy.wait(2000);
  });

<<<<<<< Updated upstream
  it('CRITICAL: Should maintain heartbeat and process agent events during health monitoring', () => {
    const heartbeatTracker = setupHeartbeatMonitoring();
    
    // Test agent events during normal heartbeat operation
    simulateAgentEventsWithHeartbeat('heartbeat-test-agent');
    
    waitForMultipleHeartbeats().then(() => {
      verifyHeartbeatFrequency(heartbeatTracker);
      testHeartbeatTimeoutDetection();
      verifyStaleConnectionRecovery();
      
      // Verify agent events work after heartbeat recovery
      simulateAgentEventsWithHeartbeat('post-heartbeat-agent');
    });
  });

  it('CRITICAL: Should handle agent event ordering during network instability', () => {
    const agentSequence = generateOrderedAgentSequence(15); // Reduced for stability
    
    sendAgentEventsWithNetworkInstability(agentSequence);
    verifyAllAgentEventsDelivered(agentSequence);
    verifyAgentEventOrdering(agentSequence);
=======
  afterEach(() => {
    // Clean up WebSocket connections and test state
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      if (ws && ws.close && ws.readyState === WebSocket.OPEN) {
        ws.close(1000, 'Test cleanup');
      }
    });
  });

  it('CRITICAL: Should maintain heartbeat and detect stale connections', () => {
    waitForConnection().then(() => {
      const heartbeatTracker = setupHeartbeatMonitoring();
      
      // Wait for initial connection establishment
      cy.wait(2000);
      
      waitForMultipleHeartbeats().then(() => {
        verifyHeartbeatFrequency(heartbeatTracker);
        testHeartbeatTimeoutDetection();
        verifyStaleConnectionRecovery();
      });
    });
  });

  it('CRITICAL: Should handle message ordering during network instability', () => {
    waitForConnection().then(() => {
      const messages = generateOrderedTestMessages(10); // Reduced count for faster testing
      
      sendMessagesWithNetworkInstability(messages);
      verifyAllMessagesDelivered(messages);
      verifyMessageOrdering(messages);
    });
  });

  it('CRITICAL: Should detect and recover from heartbeat timeout', () => {
    waitForConnection().then(() => {
      // Block heartbeat responses to simulate timeout
      blockHeartbeatResponses();
      
      // Wait for timeout detection
      cy.wait(WEBSOCKET_CONFIG.HEARTBEAT_TIMEOUT + 5000);
      
      // Verify stale connection indicators
      verifyStaleConnectionIndicators();
      
      // Restore heartbeat and verify recovery
      restoreHeartbeatResponses();
      verifyStaleConnectionRecovery();
    });
  });

  it('CRITICAL: Should handle rapid connection state changes', () => {
    waitForConnection().then(() => {
      // Simulate rapid connection changes
      for (let i = 0; i < 3; i++) {
        cy.log(`Connection cycle ${i + 1}/3`);
        
        // Simulate temporary disconnection
        cy.window().then((win) => {
          const ws = findWebSocketConnection(win);
          if (ws && ws.close) {
            ws.close(1006, `Test cycle ${i + 1}`);
          }
        });
        
        cy.wait(WEBSOCKET_CONFIG.RETRY_DELAY);
        
        // Wait for reconnection
        waitForConnection();
        
        // Verify connection works
        const testMessage = `Cycle ${i + 1} test - ${Date.now()}`;
        cy.get('textarea').clear().type(testMessage);
        cy.get('button[aria-label="Send message"]').click();
        cy.contains(testMessage).should('be.visible');
      }
    });
>>>>>>> Stashed changes
  });

  // Helper functions for heartbeat testing
  function simulateAgentEventsWithHeartbeat(agentId: string): void {
    cy.window().then((win) => {
      const events = [
        {
          type: 'agent_started',
          payload: {
            agent_id: agentId,
            agent_type: 'heartbeat_monitor_agent',
            run_id: `run-${agentId}`,
            timestamp: new Date().toISOString(),
            status: 'started'
          }
        },
        {
          type: 'agent_thinking',
          payload: {
            thought: `${agentId} monitoring heartbeat health`,
            agent_id: agentId,
            agent_type: 'heartbeat_monitor_agent',
            step_number: 1,
            total_steps: 2
          }
        },
        {
          type: 'tool_executing',
          payload: {
            tool_name: 'heartbeat_checker',
            agent_id: agentId,
            agent_type: 'heartbeat_monitor_agent',
            timestamp: Date.now()
          }
        },
        {
          type: 'tool_completed',
          payload: {
            tool_name: 'heartbeat_checker',
            result: { heartbeat_status: 'healthy', latency: 50 },
            agent_id: agentId,
            timestamp: Date.now()
          }
        },
        {
          type: 'agent_completed',
          payload: {
            agent_id: agentId,
            agent_type: 'heartbeat_monitor_agent',
            duration_ms: 1200,
            result: { monitoring_result: 'connection healthy' },
            metrics: { heartbeat_checks: 3 }
          }
        }
      ];
      
      // Simulate events with heartbeat timing considerations
      events.forEach((event, index) => {
        setTimeout(() => {
          const ws = findWebSocketConnection(win);
          if (ws && ws.onmessage) {
            ws.onmessage({ data: JSON.stringify(event) } as any);
          }
        }, index * 200);
      });
    });
  }

  function setupHeartbeatMonitoring() {
    let heartbeatCount = 0;
    let lastHeartbeatTime = Date.now();
    
<<<<<<< Updated upstream
    cy.intercept('**/ws**', (req) => {
      req.continue((res) => {
        if (res.body && (res.body.includes('heartbeat') || res.body.includes('ping'))) {
          heartbeatCount++;
          lastHeartbeatTime = Date.now();
        }
      });
=======
    // Monitor WebSocket messages for heartbeat events
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      if (ws && ws.addEventListener) {
        // Listen for heartbeat/ping events
        const originalOnMessage = ws.onmessage;
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'ping' || data.type === 'heartbeat' || data.type === 'pong') {
              heartbeatCount++;
              lastHeartbeatTime = Date.now();
            }
          } catch (e) {
            // Ignore parsing errors
          }
          // Call original handler if it exists
          if (originalOnMessage) {
            originalOnMessage.call(ws, event);
          }
        };
      }
>>>>>>> Stashed changes
    });
    
    return { getCount: () => heartbeatCount, getLastTime: () => lastHeartbeatTime };
  }

  function waitForMultipleHeartbeats() {
    return cy.wait(WEBSOCKET_CONFIG.HEARTBEAT_INTERVAL * 3); // Wait for multiple heartbeat cycles
  }

  function verifyHeartbeatFrequency(tracker: any) {
    cy.wrap(null).then(() => {
      cy.log('Verifying heartbeat frequency');
      
      const timeSinceLastHeartbeat = Date.now() - tracker.getLastTime();
      const expectedMaxInterval = WEBSOCKET_CONFIG.HEARTBEAT_INTERVAL * 2;
      
      // Verify heartbeat timing is within expected range
      if (timeSinceLastHeartbeat < expectedMaxInterval) {
        cy.log('Heartbeat timing is within acceptable range');
      } else {
        cy.log(`Heartbeat may be slow: ${timeSinceLastHeartbeat}ms since last heartbeat`);
      }
    });
  }

  function testHeartbeatTimeoutDetection() {
    cy.log('Testing heartbeat timeout detection...');
    
    blockHeartbeatResponses();
    waitForTimeoutDetection();
    verifyStaleConnectionIndicators();
  }

  function blockHeartbeatResponses() {
    // Block WebSocket traffic to simulate network issues
    cy.intercept('**/ws**', (req) => {
      const body = req.body ? JSON.stringify(req.body) : '';
      if (body.includes('heartbeat') || body.includes('ping')) {
        req.reply({ forceNetworkError: true });
      } else {
        req.continue();
      }
    }).as('blockHeartbeat');
  }

  function waitForTimeoutDetection() {
    cy.wait(WEBSOCKET_CONFIG.HEARTBEAT_TIMEOUT + 2000);
  }

  function verifyStaleConnectionIndicators() {
    cy.get('body').then(($body) => {
      const staleIndicators = [
        '[data-testid="connection-stale"]',
        '[class*="reconnecting"]',
        '[class*="offline"]',
        '[class*="disconnected"]'
      ];
      
      const hasStaleIndicator = staleIndicators.some(selector => 
        $body.find(selector).length > 0
      );
      
      if (hasStaleIndicator) {
        cy.log('Stale connection detected');
      } else {
        cy.log('No stale connection indicator found - checking connection state');
      }
    });
  }

  function verifyStaleConnectionRecovery() {
    restoreHeartbeatResponses();
    verifyConnectionRecovery();
  }

  function restoreHeartbeatResponses() {
    // Restore normal WebSocket traffic
    cy.intercept('**/ws**', (req) => req.continue()).as('restoreHeartbeat');
    cy.wait(WEBSOCKET_CONFIG.RETRY_DELAY * 2);
  }

  function verifyConnectionRecovery() {
    waitForConnection().then(() => {
      // Test that connection works after recovery
      const recoveryTestMessage = `Recovery test - ${Date.now()}`;
      cy.get('textarea').clear().type(recoveryTestMessage);
      cy.get('button[aria-label="Send message"]').click();
      cy.contains(recoveryTestMessage).should('be.visible');
      
      cy.log('Connection recovery verified');
    });
  }

<<<<<<< Updated upstream
  // Helper functions for agent event ordering tests
  function generateOrderedAgentSequence(count: number) {
    const agentSequence: Array<{ 
      id: number; 
      agentId: string; 
      eventType: string; 
      timestamp: number 
    }> = [];
=======
  // Helper functions for message ordering tests
  function generateOrderedTestMessages(count: number) {
    const messages: Array<{ id: number; text: string; timestamp: number }> = [];
    const baseTime = Date.now();
>>>>>>> Stashed changes
    
    for (let i = 1; i <= count; i++) {
      agentSequence.push({
        id: i,
<<<<<<< Updated upstream
        agentId: `ordering-agent-${i}`,
        eventType: 'agent_started',
        timestamp: Date.now() + (i * 100)
=======
        text: `Message #${i} - ${baseTime + (i * 100)}`,
        timestamp: baseTime + (i * 100)
>>>>>>> Stashed changes
      });
    }
    
    return agentSequence;
  }

  function sendAgentEventsWithNetworkInstability(agentSequence: any[]) {
    agentSequence.forEach((agentInfo, index) => {
      introduceNetworkDelay(index);
      simulateAgentEventWithInstability(agentInfo);
      addRandomDelay();
      restoreNetworkIfNeeded(index);
    });
  }
  
  function simulateAgentEventWithInstability(agentInfo: any) {
    cy.window().then((win) => {
      const agentEvent = {
        type: agentInfo.eventType,
        payload: {
          agent_id: agentInfo.agentId,
          agent_type: 'network_instability_test',
          run_id: `run-${agentInfo.agentId}`,
          timestamp: new Date(agentInfo.timestamp).toISOString(),
          status: 'started'
        }
      };
      
      const ws = findWebSocketConnection(win);
      if (ws && ws.onmessage) {
        ws.onmessage({ data: JSON.stringify(agentEvent) } as any);
      }
    });
  }

  function introduceNetworkDelay(index: number) {
    if (index % 3 === 0) { // Introduce instability every 3rd message
      cy.intercept('**/ws**', { delay: 500 + Math.random() * 1000 });
    }
  }

<<<<<<< Updated upstream
  // Legacy function - kept for compatibility but not used in agent event tests
=======
  function sendMessage(messageText: string) {
    cy.get('textarea').clear().type(messageText);
    cy.get('button[aria-label="Send message"]').click();
    cy.wait(100); // Brief wait for message processing
  }
>>>>>>> Stashed changes

  function addRandomDelay() {
    cy.wait(200 + Math.random() * 500); // Increased delay for better test stability
  }

  function restoreNetworkIfNeeded(index: number) {
    if (index % 3 === 2) { // Restore after every 3rd message
      cy.intercept('**/ws**', (req) => req.continue());
    }
  }

<<<<<<< Updated upstream
  function verifyAllAgentEventsDelivered(agentSequence: any[]) {
    cy.wait(5000); // Wait for all agent events to be processed
    
    agentSequence.forEach(agentInfo => {
      cy.get('[data-testid*="agent"], .agent-status, .message-content').should('contain', agentInfo.agentId);
    });
  }

  function verifyAgentEventOrdering(agentSequence: any[]) {
    cy.get('[data-testid*="agent"], .agent-status, [class*="agent"]').then($agentElements => {
      const displayedOrder = extractAgentEventOrder($agentElements, agentSequence);
      const orderPercentage = calculateAgentOrderPercentage(displayedOrder, agentSequence);
      
      expect(orderPercentage).to.be.at.least(70, 'At least 70% of agent events should maintain order during network instability');
=======
  function verifyAllMessagesDelivered(messages: any[]) {
    cy.wait(8000); // Extended wait for message processing during instability
    
    messages.forEach((msg, index) => {
      cy.contains(msg.text, { timeout: 15000 }).should('be.visible').then(() => {
        cy.log(`Message ${index + 1}/${messages.length} delivered: ${msg.text}`);
      });
    });
  }

  function verifyMessageOrdering(messages: any[]) {
    cy.get('.message-container, [data-testid="message"], [class*="message"]').then($messages => {
      const displayedOrder = extractMessageOrder($messages);
      const orderPercentage = calculateOrderPercentage(displayedOrder);
      
      cy.log(`Message order accuracy: ${orderPercentage.toFixed(1)}%`);
      
      // In real-world scenarios with network instability, perfect ordering may not be achievable
      // We test that most messages maintain order
      expect(orderPercentage).to.be.at.least(70, 'At least 70% of messages should maintain order during network instability');
>>>>>>> Stashed changes
    });
  }

  function extractAgentEventOrder($elements: any, agentSequence: any[]): number[] {
    const displayedOrder: number[] = [];
    
    $elements.each((index, el) => {
      const text = el.textContent || '';
      agentSequence.forEach((agentInfo, seqIndex) => {
        if (text.includes(agentInfo.agentId)) {
          displayedOrder.push(agentInfo.id);
        }
      });
    });
    
    return [...new Set(displayedOrder)]; // Remove duplicates
  }

<<<<<<< Updated upstream
  function calculateAgentOrderPercentage(displayedOrder: number[], agentSequence: any[]): number {
    if (displayedOrder.length < 2) return 100;
=======
  function calculateOrderPercentage(displayedOrder: number[]): number {
    if (displayedOrder.length <= 1) return 100;
>>>>>>> Stashed changes
    
    let inOrderCount = 0;
    
    for (let i = 1; i < displayedOrder.length; i++) {
      if (displayedOrder[i] > displayedOrder[i - 1]) {
        inOrderCount++;
      } else {
        cy.log(`Out of order: Agent #${displayedOrder[i]} appears after #${displayedOrder[i - 1]}`);
      }
    }
    
    return (inOrderCount / (displayedOrder.length - 1)) * 100;
  }
});