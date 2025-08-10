describe('Critical Agent Optimization Workflow', () => {
  const testUser = {
    email: 'test@netra.ai',
    password: 'TestPassword123!'
  };

  beforeEach(() => {
    // Login and navigate to chat
    cy.clearLocalStorage();
    cy.clearCookies();
    cy.visit('/login');
    cy.get('input[type="email"]').type(testUser.email);
    cy.get('input[type="password"]').type(testUser.password);
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/chat');
    cy.wait(2000); // Wait for WebSocket connection
  });

  it('should complete full optimization workflow with multiple agents', () => {
    // 1. Send optimization request
    const optimizationRequest = 'I need to optimize my GPT-4 deployment. Current setup: 100 requests/sec, 2000ms avg latency, $50/hour cost. Goal: Reduce latency by 50% while maintaining costs.';
    
    cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
      .type(optimizationRequest);
    cy.get('button').contains(/send|submit|optimize/i).click();
    
    // 2. Verify request is received
    cy.contains(optimizationRequest).should('be.visible');
    
    // 3. Verify Triage Agent activation
    cy.contains(/triage|analyzing request|understanding/i, { timeout: 15000 }).should('be.visible');
    
    // 4. Verify Data Agent activation
    cy.contains(/data|collecting|gathering/i, { timeout: 15000 }).should('be.visible');
    
    // 5. Verify Optimization Core Agent activation
    cy.contains(/optimization|analyzing performance|calculating/i, { timeout: 20000 }).should('be.visible');
    
    // 6. Verify Actions Agent activation
    cy.contains(/action|recommendation|implement/i, { timeout: 20000 }).should('be.visible');
    
    // 7. Verify Reporting Agent activation
    cy.contains(/report|summary|results/i, { timeout: 20000 }).should('be.visible');
    
    // 8. Verify final optimization report contains key elements
    cy.contains(/latency reduction/i, { timeout: 30000 }).should('be.visible');
    cy.contains(/cost analysis/i).should('be.visible');
    cy.contains(/recommendation/i).should('be.visible');
    
    // 9. Verify specific optimization strategies are mentioned
    cy.get('[class*="message"], [class*="response"], [class*="agent"]').within(() => {
      // Check for specific optimization techniques
      cy.contains(/caching|cache/i).should('exist');
      cy.contains(/batch|batching/i).should('exist');
      cy.contains(/model|quantization|optimization/i).should('exist');
    });
    
    // 10. Verify metrics are provided
    cy.contains(/\d+(\.\d+)?%/).should('be.visible'); // Percentage improvements
    cy.contains(/\$\d+/).should('be.visible'); // Cost estimates
    cy.contains(/\d+ms/).should('be.visible'); // Latency measurements
  });

  it('should handle complex multi-model optimization scenario', () => {
    // 1. Send complex multi-model request
    const complexRequest = `
      Optimize our AI pipeline:
      - Claude 3.5: 500 req/s, 1500ms latency, $30/hour
      - GPT-4: 300 req/s, 2000ms latency, $45/hour  
      - Llama-3: 800 req/s, 800ms latency, $15/hour
      Need: 20% latency reduction, maintain quality, reduce costs by 30%
    `;
    
    cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
      .type(complexRequest);
    cy.get('button').contains(/send|submit|optimize/i).click();
    
    // 2. Verify multi-agent collaboration
    const agents = ['triage', 'data', 'optimization', 'action', 'report'];
    agents.forEach(agent => {
      cy.contains(new RegExp(agent, 'i'), { timeout: 30000 }).should('be.visible');
    });
    
    // 3. Verify model-specific recommendations
    cy.contains(/claude/i, { timeout: 40000 }).should('be.visible');
    cy.contains(/gpt-4/i).should('be.visible');
    cy.contains(/llama/i).should('be.visible');
    
    // 4. Verify cost-benefit analysis
    cy.contains(/cost.*reduction/i).should('be.visible');
    cy.contains(/performance.*impact/i).should('be.visible');
    cy.contains(/trade-off/i).should('be.visible');
    
    // 5. Verify actionable recommendations
    cy.contains(/implement|deploy|configure/i).should('be.visible');
    cy.contains(/priority|step/i).should('be.visible');
  });

  it('should provide interactive optimization feedback', () => {
    // 1. Start with initial optimization request
    const initialRequest = 'Optimize my LLM API for cost efficiency';
    cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
      .type(initialRequest);
    cy.get('button').contains(/send|submit|optimize/i).click();
    
    // 2. Wait for initial response
    cy.contains(/optimization|analyzing/i, { timeout: 30000 }).should('be.visible');
    cy.contains(/recommendation/i, { timeout: 40000 }).should('be.visible');
    
    // 3. Send follow-up question
    const followUp = 'What about caching strategies?';
    cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
      .clear()
      .type(followUp);
    cy.get('button').contains(/send|submit/i).click();
    
    // 4. Verify contextual response about caching
    cy.contains(/cache|caching/i, { timeout: 30000 }).should('be.visible');
    cy.contains(/ttl|invalidation|memory/i).should('be.visible');
    
    // 5. Request specific implementation
    const implementation = 'Show me the implementation code for Redis caching';
    cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
      .clear()
      .type(implementation);
    cy.get('button').contains(/send|submit/i).click();
    
    // 6. Verify code example is provided
    cy.contains(/redis|implementation|code/i, { timeout: 30000 }).should('be.visible');
    cy.get('pre, code, [class*="code"]').should('exist');
  });

  it('should handle optimization errors gracefully', () => {
    // 1. Send request with invalid parameters
    const invalidRequest = 'Optimize with -100% latency and -200% cost (impossible goals)';
    cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
      .type(invalidRequest);
    cy.get('button').contains(/send|submit|optimize/i).click();
    
    // 2. Verify agents still process request
    cy.contains(/analyzing|processing/i, { timeout: 20000 }).should('be.visible');
    
    // 3. Verify system provides realistic feedback
    cy.contains(/constraint|realistic|achievable|limitation/i, { timeout: 30000 }).should('be.visible');
    
    // 4. Verify alternative recommendations are provided
    cy.contains(/alternative|instead|consider/i).should('be.visible');
    
    // 5. Send corrected request
    const correctedRequest = 'Okay, please optimize for 30% latency reduction with reasonable cost increase';
    cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
      .clear()
      .type(correctedRequest);
    cy.get('button').contains(/send|submit/i).click();
    
    // 6. Verify successful optimization after correction
    cy.contains(/optimization|recommendation/i, { timeout: 30000 }).should('be.visible');
    cy.contains(/30%|latency/i).should('be.visible');
  });

  it('should export optimization report', () => {
    // 1. Complete an optimization request
    const request = 'Optimize our AI deployment for production scale';
    cy.get('textarea[placeholder*="message"], input[placeholder*="message"], textarea[placeholder*="ask"], input[placeholder*="ask"]')
      .type(request);
    cy.get('button').contains(/send|submit|optimize/i).click();
    
    // 2. Wait for complete report
    cy.contains(/report|summary/i, { timeout: 40000 }).should('be.visible');
    
    // 3. Look for export button
    cy.get('button').contains(/export|download|save/i).should('be.visible').click();
    
    // 4. Verify export options if modal appears
    cy.get('[role="dialog"], [class*="modal"], [class*="export"]').then($modal => {
      if ($modal.length > 0) {
        // Select export format if options are presented
        cy.contains(/pdf|json|markdown/i).first().click();
        cy.get('button').contains(/confirm|download/i).click();
      }
    });
    
    // 5. Verify download or copy action completed
    cy.contains(/exported|downloaded|copied/i, { timeout: 5000 }).should('be.visible');
  });
});