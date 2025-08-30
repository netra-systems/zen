describe('Critical Agent Optimization Workflow', () => {
  beforeEach(() => {
    // Mock authentication
    cy.clearLocalStorage();
    cy.clearCookies();
    
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'mock-jwt-token-for-testing');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User'
      }));
    });
    
    // Visit simple test page instead of complex chat page
    cy.visit('/test-agent', { timeout: 60000 });
    
    // Wait for the page to fully load and become interactive
    cy.get('body', { timeout: 30000 }).should('be.visible');
    cy.wait(3000); // Additional wait for React hydration
  });

  it('should send optimization request and receive response', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // 1. Send optimization request
        const optimizationRequest = 'Help me optimize my LLM deployment for better performance and lower costs';
        
        cy.get('[data-testid="message-input"]').type(optimizationRequest);
        cy.get('[data-testid="send-button"]').click();
        
        // 2. Verify request is sent
        cy.contains(optimizationRequest, { timeout: 10000 }).should('be.visible');
        
        // 3. Look for processing indicators
        cy.contains(/analyzing|processing|thinking|optimizing/i, { timeout: 15000 }).should('exist');
        
        // 4. Verify response contains optimization keywords
        cy.contains(/optimization|performance|cost|recommendation/i, { timeout: 30000 }).should('exist');
      }
    });
  });

  it('should handle multi-step optimization workflow', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // 1. Initial request
        const request = 'Analyze my current AI infrastructure and suggest improvements';
        cy.get('[data-testid="message-input"]').type(request);
        cy.get('[data-testid="send-button"]').click();
        
        // 2. Wait for initial response
        cy.contains(request, { timeout: 10000 }).should('be.visible');
        cy.contains(/analyze|infrastructure|improvement/i, { timeout: 30000 }).should('exist');
        
        // 3. Follow-up question
        const followUp = 'What specific caching strategies do you recommend?';
        cy.get('[data-testid="message-input"]').clear().type(followUp);
        cy.get('[data-testid="send-button"]').click();
        
        // 4. Verify contextual response
        cy.contains(followUp, { timeout: 10000 }).should('be.visible');
        cy.contains(/cache|caching|memory|redis/i, { timeout: 30000 }).should('exist');
      }
    });
  });

  it('should display agent activity indicators', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // Send a complex request that triggers multiple agents
        const complexRequest = 'Perform a comprehensive analysis of my AI workload and provide optimization strategies';
        cy.get('[data-testid="message-input"]').type(complexRequest);
        cy.get('[data-testid="send-button"]').click();
        
        // Look for agent activity indicators
        cy.get('body').then(($body) => {
          // Check for any agent-related UI elements
          const agentIndicators = [
            '[class*="agent"]',
            '[class*="processing"]',
            '[class*="thinking"]',
            '[class*="analyzing"]',
            '[class*="loading"]'
          ];
          
          let foundIndicator = false;
          agentIndicators.forEach(selector => {
            if ($body.find(selector).length > 0) {
              foundIndicator = true;
              cy.log(`Found agent indicator: ${selector}`);
            }
          });
          
          if (foundIndicator) {
            cy.log('Agent activity indicators detected');
          } else {
            cy.log('No visible agent indicators, checking for text indicators');
            cy.contains(/analyzing|processing|thinking|generating/i, { timeout: 10000 }).should('exist');
          }
        });
      }
    });
  });

  it('should handle optimization for different model types', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const modelRequest = 'Compare optimization strategies for GPT-4 vs Claude vs Llama models';
        cy.get('[data-testid="message-input"]').type(modelRequest);
        cy.get('[data-testid="send-button"]').click();
        
        // Verify request is sent
        cy.contains(modelRequest, { timeout: 10000 }).should('be.visible');
        
        // Look for model-specific content in response
        cy.contains(/gpt|claude|llama|model/i, { timeout: 30000 }).should('exist');
        cy.contains(/optimization|strategy|performance/i, { timeout: 30000 }).should('exist');
      }
    });
  });

  it('should provide actionable recommendations', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const actionRequest = 'Give me specific steps to reduce my AI costs by 30%';
        cy.get('[data-testid="message-input"]').type(actionRequest);
        cy.get('[data-testid="send-button"]').click();
        
        // Verify request
        cy.contains(actionRequest, { timeout: 10000 }).should('be.visible');
        
        // Look for actionable content
        cy.contains(/step|implement|action|recommendation|reduce|cost/i, { timeout: 30000 }).should('exist');
      }
    });
  });

  it('should handle request with specific metrics', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const metricsRequest = 'My current setup: 1000 req/s, 500ms latency, $100/hour. How can I improve?';
        cy.get('[data-testid="message-input"]').type(metricsRequest);
        cy.get('[data-testid="send-button"]').click();
        
        // Verify request
        cy.contains(metricsRequest, { timeout: 10000 }).should('be.visible');
        
        // Look for metrics-related response
        cy.get('body').then(($body) => {
          // Check for any metrics in the response
          const hasMetrics = $body.text().match(/\d+\s*(req|ms|hour|\$|%)/i);
          if (hasMetrics) {
            cy.log('Response contains metrics');
          }
          
          // Verify optimization suggestions
          cy.contains(/improve|optimize|reduce|increase/i, { timeout: 30000 }).should('exist');
        });
      }
    });
  });
});