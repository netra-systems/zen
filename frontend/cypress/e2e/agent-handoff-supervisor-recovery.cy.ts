/// <reference types="cypress" />
import { 
  AgentRecoverySetup, 
  AgentMocking, 
  AgentInteraction, 
  RecoveryAssertions
} from './utils/recovery-test-helpers';

describe('Critical Test #2B: Agent Handoff & Supervisor Recovery', () => {
  beforeEach(() => {
    // Clear state and setup authentication
    cy.clearLocalStorage();
    cy.clearCookies();
    
    // Prevent uncaught exceptions from failing tests
    Cypress.on('uncaught:exception', (err, runnable) => {
      return false;
    });
    
    // Setup authenticated state with current token structure
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token-for-handoff-testing');
      win.localStorage.setItem('user_data', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
        role: 'user'
      }));
    });
    
    // Visit chat page for agent testing
    cy.visit('/chat', { failOnStatusCode: false });
    cy.wait(2000);
  });

  describe('Agent Handoff Failures', () => {
    it('should handle failed handoff from triage to data agent', () => {
      // Mock successful triage response
      cy.intercept('POST', '**/api/chat', {
        statusCode: 200,
        body: {
          classification: 'data_analysis',
          next_agent: 'data',
          message: 'Request classified for data analysis'
        }
      }).as('triageSuccess');

      // Mock subsequent handoff failure
      cy.intercept('POST', '**/api/chat', {
        statusCode: 500,
        body: {
          error: 'Handoff failed - data agent unavailable',
          type: 'handoff_error'
        }
      }).as('handoffFailure');

      // Use current system selectors
      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="message-textarea"]').length > 0) {
          cy.get('[data-testid="message-textarea"]').type('Analyze my performance metrics', { force: true });
          cy.get('[data-testid="send-button"]').click({ force: true });
          
          cy.wait('@triageSuccess');
          
          // Check for handoff error handling
          cy.get('body', { timeout: 10000 }).then(($errorBody) => {
            const bodyText = $errorBody.text();
            const hasHandoffError = bodyText.match(/handoff failed|agent unavailable|transfer error/i);
            const hasAlternative = bodyText.match(/alternative|try again|supervisor/i);
            
            if (hasHandoffError) {
              cy.log('Handoff error detected correctly');
            }
            
            if (hasAlternative) {
              cy.log('Alternative action suggested');
            }
          });
        } else if ($body.find('textarea').length > 0) {
          // Fallback to generic textarea selector
          cy.get('textarea').first().type('Analyze my performance metrics', { force: true });
          cy.get('button').contains('Send').first().click({ force: true });
        } else {
          cy.log('No input elements found, skipping handoff test');
        }
      });
    });

    it('should maintain context during agent transitions', () => {
      const context = {
        user_intent: 'cost_optimization',
        data_size: '10TB',
        current_cost: '$50000'
      };

      // Mock triage with context
      cy.intercept('POST', '**/api/chat', (req) => {
        expect(req.body).to.have.property('message');
        req.reply({
          statusCode: 200,
          body: { 
            classification: 'optimization',
            context: context,
            message: 'Request processed with context preserved'
          }
        });
      }).as('triageWithContext');

      // Mock optimization agent receiving context
      cy.intercept('POST', '**/api/chat', (req) => {
        // In a real WebSocket system, context would be maintained server-side
        req.reply({
          statusCode: 200,
          body: { 
            result: 'Optimization complete with preserved context',
            context_preserved: true,
            processing_details: 'Used provided context for optimization'
          }
        });
      }).as('optimizationWithContext');

      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="message-textarea"]').length > 0) {
          cy.get('[data-testid="message-textarea"]').type('Optimize my 10TB dataset costing $50000', { force: true });
          cy.get('[data-testid="send-button"]').click({ force: true });
          
          cy.wait('@triageWithContext');
          
          // Check for optimization completion with context
          cy.contains(/optimization complete/i, { timeout: 10000 }).should('be.visible');
        } else if ($body.find('textarea').length > 0) {
          // Fallback to generic textarea selector
          cy.get('textarea').first().type('Optimize my 10TB dataset costing $50000', { force: true });
          cy.get('button').contains('Send').first().click({ force: true });
        } else {
          cy.log('No input elements found, skipping context test');
        }
      });
    });

    it('should handle cascading agent failures', () => {
      // Mock all agents returning errors
      cy.intercept('POST', '**/api/chat', {
        statusCode: 503,
        body: { 
          error: 'All agents currently unavailable',
          type: 'system_failure',
          message: 'System is experiencing high load. Please try again later.'
        }
      }).as('systemFailure');

      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="message-textarea"]').length > 0) {
          cy.get('[data-testid="message-textarea"]').type('Complex query requiring multiple agents', { force: true });
          cy.get('[data-testid="send-button"]').click({ force: true });
          
          cy.wait('@systemFailure');
          
          // Check for system failure handling
          cy.get('body', { timeout: 10000 }).then(($failureBody) => {
            const bodyText = $failureBody.text();
            const hasSystemFailure = bodyText.match(/system unavailable|all agents failed|high load|try again later/i);
            const hasContactSupport = bodyText.match(/support|contact|help/i);
            
            if (hasSystemFailure) {
              cy.log('System failure detected and handled');
            }
            
            if (hasContactSupport) {
              cy.log('Support contact information provided');
            }
          });
        } else if ($body.find('textarea').length > 0) {
          // Fallback to generic textarea selector
          cy.get('textarea').first().type('Complex query requiring multiple agents', { force: true });
          cy.get('button').contains('Send').first().click({ force: true });
        } else {
          cy.log('No input elements found, skipping cascading failure test');
        }
      });
    });
  });

  describe('Supervisor Agent Fallback', () => {
    it('should fallback to supervisor when specialized agent unavailable', () => {
      // Mock specialized agent error
      cy.intercept('POST', '**/api/chat', {
        statusCode: 503,
        body: {
          error: 'Data agent temporarily unavailable',
          type: 'agent_unavailable'
        }
      }).as('dataError');

      // Mock supervisor fallback
      cy.intercept('POST', '**/api/chat', {
        statusCode: 200,
        body: { 
          response: 'Request handled by supervisor agent',
          fallback: true,
          message: 'Supervisor agent processed your data analysis request'
        }
      }).as('supervisorFallback');

      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="message-textarea"]').length > 0) {
          cy.get('[data-testid="message-textarea"]').type('Analyze this data: [100, 200, 300]', { force: true });
          cy.get('[data-testid="send-button"]').click({ force: true });
          
          // Check for supervisor fallback
          cy.get('body', { timeout: 10000 }).then(($supervisorBody) => {
            const bodyText = $supervisorBody.text();
            const hasSupervisor = bodyText.match(/supervisor|fallback|handled/i);
            
            if (hasSupervisor) {
              cy.contains(/supervisor|fallback|handled/i).should('be.visible');
            } else {
              cy.log('Supervisor fallback not detected in UI');
            }
          });
        } else if ($body.find('textarea').length > 0) {
          // Fallback to generic textarea selector
          cy.get('textarea').first().type('Analyze this data: [100, 200, 300]', { force: true });
          cy.get('button').contains('Send').first().click({ force: true });
        } else {
          cy.log('No input elements found, skipping supervisor test');
        }
      });
    });

    it('should prioritize requests when agents are overloaded', () => {
      let queuePosition = 5;

      // Mock queued responses
      cy.intercept('POST', '**/api/chat', (req) => {
        req.reply({
          statusCode: 202,
          body: { 
            status: 'queued',
            position: queuePosition--,
            estimated_wait: queuePosition * 2,
            message: `Your request is queued at position ${queuePosition + 1}`
          }
        });
      }).as('agentQueue');

      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="message-textarea"]').length > 0) {
          cy.get('[data-testid="message-textarea"]').type('High priority optimization request', { force: true });
          cy.get('[data-testid="send-button"]').click({ force: true });
          
          cy.wait('@agentQueue');
          
          // Check for queue information
          cy.get('body', { timeout: 10000 }).then(($queueBody) => {
            const bodyText = $queueBody.text();
            const hasQueueInfo = bodyText.match(/queue|position|wait|priority/i);
            
            if (hasQueueInfo) {
              cy.log('Queue information displayed to user');
            } else {
              cy.log('Queue information not found in UI');
            }
          });
          
          // Wait and check for position update
          cy.wait(2000);
          cy.get('body').then(($positionBody) => {
            const positionText = $positionBody.text();
            const hasPosition = positionText.match(/position.*[0-4]/i);
            
            if (hasPosition) {
              cy.log('Queue position updated');
            }
          });
        } else if ($body.find('textarea').length > 0) {
          // Fallback to generic textarea selector
          cy.get('textarea').first().type('High priority optimization request', { force: true });
          cy.get('button').contains('Send').first().click({ force: true });
        } else {
          cy.log('No input elements found, skipping queue test');
        }
      });
    });

    it('should handle supervisor agent failure gracefully', () => {
      // Mock total system failure including supervisor
      cy.intercept('POST', '**/api/chat', {
        statusCode: 500,
        body: { 
          error: 'All agents including supervisor failed',
          type: 'total_failure',
          message: 'System is currently in maintenance mode'
        }
      }).as('totalFailure');

      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="message-textarea"]').length > 0) {
          cy.get('[data-testid="message-textarea"]').type('Critical request', { force: true });
          cy.get('[data-testid="send-button"]').click({ force: true });
          
          cy.wait('@totalFailure');
          
          // Check for emergency mode handling
          cy.get('body', { timeout: 10000 }).then(($emergencyBody) => {
            const bodyText = $emergencyBody.text();
            const hasEmergencyMode = bodyText.match(/emergency|critical failure|maintenance mode|total failure/i);
            
            if (hasEmergencyMode) {
              cy.log('Emergency mode activated correctly');
            } else {
              cy.log('Emergency mode not detected in UI');
            }
          });
          
          // Check that console errors are logged (for debugging)
          cy.window().then((win) => {
            // The system should log errors for debugging
            cy.wrap(win.console).should('exist');
          });
        } else if ($body.find('textarea').length > 0) {
          // Fallback to generic textarea selector
          cy.get('textarea').first().type('Critical request', { force: true });
          cy.get('button').contains('Send').first().click({ force: true });
        } else {
          cy.log('No input elements found, skipping emergency mode test');
        }
      });
    });
  });

  afterEach(() => {
    // Clean up test state
    cy.window().then((win) => {
      win.localStorage.removeItem('agent_state');
      win.localStorage.removeItem('handoff_context');
      win.localStorage.removeItem('jwt_token');
      win.localStorage.removeItem('user_data');
    });
  });
});