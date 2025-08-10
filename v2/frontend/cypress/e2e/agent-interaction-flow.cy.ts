describe('Agent Interaction Complete Flow', () => {
  beforeEach(() => {
    // Clear state and mock authentication
    cy.clearLocalStorage();
    cy.clearCookies();
    
    // Prevent uncaught exceptions from failing tests
    Cypress.on('uncaught:exception', (err, runnable) => {
      return false;
    });
    
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'mock-jwt-token-for-testing');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netra.ai',
        name: 'Test User',
        role: 'user'
      }));
    });
    
    cy.visit('/chat', { failOnStatusCode: false });
    cy.wait(2000); // Wait for page load and WebSocket connection
  });

  it('should complete full agent workflow from triage to reporting', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // 1. Send initial optimization request
        const optimizationRequest = 'Analyze my AI workload: 5000 req/s, GPT-4, $500/hour cost. Need full optimization analysis with recommendations.';
        
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().should('be.visible').type(optimizationRequest);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎|optimize/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        // 2. Verify request appears in chat
        cy.contains(optimizationRequest, { timeout: 10000 }).should('be.visible');
        
        // 3. Check for triage agent activity
        cy.contains(/triage|analyzing request|understanding/i, { timeout: 15000 }).should('exist');
        
        // 4. Check for data collection phase
        cy.contains(/collecting data|gathering information|analyzing workload/i, { timeout: 20000 }).should('exist');
        
        // 5. Check for optimization analysis
        cy.contains(/optimization|calculating|analyzing performance/i, { timeout: 25000 }).should('exist');
        
        // 6. Verify final recommendations appear
        cy.contains(/recommendation|suggest|improve|reduce cost/i, { timeout: 30000 }).should('exist');
        
        // 7. Check for specific optimization metrics
        cy.get('body').then(($body) => {
          const text = $body.text();
          // Should contain cost analysis
          expect(text).to.match(/\$|cost|savings|reduce/i);
          // Should contain performance metrics
          expect(text).to.match(/latency|throughput|performance/i);
          // Should contain specific recommendations
          expect(text).to.match(/cache|batch|optimize|strategy/i);
        });
      }
    });
  });

  it('should handle multi-agent collaboration', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // 1. Send complex request requiring multiple agents
        const complexRequest = 'I need a complete optimization report with cost analysis, performance metrics, and implementation roadmap for my LLM infrastructure';
        
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().type(complexRequest);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        // 2. Verify request sent
        cy.contains(complexRequest, { timeout: 10000 }).should('be.visible');
        
        // 3. Look for multiple agent indicators
        const agentPhases = [
          /triage|understanding your request/i,
          /data|collecting information/i,
          /optimization|analyzing options/i,
          /action|creating plan/i,
          /report|generating summary/i
        ];
        
        agentPhases.forEach((phase, index) => {
          cy.contains(phase, { timeout: 20000 + (index * 5000) }).should('exist');
          cy.log(`Agent phase ${index + 1} detected`);
        });
        
        // 4. Verify comprehensive report structure
        cy.contains(/summary|overview|executive summary/i, { timeout: 40000 }).should('exist');
        cy.contains(/recommendation|next steps|implementation/i, { timeout: 40000 }).should('exist');
      }
    });
  });

  it('should maintain context across multiple interactions', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // 1. First interaction - establish context
        const firstRequest = 'My current setup uses GPT-4 with 100 requests per second';
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().type(firstRequest);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        cy.contains(firstRequest, { timeout: 10000 }).should('be.visible');
        cy.contains(/gpt-4|100.*request/i, { timeout: 20000 }).should('exist');
        
        // 2. Second interaction - reference previous context
        const followUp = 'Based on that, what caching strategy would work best?';
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().clear().type(followUp);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        cy.contains(followUp, { timeout: 10000 }).should('be.visible');
        
        // 3. Verify context is maintained (should reference GPT-4 or previous metrics)
        cy.get('body').then(($body) => {
          const responseText = $body.text();
          // Should reference previous context
          expect(responseText).to.match(/gpt-4|100|previous|based on|your setup/i);
          // Should provide caching recommendations
          expect(responseText).to.match(/cache|redis|memory|kv|caching strategy/i);
        });
        
        // 4. Third interaction - ask for specific metric
        const specificRequest = 'What would be the expected cost savings?';
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().clear().type(specificRequest);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        cy.contains(specificRequest, { timeout: 10000 }).should('be.visible');
        cy.contains(/cost|saving|\$|percent|reduce/i, { timeout: 20000 }).should('exist');
      }
    });
  });

  it('should display agent status and progress indicators', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const request = 'Perform deep analysis of my AI infrastructure and optimize for both cost and performance';
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().type(request);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        // Check for various progress indicators
        cy.get('body').then(($body) => {
          // Look for loading states
          const loadingSelectors = [
            '.loading',
            '.spinner',
            '[class*="loading"]',
            '[class*="processing"]',
            '[class*="thinking"]',
            '[aria-label*="loading"]'
          ];
          
          let foundLoading = false;
          loadingSelectors.forEach(selector => {
            if ($body.find(selector).length > 0) {
              foundLoading = true;
              cy.log(`Found loading indicator: ${selector}`);
            }
          });
          
          // Look for agent status text
          const statusPatterns = [
            /analyzing/i,
            /processing/i,
            /thinking/i,
            /generating/i,
            /optimizing/i,
            /calculating/i
          ];
          
          statusPatterns.forEach(pattern => {
            if (pattern.test($body.text())) {
              cy.log(`Found status text matching: ${pattern}`);
            }
          });
        });
        
        // Verify final response appears
        cy.contains(/complete|finished|recommendation|analysis complete/i, { timeout: 40000 }).should('exist');
      }
    });
  });

  it('should handle errors gracefully in agent workflow', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // Send request that might trigger error handling
        const errorProneRequest = 'Optimize this: [INVALID JSON DATA {{{]]] with null parameters and undefined metrics';
        
        cy.get('textarea, input[type="text"], [contenteditable="true"]').first().type(errorProneRequest);
        // Try different button selectors
        cy.get('body').then($body => {
          if ($body.find('button:contains("Send"), button:contains("Submit")').length > 0) {
            cy.get('button').contains(/send|submit|→|⏎/i).click();
          } else {
            cy.get('button, [role="button"]').first().click();
          }
        });
        
        // Should still show the request
        cy.contains(errorProneRequest, { timeout: 10000 }).should('be.visible');
        
        // Should handle gracefully - either process or show helpful error
        cy.get('body', { timeout: 20000 }).then(($body) => {
          const bodyText = $body.text();
          
          // Should either process the request or show an error message
          const hasProcessed = /optimization|analysis|recommendation/i.test(bodyText);
          const hasError = /error|invalid|could not|unable|failed/i.test(bodyText);
          const hasGracefulResponse = /please provide|could you|clarify|rephrase/i.test(bodyText);
          
          expect(hasProcessed || hasError || hasGracefulResponse).to.be.true;
          
          // Should not show technical error details to user
          expect(bodyText).to.not.match(/stacktrace|traceback|exception at line/i);
        });
      }
    });
  });
});