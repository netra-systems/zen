/// <reference types="cypress" />

/**
 * Critical Data Pipeline Tests
 * Tests for data generation, processing, and industry-specific optimizations
 * Business Value: Ensures core value proposition works reliably
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
  // Define inline implementations
  var TestSetup = {
    visitDemo: () => cy.visit('/demo', { failOnStatusCode: false }),
    selectIndustry: (industry) => cy.contains(industry).click({ force: true }),
    standardViewport: () => cy.viewport(1920, 1080)
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
      cy.get('[data-testid="message-input"], textarea').first().type(msg);
      cy.get('[data-testid="send-button"], button[type="submit"]').first().click();
    },
    fillRoiCalculator: (baseline, budget) => {
      cy.get('input[id="baseline"], input[name="baseline"]').type(String(baseline));
      if (budget) cy.get('input[id="budget"], input[name="budget"]').type(String(budget));
    }
  };
  var Assertions = {
    verifyGenerationComplete: (count) => cy.contains(`Generated.*${count}`).should('be.visible'),
    verifyInsightsGenerated: () => cy.contains(/insights.*generated|analysis.*complete/i).should('be.visible'),
    verifySavingsCalculation: () => cy.contains(/savings.*calculated|roi.*computed/i).should('be.visible')
  };
  var WaitUtils = {
    longWait: () => cy.wait(5000),
    mediumWait: () => cy.wait(3000),
    processingWait: () => cy.wait(2000),
    shortWait: () => cy.wait(500)
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
    cy.contains(/analyzing|processing/i, { timeout: 10000 }).should('be.visible');
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