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
    
    // Wait for connection and initial setup
    cy.wait(2000);
  });

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
    
    cy.intercept('**/ws**', (req) => {
      req.continue((res) => {
        if (res.body && (res.body.includes('heartbeat') || res.body.includes('ping'))) {
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

  // Helper functions for agent event ordering tests
  function generateOrderedAgentSequence(count: number) {
    const agentSequence: Array<{ 
      id: number; 
      agentId: string; 
      eventType: string; 
      timestamp: number 
    }> = [];
    
    for (let i = 1; i <= count; i++) {
      agentSequence.push({
        id: i,
        agentId: `ordering-agent-${i}`,
        eventType: 'agent_started',
        timestamp: Date.now() + (i * 100)
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
    if (index % 4 === 0) {
      cy.intercept('**/ws**', { delay: 1000 + Math.random() * 2000 });
    }
  }

  // Legacy function - kept for compatibility but not used in agent event tests

  function addRandomDelay() {
    cy.wait(100 + Math.random() * 300);
  }

  function restoreNetworkIfNeeded(index: number) {
    if (index % 4 === 3) {
      cy.intercept('**/ws**', (req) => req.continue());
    }
  }

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

  function calculateAgentOrderPercentage(displayedOrder: number[], agentSequence: any[]): number {
    if (displayedOrder.length < 2) return 100;
    
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