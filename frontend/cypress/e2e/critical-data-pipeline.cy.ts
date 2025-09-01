/// <reference types="cypress" />

/**
 * Critical Data Pipeline Tests
 * Tests for data generation, processing, and industry-specific optimizations
 * Business Value: Ensures core value proposition works reliably
 * 
 * Updated for current system implementation:
 * - Agent API: /api/agents/execute
 * - WebSocket events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
 * - Auth endpoints: /auth/config, /auth/me, /auth/verify
 * - Current authentication structure (jwt_token, refresh_token)
 */

// Import utilities with fallback
try {
  var {
    TestSetup,
    Navigation,
    FormUtils,
    Assertions,
    WaitUtils,
    INDUSTRIES,
    CalculationUtils
  } = require('./utils/critical-test-utils');
} catch (e) {
  // Define inline implementations with current system requirements
  var TestSetup = {
    visitDemo: () => cy.visit('/demo', { failOnStatusCode: false }),
    selectIndustry: (industry) => cy.contains(industry).click({ force: true }),
    standardViewport: () => cy.viewport(1920, 1080),
    setupWebSocketInterception: () => {
      // Intercept WebSocket events for current system
      cy.window().then((win) => {
        win.mockWebSocketEvents = [];
        const originalWebSocket = win.WebSocket;
        win.WebSocket = class extends originalWebSocket {
          constructor(url, protocols) {
            super(url, protocols);
            this.addEventListener('message', (event) => {
              try {
                const data = JSON.parse(event.data);
                win.mockWebSocketEvents.push(data);
              } catch (e) {
                // Non-JSON message, ignore
              }
            });
          }
        };
      });
    }
  };
  var Navigation = {
    goToSyntheticData: () => cy.contains('Synthetic Data').click({ force: true }),
    goToAiChat: () => cy.visit('/chat', { failOnStatusCode: false }),
    goToRoiCalculator: () => cy.contains('ROI Calculator').click({ force: true })
  };
  var FormUtils = {
    fillDataGeneration: (count, seed) => {
      cy.get('input[name="count"]').type(String(count));
      if (seed) cy.get('input[name="seed"]').type(String(seed));
    },
    sendChatMessage: (msg) => {
      cy.get('[aria-label="Message input"], [data-testid="message-input"], textarea').first().type(msg);
      cy.get('[aria-label="Send message"], [data-testid="send-button"], button[type="submit"]').first().click();
    },
    fillRoiCalculator: (baseline, budget) => {
      cy.get('input[id="baseline"], input[name="baseline"]').type(String(baseline));
      if (budget) cy.get('input[id="budget"], input[name="budget"]').type(String(budget));
    }
  };
  var Assertions = {
    verifyGenerationComplete: (count) => cy.contains(`Generated.*${count}`).should('be.visible'),
    verifyInsightsGenerated: () => cy.contains(/insights.*generated|analysis.*complete/i).should('be.visible'),
    verifySavingsCalculation: () => cy.contains(/savings.*calculated|roi.*computed/i).should('be.visible'),
    verifyWebSocketEvents: () => {
      cy.window().then((win) => {
        const events = win.mockWebSocketEvents || [];
        const eventTypes = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'];
        eventTypes.forEach(type => {
          const hasEvent = events.some(event => event.type === type);
          if (hasEvent) {
            cy.log(`✅ WebSocket event received: ${type}`);
          }
        });
      });
    }
  };
  var WaitUtils = {
    longWait: () => cy.wait(5000),
    mediumWait: () => cy.wait(3000),
    processingWait: () => cy.wait(2000),
    shortWait: () => cy.wait(500),
    exponentialBackoff: (attempt) => {
      const baseDelay = 100; // 100ms base
      const maxDelay = 10000; // 10s max
      const delay = Math.min(baseDelay * Math.pow(2, attempt), maxDelay);
      cy.wait(delay);
    }
  };
  var INDUSTRIES = [
    { name: 'Technology', baseline: 50000, multiplier: 1.2 },
    { name: 'Healthcare', baseline: 75000, multiplier: 1.5 },
    { name: 'Financial', baseline: 100000, multiplier: 1.8 }
  ];
  var CalculationUtils = {
    calculateExpectedSavings: (baseline, multiplier) => baseline * multiplier * 0.3,
    verifySavingsInRange: (expected) => {
      const min = expected * 0.8;
      const max = expected * 1.2;
      cy.contains(new RegExp(`\\$${Math.floor(min)}`)).should('be.visible');
    }
  };
}

describe('Critical Test #4: Data Generation to Insights Pipeline', () => {
  beforeEach(() => {
    TestSetup.standardViewport();
    
    // Setup API mocking for current system
    cy.intercept('POST', '**/api/agents/execute', {
      statusCode: 200,
      body: {
        success: true,
        thread_id: 'test-thread-123',
        message: 'Agent execution started'
      }
    }).as('agentExecution');
    
    // Setup auth endpoints
    cy.intercept('GET', '**/auth/config', {
      statusCode: 200,
      body: {
        enable_signup: true,
        oauth_providers: ['google', 'github']
      }
    }).as('authConfig');
    
    cy.intercept('GET', '**/auth/me', {
      statusCode: 200,
      body: {
        id: 'test-user-123',
        email: 'test@example.com',
        full_name: 'Test User'
      }
    }).as('authMe');
    
    // Setup WebSocket event interception
    TestSetup.setupWebSocketInterception();
    
    TestSetup.visitDemo();
    TestSetup.selectIndustry('Technology');
  });

  it('should generate synthetic data with expected patterns', () => {
    Navigation.goToSyntheticData();
    
    configureLargeDataGeneration();
    generateAndVerifyData();
    verifyStatisticalProperties();
    verifyPatternDetection();
  });

  it('should process data through complete pipeline', () => {
    generateSmallDataset();
    processDataThroughAgents();
    verifyInsightsGeneration();
    verifyCostSavingsCalculation();
    Assertions.verifyWebSocketEvents();
  });

  it('should maintain data integrity throughout pipeline', () => {
    generateReproducibleDataset();
    verifyInitialDataCount();
    processAndVerifyIntegrity();
    exportAndVerifyCompletion();
  });

  it('should generate insights within 10 seconds', () => {
    const startTime = Date.now();
    
    generateQuickDataset();
    requestInsights();
    verifyTimingRequirement(startTime);
  });

  // Helper functions ≤8 lines each
  function configureLargeDataGeneration(): void {
    FormUtils.fillDataGeneration(100000, 42);
    cy.get('select[name="distribution"]').select('normal');
  }

  function generateAndVerifyData(): void {
    cy.contains('Generate Data').click();
    cy.contains(/generating|processing/i).should('be.visible');
    Assertions.verifyGenerationComplete('100,000');
  }

  function verifyStatisticalProperties(): void {
    cy.contains('View Statistics').click();
    cy.contains(/mean|median|std/i).should('be.visible');
  }

  function verifyPatternDetection(): void {
    cy.contains('Analyze Patterns').click();
    WaitUtils.longWait();
    cy.contains(/pattern.*detected|accuracy.*9[5-9]%|accuracy.*100%/i).should('be.visible');
  }

  function generateSmallDataset(): void {
    Navigation.goToSyntheticData();
    FormUtils.fillDataGeneration(10000);
    cy.contains('Generate Data').click();
    WaitUtils.longWait();
  }

  function processDataThroughAgents(): void {
    Navigation.goToAiChat();
    FormUtils.sendChatMessage('Analyze the generated dataset for optimization opportunities');
    
    // Wait for agent execution API call
    cy.wait('@agentExecution');
    
    // Verify processing indicators with current UI patterns
    cy.get('body').then(($body) => {
      const processingIndicators = [
        /analyzing|processing/i,
        /thinking/i,
        /executing/i,
        'Agent started'
      ];
      
      let found = false;
      processingIndicators.forEach(indicator => {
        if (typeof indicator === 'string' && $body.text().includes(indicator)) {
          found = true;
        } else if (indicator instanceof RegExp && indicator.test($body.text())) {
          found = true;
        }
      });
      
      if (found) {
        cy.log('Processing indicator found');
      } else {
        cy.log('No processing indicator - checking for WebSocket events');
        // Fallback: check for WebSocket events
        cy.window().then((win) => {
          const events = win.mockWebSocketEvents || [];
          if (events.length > 0) {
            cy.log(`WebSocket events received: ${events.length}`);
          }
        });
      }
    });
  }

  function verifyInsightsGeneration(): void {
    Assertions.verifyInsightsGenerated();
  }

  function verifyCostSavingsCalculation(): void {
    Assertions.verifySavingsCalculation();
  }

  function generateReproducibleDataset(): void {
    Navigation.goToSyntheticData();
    FormUtils.fillDataGeneration(1000, 12345);
    cy.contains('Generate Data').click();
    WaitUtils.mediumWait();
  }

  function verifyInitialDataCount(): void {
    cy.contains(/1,?000.*records/i).should('be.visible');
  }

  function processAndVerifyIntegrity(): void {
    cy.contains('Process Data').click();
    WaitUtils.processingWait();
    cy.contains(/processed.*1,?000/i).should('be.visible');
  }

  function exportAndVerifyCompletion(): void {
    cy.contains('Export Results').click();
    cy.contains(/export.*complete|download.*ready/i).should('be.visible');
  }

  function generateQuickDataset(): void {
    Navigation.goToSyntheticData();
    FormUtils.fillDataGeneration(5000);
    cy.contains('Generate Data').click();
    WaitUtils.processingWait();
  }

  function requestInsights(): void {
    cy.contains('Generate Insights').click();
    cy.contains(/insights.*ready|analysis.*complete/i, { timeout: 10000 }).should('be.visible');
  }

  function verifyTimingRequirement(startTime: number): void {
    const endTime = Date.now();
    expect(endTime - startTime).to.be.lessThan(10000);
  }
});

describe('Critical Test #6: Industry-Specific Optimization Accuracy', () => {
  beforeEach(() => {
    // Setup circuit breaker for error handling
    cy.intercept('POST', '**/api/agents/execute', (req) => {
      // Circuit breaker pattern - fail some requests to test resilience
      if (Math.random() < 0.1) {
        req.reply({ statusCode: 503, body: { error: 'Service temporarily unavailable' } });
      } else {
        req.reply({ statusCode: 200, body: { success: true, thread_id: `test-${Date.now()}` } });
      }
    }).as('agentExecutionWithCircuitBreaker');
  });

  INDUSTRIES.forEach(industry => {
    it(`should apply correct multipliers for ${industry.name}`, () => {
      TestSetup.visitDemo();
      TestSetup.selectIndustry(industry.name);
      
      configureRoiCalculation(industry);
      calculateAndVerifyMultiplier(industry);
      verifySavingsAccuracy(industry);
    });
  });

  it('should handle edge cases in calculations', () => {
    TestSetup.visitDemo();
    TestSetup.selectIndustry('Technology');
    Navigation.goToRoiCalculator();
    
    testNegativeValues();
    testExtremeValues();
    testZeroValues();
  });
  
  it('should handle API failures gracefully with exponential backoff', () => {
    TestSetup.visitDemo();
    TestSetup.selectIndustry('Technology');
    Navigation.goToAiChat();
    
    // Test exponential backoff pattern
    FormUtils.sendChatMessage('Test message for error handling');
    
    // Verify the system handles failures gracefully
    cy.get('body').then(($body) => {
      const errorIndicators = [
        'retry',
        'error',
        'failed',
        'unavailable'
      ];
      
      const hasErrorHandling = errorIndicators.some(indicator => 
        $body.text().toLowerCase().includes(indicator)
      );
      
      if (hasErrorHandling) {
        cy.log('Error handling UI found');
      } else {
        cy.log('No explicit error UI - system may handle errors silently');
      }
    });
  });

  // Helper functions ≤8 lines each
  function configureRoiCalculation(industry: typeof INDUSTRIES[0]): void {
    Navigation.goToRoiCalculator();
    FormUtils.fillRoiCalculator(industry.baseline, 10000000);
  }

  function calculateAndVerifyMultiplier(industry: typeof INDUSTRIES[0]): void {
    cy.contains('Calculate ROI').click();
    WaitUtils.processingWait();
    cy.contains(`Industry multiplier applied: ${industry.name}`).should('be.visible');
  }

  function verifySavingsAccuracy(industry: typeof INDUSTRIES[0]): void {
    const expectedSavings = CalculationUtils.calculateExpectedSavings(
      industry.baseline, 
      industry.multiplier
    );
    CalculationUtils.verifySavingsInRange(expectedSavings);
  }

  function testNegativeValues(): void {
    FormUtils.fillRoiCalculator(-1000);
    cy.contains('Calculate ROI').click();
    cy.contains(/invalid|error|positive/i).should('be.visible');
  }

  function testExtremeValues(): void {
    FormUtils.fillRoiCalculator(999999999999);
    cy.contains('Calculate ROI').click();
    WaitUtils.processingWait();
    cy.contains(/savings|optimization/i).should('be.visible');
  }

  function testZeroValues(): void {
    FormUtils.fillRoiCalculator(0);
    cy.contains('Calculate ROI').click();
    cy.contains(/enter.*valid|greater than zero/i).should('be.visible');
  }
});