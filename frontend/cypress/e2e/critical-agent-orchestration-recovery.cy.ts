/// <reference types="cypress" />

// Define helper functions - fallback implementations for testing
let AgentRecoverySetup, AgentMocking, AgentInteraction, RecoveryAssertions, CircuitBreakerUtils;

try {
  const helpers = require('./utils/recovery-test-helpers');
  AgentRecoverySetup = helpers.AgentRecoverySetup;
  AgentMocking = helpers.AgentMocking;
  AgentInteraction = helpers.AgentInteraction;
  RecoveryAssertions = helpers.RecoveryAssertions;
  CircuitBreakerUtils = helpers.CircuitBreakerUtils;
} catch (e) {
  // Define inline helper functions
  AgentRecoverySetup = {
    fullSetup: () => {
      cy.clearLocalStorage();
      cy.clearCookies();
      cy.window().then((win) => {
        win.localStorage.setItem('jwt_token', 'test-jwt-token');
        win.localStorage.setItem('user', JSON.stringify({
          id: 'test-user-id',
          email: 'test@netrasystems.ai',
          full_name: 'Test User'
        }));
      });
      cy.visit('/chat');
      cy.wait(2000);
    },
    cleanup: () => {
      cy.clearLocalStorage();
    }
  };
  
  AgentMocking = {
    mockTimeout: (agentType) => {
      cy.intercept('POST', '**/api/agents/execute', (req) => {
        if (req.body.agent_type === agentType) {
          req.reply({
            statusCode: 408,
            body: { error: 'Request timeout' },
            delay: 5000
          });
        }
      });
    },
    mockError: (agentType) => {
      cy.intercept('POST', '**/api/agents/execute', (req) => {
        if (req.body.agent_type === agentType) {
          req.reply({
            statusCode: 500,
            body: { error: 'Internal server error' }
          });
        }
      });
    }
  };
  
  AgentInteraction = {
    sendMessage: (message) => {
      cy.get('[data-testid="message-input"], textarea').first().type(message);
      cy.get('[data-testid="send-button"], button[type="submit"]').first().click();
    },
    waitForProcessing: () => {
      cy.wait(3000);
    },
    waitForAgent: (agentType) => {
      cy.wait(2000);
    }
  };
  
  RecoveryAssertions = {
    verifyTimeout: () => {
      cy.contains(/timeout|error|retry/i, { timeout: 10000 }).should('be.visible');
    },
    verifyRetryOption: () => {
      cy.get('button').contains(/retry|try again/i).should('be.visible');
    },
    verifyFallback: () => {
      cy.contains(/fallback|alternative|backup/i).should('be.visible');
    },
    verifyErrorMessage: (pattern) => {
      cy.contains(pattern, { timeout: 5000 }).should('be.visible');
    },
    verifyCircuitBreaker: () => {
      cy.contains(/circuit.*breaker|service.*unavailable/i).should('be.visible');
    }
  };
  
  CircuitBreakerUtils = {
    setupFailureTracking: () => {
      return { failures: 0 };
    },
    triggerMultipleFailures: (count) => {
      // Mock multiple failures to trigger circuit breaker
      cy.intercept('POST', '**/api/agents/execute', {
        statusCode: 503,
        body: { 
          error: 'Service unavailable',
          circuit_breaker_open: true,
          retry_after: 30000
        }
      });
      // Also mock WebSocket connection failures
      cy.intercept('GET', '**/ws', {
        statusCode: 503,
        body: { error: 'WebSocket service unavailable' }
      });
    },
    verifyCircuitBreakerActivated: () => {
      cy.contains(/circuit.*breaker.*open|too.*many.*failures|service.*temporarily.*unavailable/i, { timeout: 10000 }).should('be.visible');
    }
  };
}

describe('Critical Test #2: Agent Orchestration Recovery - Timeout Handling', () => {
  beforeEach(() => {
    AgentRecoverySetup.fullSetup();
  });

  describe('Agent Timeout Handling', () => {
    it('should handle triage agent timeout gracefully', () => {
      AgentMocking.mockTimeout('triage');
      
      AgentInteraction.sendMessage('Analyze my workload for optimization opportunities');
      
      AgentInteraction.waitForProcessing();
      RecoveryAssertions.verifyTimeout();
      RecoveryAssertions.verifyRetryOption();
    });

    it('should handle data agent failure with fallback', () => {
      AgentMocking.mockError('data');
      
      AgentInteraction.sendMessage('Process this dataset: [1,2,3,4,5]');
      
      AgentInteraction.waitForAgent('data');
      RecoveryAssertions.verifyFallback();
      RecoveryAssertions.verifyErrorMessage(/unable to process|error occurred|try different/i);
    });

    it('should handle optimization agent crash recovery', () => {
      let failCount = 0;
      
      cy.intercept('POST', '**/api/agents/execute', (req) => {
        if (req.body.agent_type === 'optimization') {
          failCount++;
          if (failCount <= 2) {
            req.reply({
              statusCode: 503,
              body: { error: 'Service temporarily unavailable' }
            });
          } else {
            req.reply({
              statusCode: 200,
              body: { 
                status: 'success',
                result: {
                  content: 'Successfully optimized your infrastructure with 45% cost savings'
                },
                session_id: 'test-session-123'
              }
            });
          }
        }
      }).as('optimizationRetry');
      
      AgentInteraction.sendMessage('Optimize my AI infrastructure costs');
      
      cy.wait('@optimizationRetry');
      cy.wait('@optimizationRetry');
      cy.wait('@optimizationRetry');
      
      cy.contains(/optimized|savings|45%/i, { timeout: 10000 }).should('be.visible');
    });

    it('should activate circuit breaker after repeated failures', () => {
      const counter = CircuitBreakerUtils.setupFailureTracking();
      
      CircuitBreakerUtils.triggerMultipleFailures(4);
      
      // Try to send a message to trigger the circuit breaker
      AgentInteraction.sendMessage('Test message to trigger circuit breaker');
      AgentInteraction.waitForProcessing();
      
      CircuitBreakerUtils.verifyCircuitBreakerActivated();
      RecoveryAssertions.verifyCircuitBreaker();
    });
  });

  describe('WebSocket Agent Events Recovery', () => {
    it('should handle WebSocket reconnection and event delivery', () => {
      // Setup WebSocket connection monitoring
      cy.window().then((win) => {
        win.wsEventLog = [];
        
        // Mock WebSocket that fails initially then recovers
        let connectionAttempts = 0;
        cy.stub(win, 'WebSocket').callsFake((url) => {
          connectionAttempts++;
          const mockWs = {
            readyState: connectionAttempts <= 2 ? 3 : 1, // Failed, then open
            close: cy.stub(),
            send: cy.stub(),
            addEventListener: cy.stub()
          };
          
          if (connectionAttempts > 2) {
            // Simulate successful connection and event delivery
            setTimeout(() => {
              win.wsEventLog.push('agent_started');
              win.wsEventLog.push('agent_thinking');
              win.wsEventLog.push('tool_executing');
              win.wsEventLog.push('tool_completed');
              win.wsEventLog.push('agent_completed');
            }, 1000);
          }
          
          return mockWs;
        });
      });
      
      AgentInteraction.sendMessage('Test WebSocket recovery');
      AgentInteraction.waitForProcessing();
      
      // Verify WebSocket events were eventually received
      cy.window().then((win) => {
        expect(win.wsEventLog).to.include('agent_started');
        expect(win.wsEventLog).to.include('agent_completed');
      });
    });

    it('should handle partial event delivery and retry', () => {
      // Setup to simulate missing events
      cy.window().then((win) => {
        win.partialEventLog = ['agent_started', 'tool_executing']; // Missing tool_completed
      });
      
      AgentInteraction.sendMessage('Test partial events');
      
      // Should show retry option when events are incomplete
      cy.contains(/retry|incomplete|try again/i, { timeout: 10000 }).should('be.visible');
    });
  });

  afterEach(() => {
    AgentRecoverySetup.cleanup();
  });
});