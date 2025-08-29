/// <reference types="cypress" />
// Import helper functions - fallback to inline implementations if utils not available
try {
  const {
    AgentRecoverySetup, 
    AgentMocking, 
    AgentInteraction, 
    RecoveryAssertions,
    CircuitBreakerUtils
  } = require('./utils/recovery-test-helpers');
} catch (e) {
  // Define inline helper functions
  const AgentRecoverySetup = {
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
  
  const AgentMocking = {
    mockTimeout: (agentType) => {
      cy.intercept('POST', `**/api/agents/${agentType}**`, {
        statusCode: 408,
        body: { error: 'Request timeout' },
        delay: 5000
      });
    },
    mockError: (agentType) => {
      cy.intercept('POST', `**/api/agents/${agentType}**`, {
        statusCode: 500,
        body: { error: 'Internal server error' }
      });
    }
  };
  
  const AgentInteraction = {
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
  
  const RecoveryAssertions = {
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
  
  const CircuitBreakerUtils = {
    setupFailureTracking: () => {
      return { failures: 0 };
    },
    triggerMultipleFailures: (count) => {
      for (let i = 0; i < count; i++) {
        cy.intercept('POST', '**/api/**', {
          statusCode: 503,
          body: { error: 'Service unavailable' }
        });
      }
    },
    verifyCircuitBreakerActivated: () => {
      cy.contains(/circuit.*breaker.*open|too.*many.*failures/i).should('be.visible');
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
      
      cy.intercept('POST', 'http://localhost:8001/api/agents/optimization**', (req) => {
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
              optimization: 'Successfully optimized',
              savings: '45%'
            }
          });
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
      
      CircuitBreakerUtils.verifyCircuitBreakerActivated();
      RecoveryAssertions.verifyCircuitBreaker();
    });
  });

  afterEach(() => {
    AgentRecoverySetup.cleanup();
  });
});