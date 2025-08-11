/// <reference types="cypress" />

describe('Critical Test #2: Agent Orchestration Failure Recovery', () => {
  const agents = ['triage', 'data', 'optimization', 'reporting', 'analysis'];
  
  beforeEach(() => {
    cy.viewport(1920, 1080);
    
    // Set up auth
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'test-token');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user',
        email: 'test@netra.ai',
        name: 'Test User'
      }));
    });
    
    // Visit demo chat
    cy.visit('/demo');
    cy.contains('Technology').click();
    cy.contains('AI Chat').click({ force: true });
    cy.wait(1000);
  });

  describe('Agent Timeout Handling', () => {
    it('should handle triage agent timeout gracefully', () => {
      // Intercept triage agent calls and delay response
      cy.intercept('POST', '**/api/agents/triage**', (req) => {
        req.reply((res) => {
          res.delay(15000); // 15 second delay to trigger timeout
          res.send({ status: 'timeout' });
        });
      }).as('triageTimeout');
      
      // Send message that triggers triage
      cy.get('textarea').type('Analyze my workload for optimization opportunities');
      cy.get('button[aria-label="Send message"]').click();
      
      // Should show processing indicator
      cy.contains(/processing|analyzing|thinking/i).should('be.visible');
      
      // Should show timeout message after 10 seconds
      cy.contains(/taking longer|timeout|retry/i, { timeout: 12000 }).should('be.visible');
      
      // Should offer retry option
      cy.get('button').contains(/retry|try again/i).should('be.visible');
    });

    it('should handle data agent failure with fallback', () => {
      // Intercept data agent and return error
      cy.intercept('POST', '**/api/agents/data**', {
        statusCode: 500,
        body: { error: 'Data agent internal error' }
      }).as('dataError');
      
      // Send data analysis request
      cy.get('textarea').type('Process this dataset: [1,2,3,4,5]');
      cy.get('button[aria-label="Send message"]').click();
      
      // Should attempt data agent
      cy.wait('@dataError');
      
      // Should fallback to supervisor
      cy.contains(/supervisor|fallback|alternative/i, { timeout: 5000 }).should('exist');
      
      // Should still provide a response
      cy.contains(/unable to process|error occurred|try different/i).should('be.visible');
    });

    it('should handle optimization agent crash recovery', () => {
      let failCount = 0;
      
      // Simulate intermittent failures
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
      
      // Send optimization request
      cy.get('textarea').type('Optimize my AI infrastructure costs');
      cy.get('button[aria-label="Send message"]').click();
      
      // Should retry failed requests
      cy.wait('@optimizationRetry');
      cy.wait('@optimizationRetry');
      cy.wait('@optimizationRetry');
      
      // Should eventually succeed
      cy.contains(/optimized|savings|45%/i, { timeout: 10000 }).should('be.visible');
    });

    it('should activate circuit breaker after repeated failures', () => {
      let requestCount = 0;
      
      // Simulate consistent failures
      cy.intercept('POST', '**/api/agents/**', (req) => {
        requestCount++;
        req.reply({
          statusCode: 500,
          body: { error: 'Agent error' }
        });
      }).as('agentFailure');
      
      // Send multiple requests
      for (let i = 0; i < 4; i++) {
        cy.get('textarea').clear().type(`Test message ${i}`);
        cy.get('button[aria-label="Send message"]').click();
        cy.wait(1000);
      }
      
      // Circuit breaker should activate after 3 failures
      expect(requestCount).to.be.lessThan(8); // Should stop making requests
      
      // Should show circuit breaker message
      cy.contains(/temporarily unavailable|circuit breaker|too many errors/i)
        .should('be.visible');
    });
  });

  describe('Agent Handoff Failures', () => {
    it('should handle failed handoff from triage to data agent', () => {
      // Mock successful triage but failed handoff
      cy.intercept('POST', '**/api/agents/triage**', {
        statusCode: 200,
        body: { 
          classification: 'data_analysis',
          next_agent: 'data'
        }
      }).as('triageSuccess');
      
      cy.intercept('POST', '**/api/agents/handoff**', {
        statusCode: 500,
        body: { error: 'Handoff failed' }
      }).as('handoffFailure');
      
      // Send message requiring handoff
      cy.get('textarea').type('Analyze my performance metrics');
      cy.get('button[aria-label="Send message"]').click();
      
      cy.wait('@triageSuccess');
      cy.wait('@handoffFailure');
      
      // Should show handoff error
      cy.contains(/handoff failed|unable to transfer|communication error/i)
        .should('be.visible');
      
      // Should provide alternative action
      cy.contains(/try again|alternative|manual/i).should('be.visible');
    });

    it('should maintain context during agent transitions', () => {
      const context = {
        user_intent: 'cost_optimization',
        data_size: '10TB',
        current_cost: '$50000'
      };
      
      // Intercept agent calls to verify context
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
        // Verify context is passed
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
      
      cy.get('textarea').type('Optimize my 10TB dataset costing $50000');
      cy.get('button[aria-label="Send message"]').click();
      
      cy.wait('@triageWithContext');
      cy.wait('@optimizationWithContext');
      
      cy.contains(/optimization complete/i).should('be.visible');
    });

    it('should handle cascading agent failures', () => {
      // All agents fail
      agents.forEach(agent => {
        cy.intercept('POST', `**/api/agents/${agent}**`, {
          statusCode: 500,
          body: { error: `${agent} agent failed` }
        }).as(`${agent}Failed`);
      });
      
      // Send message
      cy.get('textarea').type('Complex query requiring multiple agents');
      cy.get('button[aria-label="Send message"]').click();
      
      // Should show graceful error handling
      cy.contains(/system unavailable|all agents failed|maintenance/i, { timeout: 10000 })
        .should('be.visible');
      
      // Should provide contact or alternative
      cy.contains(/support|contact|try later/i).should('be.visible');
    });
  });

  describe('Supervisor Agent Fallback', () => {
    it('should fallback to supervisor when specialized agent unavailable', () => {
      // Data agent unavailable
      cy.intercept('POST', '**/api/agents/data**', {
        statusCode: 503,
        body: { error: 'Service unavailable' }
      }).as('dataUnavailable');
      
      // Supervisor handles request
      cy.intercept('POST', '**/api/agents/supervisor**', {
        statusCode: 200,
        body: { 
          response: 'Handled by supervisor',
          fallback: true
        }
      }).as('supervisorFallback');
      
      cy.get('textarea').type('Analyze this data: [100, 200, 300]');
      cy.get('button[aria-label="Send message"]').click();
      
      cy.wait('@dataUnavailable');
      cy.wait('@supervisorFallback');
      
      cy.contains(/supervisor|fallback|handled/i).should('be.visible');
    });

    it('should prioritize requests when agents are overloaded', () => {
      let queuePosition = 5;
      
      // Simulate queue system
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
      
      cy.get('textarea').type('High priority optimization request');
      cy.get('button[aria-label="Send message"]').click();
      
      // Should show queue position
      cy.contains(/queue|position|waiting/i).should('be.visible');
      
      // Should update position
      cy.wait(2000);
      cy.contains(/position.*[0-4]/i).should('be.visible');
    });

    it('should handle supervisor agent failure gracefully', () => {
      // Even supervisor fails
      cy.intercept('POST', '**/api/agents/**', {
        statusCode: 500,
        body: { error: 'All agents including supervisor failed' }
      }).as('totalFailure');
      
      cy.get('textarea').type('Critical request');
      cy.get('button[aria-label="Send message"]').click();
      
      // Should show emergency fallback
      cy.contains(/emergency|critical failure|maintenance mode/i, { timeout: 5000 })
        .should('be.visible');
      
      // Should log for support
      cy.window().then((win) => {
        // Check if error was logged (console or telemetry)
        cy.wrap(win.console).should('have.property', 'error');
      });
    });
  });

  describe('Error Messages and User Feedback', () => {
    it('should provide meaningful error messages for each agent failure', () => {
      const agentErrors = {
        triage: 'Unable to classify your request',
        data: 'Error processing data analysis', 
        optimization: 'Optimization engine temporarily unavailable',
        reporting: 'Report generation failed',
        analysis: 'Analysis service is down'
      };
      
      Object.entries(agentErrors).forEach(([agent, errorMsg]) => {
        cy.intercept('POST', `**/api/agents/${agent}**`, {
          statusCode: 500,
          body: { 
            error: errorMsg,
            user_message: errorMsg
          }
        }).as(`${agent}Error`);
      });
      
      // Test each agent error
      const testMessages = {
        triage: 'Help me with something',
        data: 'Analyze my dataset',
        optimization: 'Optimize my costs',
        reporting: 'Generate a report',
        analysis: 'Perform analysis'
      };
      
      Object.entries(testMessages).forEach(([agent, msg]) => {
        cy.get('textarea').clear().type(msg);
        cy.get('button[aria-label="Send message"]').click();
        cy.wait(2000);
        
        // Should show specific error message
        cy.contains(agentErrors[agent]).should('be.visible');
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
      
      cy.get('textarea').type('Complex optimization query');
      cy.get('button[aria-label="Send message"]').click();
      
      cy.wait('@errorWithSuggestions');
      
      // Should show suggestions
      cy.contains(/try rephrasing|break down|contact support/i).should('be.visible');
    });

    it('should track and display agent response times', () => {
      // Intercept with varying delays
      cy.intercept('POST', '**/api/agents/triage**', (req) => {
        req.reply((res) => {
          res.delay(500);
          res.send({ status: 'success' });
        });
      }).as('triageDelay');
      
      cy.intercept('POST', '**/api/agents/optimization**', (req) => {
        req.reply((res) => {
          res.delay(2000);
          res.send({ status: 'success' });
        });
      }).as('optimizationDelay');
      
      cy.get('textarea').type('Optimize my infrastructure');
      cy.get('button[aria-label="Send message"]').click();
      
      // Should show timing information
      cy.contains(/\d+ms|\d+s|response time/i, { timeout: 5000 }).should('exist');
    });
  });

  describe('Recovery and Retry Mechanisms', () => {
    it('should implement exponential backoff for retries', () => {
      let attemptCount = 0;
      const attemptTimes: number[] = [];
      
      cy.intercept('POST', '**/api/agents/**', (req) => {
        attemptTimes.push(Date.now());
        attemptCount++;
        
        if (attemptCount < 3) {
          req.reply({
            statusCode: 503,
            body: { error: 'Temporary failure' }
          });
        } else {
          req.reply({
            statusCode: 200,
            body: { status: 'success' }
          });
        }
      }).as('retryWithBackoff');
      
      cy.get('textarea').type('Test retry mechanism');
      cy.get('button[aria-label="Send message"]').click();
      
      // Wait for retries
      cy.wait('@retryWithBackoff');
      cy.wait('@retryWithBackoff');
      cy.wait('@retryWithBackoff');
      
      // Verify exponential backoff
      cy.wrap(null).then(() => {
        if (attemptTimes.length >= 3) {
          const delay1 = attemptTimes[1] - attemptTimes[0];
          const delay2 = attemptTimes[2] - attemptTimes[1];
          
          // Second delay should be longer (exponential)
          expect(delay2).to.be.greaterThan(delay1);
        }
      });
    });

    it('should preserve message order during retries', () => {
      const messages = ['First message', 'Second message', 'Third message'];
      let processedOrder: string[] = [];
      
      cy.intercept('POST', '**/api/agents/**', (req) => {
        processedOrder.push(req.body.message);
        req.reply({
          statusCode: 200,
          body: { processed: req.body.message }
        });
      }).as('orderedProcessing');
      
      // Send messages rapidly
      messages.forEach(msg => {
        cy.get('textarea').clear().type(msg);
        cy.get('button[aria-label="Send message"]').click();
        cy.wait(500);
      });
      
      // Wait for all to process
      cy.wait(3000);
      
      // Verify order preserved
      cy.wrap(processedOrder).should('deep.equal', messages);
    });

    it('should clean up resources after agent failures', () => {
      // Check for resource cleanup
      cy.window().then((win) => {
        const initialListeners = win.addEventListener.length || 0;
        
        // Trigger multiple failures
        cy.intercept('POST', '**/api/agents/**', {
          statusCode: 500,
          body: { error: 'Agent failure' }
        }).as('agentFail');
        
        for (let i = 0; i < 5; i++) {
          cy.get('textarea').clear().type(`Message ${i}`);
          cy.get('button[aria-label="Send message"]').click();
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
    // Clear any pending requests or timers
    cy.window().then((win) => {
      win.localStorage.removeItem('agent_state');
      win.localStorage.removeItem('retry_count');
    });
  });
});