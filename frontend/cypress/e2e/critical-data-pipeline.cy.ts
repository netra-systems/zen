/// <reference types="cypress" />

/**
 * Critical Data Pipeline Tests
 * Tests for data generation, processing, and industry-specific optimizations
 * Business Value: Ensures core value proposition works reliably
 */

import {
  TestSetup,
  Navigation,
  FormUtils,
  Assertions,
  WaitUtils,
  INDUSTRIES,
  CalculationUtils
} from './utils/critical-test-utils';

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