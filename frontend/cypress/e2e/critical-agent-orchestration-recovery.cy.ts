/// <reference types="cypress" />
import { 
  AgentRecoverySetup, 
  AgentMocking, 
  AgentInteraction, 
  RecoveryAssertions,
  CircuitBreakerUtils
} from './utils/recovery-test-helpers';

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
      
      cy.intercept('POST', '**/api/agents/optimization**', (req) => {
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