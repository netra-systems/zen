/// <reference types="cypress" />

/**
 * WebSocket Test Helpers and Shared Utilities
 * 
 * Provides common setup, configuration, and helper functions
 * for WebSocket resilience testing across all test modules.
 */

// Configuration constants matching current WebSocketService
export const WEBSOCKET_CONFIG = {
  HEARTBEAT_INTERVAL: 30000, // 30 seconds
  HEARTBEAT_TIMEOUT: 60000, // 60 seconds  
  MAX_CONNECTIONS_PER_USER: 5,
  MAX_RETRY_ATTEMPTS: 10, // Updated to match current service (was 3)
  RETRY_DELAY: 100, // Updated to match current service (was 1000)
  CONNECTION_TIMEOUT: 10000, // 10 seconds
  PING_INTERVAL: 25000, // 25 seconds
  BASE_RECONNECT_DELAY: 100, // New: matches current service
  MAX_RECONNECT_DELAY: 10000, // New: matches current service (was 30s, now 10s)
  WEBSOCKET_ENDPOINT: 'ws://localhost:8000/ws', // New: unified endpoint
};

// Mission-critical WebSocket event types (updated to match current system)
export const CRITICAL_WS_EVENTS = [
  'agent_started',
  'agent_thinking',
  'tool_executing', 
  'tool_completed',
  'agent_completed',
  'final_report', // Added: current system sends this
  'partial_result', // Added: current system may send this
  'agent_fallback' // Added: error handling event
] as const;

export type CriticalWebSocketEvent = typeof CRITICAL_WS_EVENTS[number];

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
  // Navigate directly to chat for faster test execution
  cy.visit('/chat');
  cy.wait(2000); // Wait for app initialization
};

export const findWebSocketConnection = (win: any): WebSocket | null => {
  // Updated to match current WebSocket service integration points
  const possibleWS = [
    win.ws,
    win.websocket,
    win.socket,
    win.__netraWebSocket,
    win.WebSocketManager?.activeConnection,
    win.webSocketService?.ws, // Current service stores WebSocket in .ws property
    win.useUnifiedChatStore?.getState()?.webSocketService?.ws, // Store integration
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

// Mission-critical WebSocket event validation functions (updated)
export const validateCriticalEvents = () => {
  const criticalEvents = [
    'agent_started',
    'agent_thinking', 
    'tool_executing',
    'tool_completed',
    'agent_completed',
    'final_report',
    'partial_result',
    'agent_fallback'
  ];
  
  return {
    events: criticalEvents,
    validate: (eventType: string) => {
      return criticalEvents.includes(eventType);
    },
    // New: Get required events (subset that MUST be present for valid flow)
    getRequiredEvents: () => [
      'agent_started',
      'agent_completed'
    ],
    // New: Get optional events (nice to have but not required)
    getOptionalEvents: () => [
      'agent_thinking',
      'tool_executing', 
      'tool_completed',
      'final_report',
      'partial_result',
      'agent_fallback'
    ]
  };
};

export const testWebSocketEventHandling = () => {
  cy.window().then((win) => {
    const store = (win as any).useUnifiedChatStore?.getState();
    if (store && store.handleWebSocketEvent) {
      cy.log('WebSocket event handling available');
      return store;
    } else {
      cy.log('WebSocket event handling not available');
      return null;
    }
  });
};

export const simulateCriticalWebSocketEvents = () => {
  cy.window().then((win) => {
    const store = (win as any).useUnifiedChatStore?.getState();
    if (store && store.handleWebSocketEvent) {
      const testAgentId = `test-agent-${Date.now()}`;
      const testRunId = `test-run-${Date.now()}`;
      
      // Simulate complete agent lifecycle
      const events = [
        {
          type: 'agent_started',
          payload: {
            agent_id: testAgentId,
            agent_type: 'TestAgent',
            run_id: testRunId,
            timestamp: Date.now()
          }
        },
        {
          type: 'tool_executing',
          payload: {
            tool_name: 'test-tool',
            agent_id: testAgentId,
            timestamp: Date.now()
          }
        },
        {
          type: 'agent_thinking',
          payload: {
            thought: 'Processing test request...',
            agent_id: testAgentId,
            step_number: 1,
            total_steps: 2
          }
        },
        {
          type: 'tool_completed',
          payload: {
            tool_name: 'test-tool',
            result: { success: true, data: 'test result' },
            agent_id: testAgentId,
            timestamp: Date.now()
          }
        },
        {
          type: 'agent_completed',
          payload: {
            agent_id: testAgentId,
            agent_type: 'TestAgent',
            duration_ms: 5000,
            result: { status: 'success' },
            metrics: { tools_used: 1 }
          }
        }
      ];
      
      // Send events with delays to simulate real timing
      events.forEach((event, index) => {
        setTimeout(() => {
          store.handleWebSocketEvent(event);
          cy.log(`Sent ${event.type} event`);
        }, index * 500);
      });
      
      cy.log('All critical WebSocket events simulated');
    }
  });
};

export const verifyWebSocketServiceIntegration = () => {
  cy.window().then((win) => {
    const webSocketService = (win as any).webSocketService;
    if (webSocketService) {
      const securityStatus = webSocketService.getSecurityStatus();
      cy.log('WebSocket security status:', securityStatus);
      
      expect(securityStatus).to.have.property('authMethod');
      expect(securityStatus).to.have.property('hasToken');
      expect(securityStatus).to.have.property('tokenRefreshEnabled');
      
      return securityStatus;
    } else {
      cy.log('WebSocket service not available');
      return null;
    }
  });
};

export const monitorWebSocketEvents = (duration: number = 10000): Cypress.Chainable<any[]> => {
  const events: any[] = [];
  
  return cy.window().then((win): Cypress.Chainable<any[]> => {
    const ws = findWebSocketConnection(win);
    if (ws) {
      const originalOnMessage = ws.onmessage;
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          events.push({
            timestamp: Date.now(),
            type: data.type,
            payload: data.payload || data.data, // Handle both payload and data fields
            raw: data
          });
          
          cy.log(`WebSocket event: ${data.type}`);
        } catch (e) {
          // Log parsing errors but continue
          cy.log(`WebSocket parsing error: ${e}`);
        }
        
        // Call original handler
        if (originalOnMessage) {
          originalOnMessage.call(ws, event);
        }
      };
      
      // Return promise that resolves with events after duration
      return cy.wrap(new Promise<any[]>((resolve) => {
        setTimeout(() => {
          // Restore original handler
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.onmessage = originalOnMessage;
          }
          cy.log(`Monitored ${events.length} WebSocket events over ${duration}ms`);
          resolve(events);
        }, duration);
      }));
    } else {
      cy.log('No WebSocket connection found for monitoring');
      return cy.wrap([]);
    }
  });
};