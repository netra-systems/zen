/// <reference types="cypress" />

import { ROICalculatorHelpers, TestData } from '../support/roi-calculator-helpers'

// ROI Calculator Advanced Features Tests
// BVJ: Enterprise segment - demonstrates advanced capabilities for enterprise sales
// Modular design following 300-line limit and 8-line function requirements

describe('ROI Calculator Advanced Features Tests', () => {
  beforeEach(() => {
    ROICalculatorHelpers.navigateToCalculator()
    ROICalculatorHelpers.setMonthlySpend(TestData.defaultSpend)
    ROICalculatorHelpers.setModelCount(TestData.defaultModels)
    ROICalculatorHelpers.selectModelTypes(['llm'])
  })

  describe('Industry Multipliers', () => {
    it('should apply Technology industry multiplier', () => {
      ROICalculatorHelpers.triggerCalculation()
      ROICalculatorHelpers.validateIndustryMultiplier('Technology')
    })

    it('should show different results for Healthcare', () => {
      ROICalculatorHelpers.navigateToIndustry('Healthcare')
      ROICalculatorHelpers.setMonthlySpend(TestData.defaultSpend)
      ROICalculatorHelpers.setModelCount(TestData.defaultModels)
      ROICalculatorHelpers.selectModelTypes(['llm'])
      ROICalculatorHelpers.triggerCalculation()
      ROICalculatorHelpers.validateIndustryMultiplier('Healthcare')
    })

    it('should show different results for Financial Services', () => {
      ROICalculatorHelpers.navigateToIndustry('Financial Services')
      ROICalculatorHelpers.setMonthlySpend(TestData.defaultSpend)
      ROICalculatorHelpers.setModelCount(TestData.defaultModels)
      ROICalculatorHelpers.selectModelTypes(['llm'])
      ROICalculatorHelpers.triggerCalculation()
      ROICalculatorHelpers.validateIndustryMultiplier('Financial Services')
    })

    it('should display industry-specific benefits', () => {
      ROICalculatorHelpers.triggerCalculation()
      ROICalculatorHelpers.validateIndustryBenefits()
    })

    it('should show compliance considerations', () => {
      ROICalculatorHelpers.navigateToIndustry('Healthcare')
      ROICalculatorHelpers.setMonthlySpend(TestData.defaultSpend)
      ROICalculatorHelpers.triggerCalculation()
      cy.contains('HIPAA Compliance').should('be.visible')
    })

    it('should apply industry-specific multipliers to calculations', () => {
      ROICalculatorHelpers.triggerCalculation()
      cy.get('[data-testid="monthly-savings"]').invoke('text')
        .then(techSavings => {
          ROICalculatorHelpers.navigateToIndustry('Financial Services')
          ROICalculatorHelpers.setMonthlySpend(TestData.defaultSpend)
          ROICalculatorHelpers.triggerCalculation()
          cy.get('[data-testid="monthly-savings"]').invoke('text')
            .should('not.equal', techSavings)
        })
    })

    it('should show industry benchmarks', () => {
      ROICalculatorHelpers.triggerCalculation()
      cy.contains('Industry Benchmark').should('be.visible')
      cy.contains(/\d+% above average/).should('be.visible')
    })

    it('should display regulatory impact', () => {
      ROICalculatorHelpers.navigateToIndustry('Financial Services')
      ROICalculatorHelpers.triggerCalculation()
      cy.contains('Regulatory Compliance').should('be.visible')
    })
  })

  describe('Export and Sharing', () => {
    beforeEach(() => {
      ROICalculatorHelpers.triggerCalculation()
    })

    it('should display export options', () => {
      ROICalculatorHelpers.validateExportOptions()
    })

    it('should allow downloading PDF report', () => {
      ROICalculatorHelpers.downloadPDFReport()
    })

    it('should allow exporting to Excel', () => {
      ROICalculatorHelpers.exportToExcel()
    })

    it('should allow sharing via email', () => {
      ROICalculatorHelpers.shareViaEmail()
      cy.get('input[type="email"]').should('be.visible')
    })

    it('should generate shareable link', () => {
      ROICalculatorHelpers.generateShareableLink()
      cy.contains('Copy Link').should('be.visible')
    })

    it('should copy link to clipboard', () => {
      ROICalculatorHelpers.generateShareableLink()
      cy.contains('Copy Link').click()
      cy.contains('Copied!').should('be.visible')
    })

  })

  describe('Comparison Features', () => {
    beforeEach(() => {
      ROICalculatorHelpers.triggerCalculation()
    })

    it('should show comparison with competitors', () => {
      cy.contains('Compare with Alternatives').should('be.visible')
    })

    it('should display competitor pricing', () => {
      ROICalculatorHelpers.openComparisonView()
      ROICalculatorHelpers.validateCompetitorComparison()
    })

    it('should highlight Netra advantages', () => {
      ROICalculatorHelpers.openComparisonView()
      cy.get('[data-testid="advantage-badge"]')
        .should('have.class', 'bg-green-500')
    })

    it('should show feature comparison matrix', () => {
      ROICalculatorHelpers.openComparisonView()
      ROICalculatorHelpers.validateComparisonMatrix()
    })

  })

  describe('Interactive Features', () => {
    it('should allow recalculation with new values', () => {
      ROICalculatorHelpers.triggerCalculation()
      cy.contains('Adjust Values').click()
      ROICalculatorHelpers.setMonthlySpend(100000)
      cy.contains('button', 'Recalculate').click()
      cy.wait(3000)
      cy.contains('Updated Results').should('be.visible')
    })

    it('should show tooltips on hover', () => {
      cy.get('[data-testid="info-icon"]').first()
        .trigger('mouseenter')
      cy.contains('This represents').should('be.visible')
    })

    it('should expand/collapse sections', () => {
      cy.contains('Advanced Options').click()
      cy.contains('GPU Utilization').should('be.visible')
      cy.contains('Advanced Options').click()
      cy.contains('GPU Utilization').should('not.be.visible')
    })

    it('should save calculation history', () => {
      ROICalculatorHelpers.triggerCalculation()
      cy.contains('View History').click()
      cy.get('[data-testid="history-item"]')
        .should('have.length.at.least', 1)
    })

    it('should enable scenario comparison', () => {
      ROICalculatorHelpers.triggerCalculation()
      cy.contains('Save Scenario').click()
      cy.get('input[placeholder="Scenario name"]').type('Base Case')
      cy.contains('Save').click()
      
      ROICalculatorHelpers.setMonthlySpend(TestData.highSpend)
      ROICalculatorHelpers.triggerCalculation()
      cy.contains('Compare Scenarios').should('be.visible')
    })

    it('should support What-If analysis', () => {
      ROICalculatorHelpers.triggerCalculation()
      cy.contains('What-If Analysis').click()
      cy.get('[data-testid="scenario-slider"]').should('be.visible')
    })

    it('should allow parameter sensitivity analysis', () => {
      ROICalculatorHelpers.triggerCalculation()
      cy.contains('Sensitivity Analysis').click()
      cy.contains('Parameter Impact').should('be.visible')
    })

    it('should display optimization recommendations', () => {
      ROICalculatorHelpers.triggerCalculation()
      cy.contains('Optimization Recommendations')
        .should('be.visible')
      cy.get('[data-testid="recommendation"]')
        .should('have.length.at.least', 3)
    })
  })

  describe('Advanced Analytics', () => {
    beforeEach(() => {
      ROICalculatorHelpers.triggerCalculation()
    })

    it('should show trend analysis', () => {
      cy.contains('Trend Analysis').click()
      cy.get('[data-testid="trend-chart"]').should('be.visible')
      cy.contains('6-Month Projection').should('be.visible')
    })

    it('should display risk assessment', () => {
      cy.contains('Risk Analysis').should('be.visible')
      cy.contains('Implementation Risk').should('be.visible')
      cy.contains('Market Risk').should('be.visible')
    })

  })

})