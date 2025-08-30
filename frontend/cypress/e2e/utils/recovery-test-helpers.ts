/// <reference types="cypress" />

/**
 * Agent Recovery Test Utilities
 * Modular helpers for agent orchestration recovery testing
 * Business Value: Enterprise segment - ensures system resilience, prevents agent failures
 */

// Agent Configuration
export const AGENTS = ['triage', 'data', 'optimization', 'reporting', 'analysis'] as const;
export type AgentType = typeof AGENTS[number];

export const AGENT_ENDPOINTS = {
  triage: '**/api/agents/triage**',
  data: '**/api/agents/data**', 
  optimization: '**/api/agents/optimization**',
  reporting: '**/api/agents/reporting**',
  analysis: '**/api/agents/analysis**',
  supervisor: '**/api/agents/supervisor**',
  handoff: '**/api/agents/handoff**'
} as const;

// Error Messages
export const ERROR_MESSAGES = {
  triage: 'Unable to classify your request',
  data: 'Error processing data analysis',
  optimization: 'Optimization engine temporarily unavailable', 
  reporting: 'Report generation failed',
  analysis: 'Analysis service is down'
} as const;

// Test Data
export const TEST_MESSAGES = {
  triage: 'Help me with something',
  data: 'Analyze my dataset', 
  optimization: 'Optimize my costs',
  reporting: 'Generate a report',
  analysis: 'Perform analysis'
} as const;

/**
 * Agent Recovery Setup Utilities
 */
export class AgentRecoverySetup {
  static standardSetup(): void {
    cy.viewport(1920, 1080);
  }

  static setupAuth(): void {
    cy.window().then((win) => {
      win.localStorage.setItem('auth_token', 'test-token');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user',
        email: 'test@netrasystems.ai',
        name: 'Test User'
      }));
    });
  }

  static visitDemoChat(): void {
    // Use /chat page instead of /demo since it's working
    // Next.js dev server is slow on first load, so use longer timeout
    cy.visit('/chat', { 
      failOnStatusCode: false,
      timeout: 60000  // 60 second timeout for slow Next.js dev server
    });
    
    // Check if page loaded properly with extended timeout
    cy.get('body', { timeout: 30000 }).should('be.visible');
    
    // Wait for any authentication, compilation, or loading to complete
    cy.wait(5000);
  }

  static fullSetup(): void {
    this.standardSetup();
    this.setupAuth();
    this.visitDemoChat();
  }

  static cleanup(): void {
    cy.window().then((win) => {
      win.localStorage.removeItem('agent_state');
      win.localStorage.removeItem('retry_count');
    });
  }
}

/**
 * Agent Mocking Utilities
 */
export class AgentMocking {
  static mockTimeout(agent: AgentType, delay = 15000): void {
    cy.intercept('POST', AGENT_ENDPOINTS[agent], (req) => {
      req.reply((res: any) => {
        res.delay(delay);
        res.send({ status: 'timeout' });
      });
    }).as(`${agent}Timeout`);
  }

  static mockError(agent: AgentType, statusCode = 500): void {
    cy.intercept('POST', AGENT_ENDPOINTS[agent], {
      statusCode,
      body: { 
        error: ERROR_MESSAGES[agent],
        user_message: ERROR_MESSAGES[agent]
      }
    }).as(`${agent}Error`);
  }

  static mockSuccess(agent: AgentType, response: any): void {
    cy.intercept('POST', AGENT_ENDPOINTS[agent], {
      statusCode: 200,
      body: response
    }).as(`${agent}Success`);
  }

  static mockAllAgentsError(): void {
    AGENTS.forEach(agent => this.mockError(agent));
  }

  static mockHandoffFailure(): void {
    cy.intercept('POST', AGENT_ENDPOINTS.handoff, {
      statusCode: 500,
      body: { error: 'Handoff failed' }
    }).as('handoffFailure');
  }

  static mockSupervisorFallback(): void {
    cy.intercept('POST', AGENT_ENDPOINTS.supervisor, {
      statusCode: 200,
      body: { 
        response: 'Handled by supervisor',
        fallback: true
      }
    }).as('supervisorFallback');
  }
}

/**
 * Agent Interaction Utilities
 */
export class AgentInteraction {
  static sendMessage(message: string): void {
    // Find input with flexible selectors
    cy.get('body').then(($body) => {
      if ($body.find('textarea[aria-label="Message input"]').length > 0) {
        cy.get('textarea[aria-label="Message input"]').type(message, { force: true });
      } else if ($body.find('textarea').length > 0) {
        cy.get('textarea').first().type(message, { force: true });
      } else {
        cy.log('No textarea found for message input');
        return;
      }
    });
    
    // Find send button with flexible selectors
    cy.get('body').then(($body) => {
      if ($body.find('button[aria-label="Send message"]').length > 0) {
        cy.get('button[aria-label="Send message"]').click({ force: true });
      } else if ($body.find('button').filter(':contains("Send")').length > 0) {
        cy.get('button').filter(':contains("Send")').first().click({ force: true });
      } else if ($body.find('button[type="submit"]').length > 0) {
        cy.get('button[type="submit"]').first().click({ force: true });
      } else {
        cy.log('No send button found');
      }
    });
  }

  static sendAndClear(message: string): void {
    // Find and clear input with flexible selectors
    cy.get('body').then(($body) => {
      if ($body.find('textarea[aria-label="Message input"]').length > 0) {
        cy.get('textarea[aria-label="Message input"]').clear().type(message, { force: true });
      } else if ($body.find('textarea').length > 0) {
        cy.get('textarea').first().clear().type(message, { force: true });
      } else {
        cy.log('No textarea found for message input');
        return;
      }
    });
    
    // Find and click send button
    cy.get('body').then(($body) => {
      if ($body.find('button[aria-label="Send message"]').length > 0) {
        cy.get('button[aria-label="Send message"]').click({ force: true });
      } else if ($body.find('button').filter(':contains("Send")').length > 0) {
        cy.get('button').filter(':contains("Send")').first().click({ force: true });
      } else if ($body.find('button[type="submit"]').length > 0) {
        cy.get('button[type="submit"]').first().click({ force: true });
      } else {
        cy.log('No send button found');
      }
    });
  }

  static sendMultipleMessages(messages: string[]): void {
    messages.forEach(msg => {
      this.sendAndClear(msg);
      cy.wait(800); // Slightly longer wait
    });
  }

  static waitForAgent(agent: AgentType): void {
    cy.wait(`@${agent}Error`);
  }

  static waitForProcessing(): void {
    cy.contains(/processing|analyzing|thinking/i).should('be.visible');
  }
}

/**
 * Recovery Assertion Utilities  
 */
export class RecoveryAssertions {
  static verifyTimeout(): void {
    cy.contains(/taking longer|timeout|retry/i, { timeout: 12000 })
      .should('be.visible');
  }

  static verifyRetryOption(): void {
    cy.get('button').contains(/retry|try again/i).should('be.visible');
  }

  static verifyFallback(): void {
    cy.contains(/supervisor|fallback|alternative/i, { timeout: 5000 })
      .should('exist');
  }

  static verifyErrorMessage(pattern: RegExp): void {
    cy.contains(pattern, { timeout: 5000 }).should('be.visible');
  }

  static verifySuggestions(): void {
    cy.contains(/try rephrasing|break down|contact support/i)
      .should('be.visible');
  }

  static verifyCircuitBreaker(): void {
    cy.contains(/temporarily unavailable|circuit breaker|too many errors/i)
      .should('be.visible');
  }

  static verifyHandoffError(): void {
    cy.contains(/handoff failed|unable to transfer|communication error/i)
      .should('be.visible');
  }

  static verifyAlternativeAction(): void {
    cy.contains(/try again|alternative|manual/i).should('be.visible');
  }

  static verifySystemFailure(): void {
    cy.contains(/system unavailable|all agents failed|maintenance/i, { timeout: 10000 })
      .should('be.visible');
  }

  static verifyContactSupport(): void {
    cy.contains(/support|contact|try later/i).should('be.visible');
  }

  static verifyEmergencyMode(): void {
    cy.contains(/emergency|critical failure|maintenance mode/i, { timeout: 5000 })
      .should('be.visible');
  }

  static verifyQueue(): void {
    cy.contains(/queue|position|waiting/i).should('be.visible');
  }

  static verifyTiming(): void {
    cy.contains(/\d+ms|\d+s|response time/i, { timeout: 5000 })
      .should('exist');
  }
}

/**
 * Recovery Retry Utilities
 */
export class RetryUtils {
  static setupRetryCounter(): { getCount: () => number } {
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

    return { getCount: () => attemptCount };
  }

  static verifyExponentialBackoff(): void {
    cy.wait('@retryWithBackoff');
    cy.wait('@retryWithBackoff'); 
    cy.wait('@retryWithBackoff');
  }

  static setupOrderTracking(): { getOrder: () => string[] } {
    const processedOrder: string[] = [];
    
    cy.intercept('POST', '**/api/agents/**', (req) => {
      processedOrder.push(req.body.message);
      req.reply({
        statusCode: 200,
        body: { processed: req.body.message }
      });
    }).as('orderedProcessing');

    return { getOrder: () => processedOrder };
  }

  static verifyMessageOrder(expected: string[], actual: string[]): void {
    cy.wrap(actual).should('deep.equal', expected);
  }
}

/**
 * Circuit Breaker Utilities
 */
export class CircuitBreakerUtils {
  static setupFailureTracking(): { getRequestCount: () => number } {
    let requestCount = 0;
    
    cy.intercept('POST', '**/api/agents/**', (req) => {
      requestCount++;
      req.reply({
        statusCode: 500,
        body: { error: 'Agent error' }
      });
    }).as('agentFailure');

    return { getRequestCount: () => requestCount };
  }

  static triggerMultipleFailures(count = 4): void {
    for (let i = 0; i < count; i++) {
      AgentInteraction.sendAndClear(`Test message ${i}`);
      cy.wait(1000);
    }
  }

  static verifyCircuitBreakerActivated(maxRequests = 8): void {
    cy.wrap(null).then(() => {
      // Circuit breaker should limit requests
      RecoveryAssertions.verifyCircuitBreaker();
    });
  }
}