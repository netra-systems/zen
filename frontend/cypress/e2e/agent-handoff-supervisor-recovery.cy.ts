/// <reference types="cypress" />
import { 
  AgentRecoverySetup, 
  AgentMocking, 
  AgentInteraction, 
  RecoveryAssertions
} from './utils/recovery-test-helpers';

describe('Critical Test #2B: Agent Handoff & Supervisor Recovery', () => {
  beforeEach(() => {
    AgentRecoverySetup.fullSetup();
  });

  describe('Agent Handoff Failures', () => {
    it('should handle failed handoff from triage to data agent', () => {
      AgentMocking.mockSuccess('triage', {
        classification: 'data_analysis',
        next_agent: 'data'
      });
      
      AgentMocking.mockHandoffFailure();
      
      AgentInteraction.sendMessage('Analyze my performance metrics');
      
      cy.wait('@triageSuccess');
      cy.wait('@handoffFailure');
      
      RecoveryAssertions.verifyHandoffError();
      RecoveryAssertions.verifyAlternativeAction();
    });

    it('should maintain context during agent transitions', () => {
      const context = {
        user_intent: 'cost_optimization',
        data_size: '10TB',
        current_cost: '$50000'
      };
      
      cy.intercept('POST', '**/api/agents/triage**', (req) => {
        req.reply({
          statusCode: 200,
          body: { 
            classification: 'optimization',
            context: context
          }
        });
      }).as('triageWithContext');
      
      cy.intercept('POST', '**/api/agents/optimization**', (req) => {
        expect(req.body).to.have.property('context');
        expect(req.body.context).to.deep.include(context);
        
        req.reply({
          statusCode: 200,
          body: { 
            result: 'Optimization complete',
            context_preserved: true
          }
        });
      }).as('optimizationWithContext');
      
      AgentInteraction.sendMessage('Optimize my 10TB dataset costing $50000');
      
      cy.wait('@triageWithContext');
      cy.wait('@optimizationWithContext');
      
      cy.contains(/optimization complete/i).should('be.visible');
    });

    it('should handle cascading agent failures', () => {
      AgentMocking.mockAllAgentsError();
      
      AgentInteraction.sendMessage('Complex query requiring multiple agents');
      
      RecoveryAssertions.verifySystemFailure();
      RecoveryAssertions.verifyContactSupport();
    });
  });

  describe('Supervisor Agent Fallback', () => {
    it('should fallback to supervisor when specialized agent unavailable', () => {
      AgentMocking.mockError('data', 503);
      AgentMocking.mockSupervisorFallback();
      
      AgentInteraction.sendMessage('Analyze this data: [100, 200, 300]');
      
      cy.wait('@dataError');
      cy.wait('@supervisorFallback');
      
      cy.contains(/supervisor|fallback|handled/i).should('be.visible');
    });

    it('should prioritize requests when agents are overloaded', () => {
      let queuePosition = 5;
      
      cy.intercept('POST', '**/api/agents/**', (req) => {
        req.reply({
          statusCode: 202,
          body: { 
            status: 'queued',
            position: queuePosition--,
            estimated_wait: queuePosition * 2
          }
        });
      }).as('agentQueue');
      
      AgentInteraction.sendMessage('High priority optimization request');
      
      RecoveryAssertions.verifyQueue();
      
      cy.wait(2000);
      cy.contains(/position.*[0-4]/i).should('be.visible');
    });

    it('should handle supervisor agent failure gracefully', () => {
      cy.intercept('POST', '**/api/agents/**', {
        statusCode: 500,
        body: { error: 'All agents including supervisor failed' }
      }).as('totalFailure');
      
      AgentInteraction.sendMessage('Critical request');
      
      RecoveryAssertions.verifyEmergencyMode();
      
      cy.window().then((win) => {
        cy.wrap(win.console).should('have.property', 'error');
      });
    });
  });

  afterEach(() => {
    AgentRecoverySetup.cleanup();
  });
});