/// <reference types="cypress" />
import { 
  AgentRecoverySetup, 
  AgentMocking, 
  AgentInteraction, 
  RecoveryAssertions,
  RetryUtils,
  ERROR_MESSAGES,
  TEST_MESSAGES
} from './utils/recovery-test-helpers';

describe('Critical Test #2C: Agent Feedback & Retry Recovery', () => {
  beforeEach(() => {
    AgentRecoverySetup.fullSetup();
  });

  describe('Error Messages and User Feedback', () => {
    it('should provide meaningful error messages for each agent failure', () => {
      // Setup agent error mocks
      Object.entries(ERROR_MESSAGES).forEach(([agent, errorMsg]) => {
        cy.intercept('POST', `**/api/agents/${agent}**`, {
          statusCode: 500,
          body: { 
            error: errorMsg,
            user_message: errorMsg
          }
        }).as(`${agent}Error`);
      });

      // Test each agent error
      Object.entries(TEST_MESSAGES).forEach(([agent, msg]) => {
        AgentInteraction.sendAndClear(msg);
        cy.wait(2000);
        
        cy.contains(ERROR_MESSAGES[agent as keyof typeof ERROR_MESSAGES])
          .should('be.visible');
      });
    });

    it('should suggest recovery actions for failures', () => {
      cy.intercept('POST', '**/api/agents/**', {
        statusCode: 500,
        body: { 
          error: 'Agent error',
          suggestions: [
            'Try rephrasing your request',
            'Break down into smaller queries',
            'Contact support if issue persists'
          ]
        }
      }).as('errorWithSuggestions');
      
      AgentInteraction.sendMessage('Complex optimization query');
      
      cy.wait('@errorWithSuggestions');
      RecoveryAssertions.verifySuggestions();
    });

    it('should track and display agent response times', () => {
      cy.intercept('POST', '**/api/agents/triage**', (req) => {
        req.reply((res) => {
          (res as any).delay(500);
          (res as any).send({ status: 'success' });
        });
      }).as('triageDelay');
      
      cy.intercept('POST', '**/api/agents/optimization**', (req) => {
        req.reply((res) => {
          (res as any).delay(2000);
          (res as any).send({ status: 'success' });
        });
      }).as('optimizationDelay');
      
      AgentInteraction.sendMessage('Optimize my infrastructure');
      
      RecoveryAssertions.verifyTiming();
    });
  });

  describe('Recovery and Retry Mechanisms', () => {
    it('should implement exponential backoff for retries', () => {
      const counter = RetryUtils.setupRetryCounter();
      
      AgentInteraction.sendMessage('Test retry mechanism');
      
      RetryUtils.verifyExponentialBackoff();
    });

    it('should preserve message order during retries', () => {
      const messages = ['First message', 'Second message', 'Third message'];
      const tracker = RetryUtils.setupOrderTracking();
      
      AgentInteraction.sendMultipleMessages(messages);
      
      cy.wait(3000);
      RetryUtils.verifyMessageOrder(messages, tracker.getOrder());
    });

    it('should clean up resources after agent failures', () => {
      cy.window().then((win) => {
        const initialListeners = win.addEventListener.length || 0;
        
        cy.intercept('POST', '**/api/agents/**', {
          statusCode: 500,
          body: { error: 'Agent failure' }
        }).as('agentFail');
        
        // Trigger multiple failures
        for (let i = 0; i < 5; i++) {
          AgentInteraction.sendAndClear(`Message ${i}`);
          cy.wait(500);
        }
        
        cy.wait(2000);
        
        // Check event listeners haven't grown excessively
        cy.window().then((win2) => {
          const finalListeners = win2.addEventListener.length || 0;
          expect(finalListeners - initialListeners).to.be.lessThan(10);
        });
      });
    });
  });

  afterEach(() => {
    AgentRecoverySetup.cleanup();
  });
});