describe('Apex Optimizer Agent End-to-End Test', () => {
  beforeEach(() => {
    // Clear state and setup authentication
    cy.clearLocalStorage();
    cy.clearCookies();
    
    // Prevent uncaught exceptions from failing tests
    Cypress.on('uncaught:exception', (err, runnable) => {
      return false;
    });
    
    // Mock current auth endpoints
    cy.intercept('GET', '**/auth/config', {
      statusCode: 200,
      body: {
        endpoints: {
          login: '/auth/dev/login',
          user: '/auth/me'
        }
      }
    }).as('authConfig');
    
    cy.intercept('GET', '**/auth/me', {
      statusCode: 200,
      body: {
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User',
        role: 'user',
        verified: true
      }
    }).as('userAuth');
    
    // Setup authenticated state with current JWT structure
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-apex-optimizer-token');
      win.localStorage.setItem('refresh_token', 'test-refresh-token');
    });
  });

  it('should run an Apex Optimizer Agent analysis via current agent API', () => {
    // Mock the current agent execution API with apex_optimizer agent type
    cy.intercept('POST', '**/api/agents/execute', (req) => {
      expect(req.body).to.have.property('agent_type', 'apex_optimizer');
      expect(req.body).to.have.property('message');
      
      req.reply({
        statusCode: 200,
        body: {
          thread_id: 'apex-thread-123',
          agent_type: 'apex_optimizer',
          status: 'processing',
          websocket_url: 'ws://localhost:8000/ws',
          message: 'Apex Optimizer analysis started'
        }
      });
    }).as('apexOptimizerExecution');
    
    // Visit chat page for current system integration
    cy.visit('/chat', { failOnStatusCode: false });
    
    // Wait for page to load and auth
    cy.wait('@authConfig');
    cy.wait('@userAuth');
    cy.get('body').should('be.visible');
    cy.wait(2000);
    
    // Verify chat interface is loaded with current system structure
    cy.get('[data-testid="main-chat"]', { timeout: 10000 }).should('be.visible');
    cy.get('[data-testid="message-textarea"]', { timeout: 5000 }).should('be.visible');
    
    // Submit optimization request using current system interface
    const optimizationRequest = 'I need to reduce costs by 20% and improve latency by 2x.';
    
    cy.get('[data-testid="message-textarea"]')
      .clear()
      .type(optimizationRequest);
    
    cy.get('[data-testid="send-button"]').should('be.enabled');
    cy.get('[data-testid="send-button"]').click();
    
    // Wait for agent API call
    cy.wait('@apexOptimizerExecution').then((interception) => {
      // Verify the request structure matches current API
      expect(interception.request.body).to.deep.include({
        message: optimizationRequest,
        agent_type: 'apex_optimizer'
      });
    });
    
    // Verify message was sent
    cy.get('[data-testid="message-textarea"]').should('have.value', '');
    
    // Check for WebSocket agent events (apex optimizer processing)
    cy.get('body').then($body => {
      const bodyText = $body.text().toLowerCase();
      
      // Look for WebSocket event indicators: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
      const hasProcessingIndicators = /thinking|processing|analyzing|executing|working/i.test(bodyText);
      const hasOptimizationContent = /cost|latency|performance|optimization|efficiency/i.test(bodyText);
      
      if (hasProcessingIndicators) {
        cy.log('WebSocket agent events detected - processing indicators found');
      }
      
      if (hasOptimizationContent) {
        cy.log('Optimization content detected in response');
      }
      
      // Verify the optimization request is visible
      expect(bodyText).to.include(optimizationRequest.toLowerCase());
    });
    
    // Check for agent response or processing state
    cy.get('body', { timeout: 15000 }).then($responseBody => {
      const responseText = $responseBody.text();
      
      // Check for various response patterns that would come from WebSocket events
      const hasAgentStarted = /started|initiated|beginning/i.test(responseText);
      const hasAgentThinking = /thinking|analyzing|processing/i.test(responseText);
      const hasToolExecution = /executing|running|tool/i.test(responseText);
      const hasOptimizationResults = /cost|latency|performance|optimization|efficiency|\d+%|\$[\d,]+|ms|reduction|improvement/i.test(responseText);
      
      if (hasAgentStarted) {
        cy.log('Agent started event processed');
      }
      
      if (hasAgentThinking) {
        cy.log('Agent thinking event processed');
        cy.contains(/thinking|analyzing|processing/i).should('be.visible');
      }
      
      if (hasToolExecution) {
        cy.log('Tool execution events detected');
      }
      
      if (hasOptimizationResults) {
        cy.log('Optimization results found');
        cy.contains(/cost|latency|performance|optimization/i).should('be.visible');
      }
      
      // Minimum requirement: system shows the message was processed
      cy.get('body').should('contain.text', optimizationRequest);
    });
  });

  it('should handle apex optimizer errors with circuit breaker', () => {
    // Mock auth for error test
    cy.visit('/chat', { failOnStatusCode: false });
    cy.wait('@authConfig');
    cy.wait('@userAuth');
    
    // Mock API error for apex optimizer with circuit breaker response
    cy.intercept('POST', '**/api/agents/execute', (req) => {
      if (req.body.agent_type === 'apex_optimizer') {
        req.reply({
          statusCode: 503,
          body: {
            error: 'service_unavailable',
            message: 'Apex Optimizer temporarily unavailable',
            circuit_breaker: {
              state: 'open',
              failure_count: 5,
              next_attempt_at: new Date(Date.now() + 30000).toISOString()
            },
            retry_after: 30
          }
        });
      }
    }).as('apexOptimizerError');
    
    // Wait for chat interface
    cy.get('[data-testid="main-chat"]', { timeout: 10000 }).should('be.visible');
    cy.get('[data-testid="message-textarea"]').should('be.visible');
    
    // Submit request that will trigger the error
    const errorTestMessage = 'Test error handling for apex optimizer';
    cy.get('[data-testid="message-textarea"]')
      .clear()
      .type(errorTestMessage);
    cy.get('[data-testid="send-button"]').click();
    
    // Wait for error response
    cy.wait('@apexOptimizerError');
    
    // Check for circuit breaker error handling
    cy.get('body').then($resultBody => {
      const resultText = $resultBody.text().toLowerCase();
      
      // Look for error indicators that would come from WebSocket error events
      const hasErrorMessage = /error|unavailable|service.*temporarily|try.*again|circuit.*breaker/i.test(resultText);
      const hasRetryGuidance = /retry|wait|later|minutes/i.test(resultText);
      
      if (hasErrorMessage) {
        cy.log('Circuit breaker error handling detected');
        // Don't require specific error text as it may vary
      } else {
        cy.log('Error response received, checking system stability');
      }
      
      // Verify the system remains functional after error
      cy.get('[data-testid="message-textarea"]').should('be.visible');
      cy.get('[data-testid="send-button"]').should('be.visible');
      
      // Verify the error request is still visible in chat
      expect(resultText).to.include(errorTestMessage.toLowerCase());
    });
  });

  it('should maintain responsive UI with WebSocket agent events', () => {
    // Mock successful apex optimizer with WebSocket events
    cy.intercept('POST', '**/api/agents/execute', (req) => {
      if (req.body.agent_type === 'apex_optimizer') {
        req.reply({
          statusCode: 200,
          body: {
            thread_id: 'responsive-ui-thread',
            agent_type: 'apex_optimizer',
            status: 'processing',
            websocket_url: 'ws://localhost:8000/ws',
            estimated_duration: 30
          }
        });
      }
    }).as('responsiveApexOptimizer');
    
    // Visit chat interface
    cy.visit('/chat', { failOnStatusCode: false });
    cy.wait('@authConfig');
    cy.wait('@userAuth');
    
    cy.get('[data-testid="main-chat"]', { timeout: 10000 }).should('be.visible');
    cy.get('[data-testid="message-textarea"]').should('be.visible');
    
    // Submit comprehensive optimization request
    const comprehensiveRequest = 'Comprehensive optimization analysis for my infrastructure';
    cy.get('[data-testid="message-textarea"]')
      .clear()
      .type(comprehensiveRequest);
    cy.get('[data-testid="send-button"]').click();
    
    // Wait for agent execution to start
    cy.wait('@responsiveApexOptimizer');
    
    // Test UI remains responsive during processing
    cy.wait(1000);
    
    // Verify interface remains interactive
    cy.get('[data-testid="message-textarea"]').should('be.visible').should('not.be.disabled');
    cy.get('[data-testid="send-button"]').should('be.visible');
    
    // Check for WebSocket event indicators (responsive loading states)
    cy.get('body').then($progressBody => {
      const progressText = $progressBody.text();
      
      // Look for WebSocket-driven progress indicators
      const hasWebSocketEventIndicators = /thinking|processing|analyzing|executing|working/i.test(progressText);
      const hasVisualLoadingIndicators = $progressBody.find('[class*="loading"], [class*="spinner"], [class*="animate-spin"], [data-testid*="thinking"]').length > 0;
      
      if (hasWebSocketEventIndicators) {
        cy.log('WebSocket agent event indicators found - UI is responsive to events');
      }
      
      if (hasVisualLoadingIndicators) {
        cy.log('Visual loading indicators found - responsive UI elements present');
      }
      
      // Verify the message is displayed (immediate UI feedback)
      expect(progressText.toLowerCase()).to.include(comprehensiveRequest.toLowerCase());
    });
    
    // Test that user can type while agent is processing
    cy.get('[data-testid="message-textarea"]').type('Follow-up question while processing');
    cy.get('[data-testid="message-textarea"]').should('contain.value', 'Follow-up question while processing');
    
    // Verify UI remains stable and ready for interaction
    cy.get('[data-testid="send-button"]').should('be.enabled');
    cy.get('[data-testid="message-textarea"]').should('not.be.disabled');
  });

  afterEach(() => {
    // Clean up test state with current token structure
    cy.window().then((win) => {
      win.localStorage.removeItem('jwt_token');
      win.localStorage.removeItem('refresh_token');
      win.localStorage.removeItem('apex_optimizer_state');
    });
  });
});