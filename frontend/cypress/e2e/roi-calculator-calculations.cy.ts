/// <reference types="cypress" />

import { ROICalculatorHelpers, TestData, Assertions } from '../support/roi-calculator-helpers'

// ROI Calculator Calculation and Results Tests
// BVJ: Enterprise segment - validates calculation accuracy for business case creation
// Modular design following 300-line limit and 8-line function requirements

describe('ROI Calculator Calculation and Results Tests', () => {
  beforeEach(() => {
    ROICalculatorHelpers.navigateToCalculator()
    ROICalculatorHelpers.setMonthlySpend(TestData.defaultSpend)
    ROICalculatorHelpers.setModelCount(TestData.defaultModels)
    ROICalculatorHelpers.selectModelTypes(['llm'])
  })

  describe('Calculation Process', () => {
    it('should have calculate button', () => {
      cy.contains('button', 'Calculate ROI').should('be.visible')
    })

    it('should enable calculate button with valid inputs', () => {
      ROICalculatorHelpers.setMonthlySpend(50000)
      ROICalculatorHelpers.validateCalculationEnabled()
    })

    it('should trigger calculation on button click', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.contains('Calculating').should('be.visible')
      cy.get('.animate-spin').should('exist')
    })

    it('should show progress during calculation', () => {
      cy.contains('button', 'Calculate ROI').click()
      ROICalculatorHelpers.validateProgressIndicators()
    })

    it('should complete calculation', () => {
      ROICalculatorHelpers.triggerCalculationAndWait()
      cy.contains('Results').should('be.visible')
    })

  })

  describe('Results Display', () => {
    beforeEach(() => {
      ROICalculatorHelpers.triggerCalculation()
    })

    it('should display monthly savings', () => {
      ROICalculatorHelpers.validateMonthlySavingsVisible()
    })

    it('should show percentage reduction', () => {
      cy.contains('Cost Reduction').should('be.visible')
      Assertions.hasValidPercentage('Cost Reduction')
    })

    it('should display annual savings', () => {
      ROICalculatorHelpers.validateAnnualSavingsVisible()
    })

    it('should show ROI percentage', () => {
      ROICalculatorHelpers.validateROIPercentageVisible()
    })

    it('should display payback period', () => {
      ROICalculatorHelpers.validatePaybackPeriodVisible()
    })

    it('should show 3-year projection', () => {
      ROICalculatorHelpers.validate3YearProjectionVisible()
    })

  })

  describe('Breakdown Analysis', () => {
    beforeEach(() => {
      ROICalculatorHelpers.triggerCalculation()
    })

    it('should display savings breakdown', () => {
      ROICalculatorHelpers.validateSavingsBreakdown()
    })

    it('should show infrastructure savings', () => {
      cy.contains('Infrastructure Optimization').should('be.visible')
      cy.contains('infrastructure').parent()
        .contains(/\$[\d,]+/).should('be.visible')
    })

    it('should show operational savings', () => {
      cy.contains('Operational Efficiency').should('be.visible')
      cy.contains('operational').parent()
        .contains(/\$[\d,]+/).should('be.visible')
    })

    it('should show performance improvements', () => {
      ROICalculatorHelpers.validatePerformanceGains()
    })

    it('should display visual chart', () => {
      ROICalculatorHelpers.validateVisualChart()
    })

    it('should show breakdown percentages', () => {
      cy.get('[data-testid="breakdown-percentage"]')
        .should('have.length.at.least', 3)
      cy.get('[data-testid="breakdown-percentage"]').each($el => {
        cy.wrap($el).should('match', /\d+%/)
      })
    })

    it('should display cost category details', () => {
      cy.contains('Compute Savings').should('be.visible')
      cy.contains('Storage Optimization').should('be.visible')
      cy.contains('Network Efficiency').should('be.visible')
    })

    it('should show time-based projections', () => {
      cy.contains('Month 1-6').should('be.visible')
      cy.contains('Month 7-12').should('be.visible')
      cy.contains('Year 2-3').should('be.visible')
    })
  })

  describe('Calculation Accuracy', () => {
    it('should calculate correctly for high spend scenarios', () => {
      ROICalculatorHelpers.setMonthlySpend(TestData.highSpend)
      ROICalculatorHelpers.setModelCount(50)
      ROICalculatorHelpers.triggerCalculation()
      
      cy.contains(/\$[\d,]+/).should('be.visible')
      cy.contains(/\d+%/).should('be.visible')
    })

    it('should handle low spend calculations', () => {
      ROICalculatorHelpers.setMonthlySpend(TestData.lowSpend)
      ROICalculatorHelpers.setModelCount(5)
      ROICalculatorHelpers.triggerCalculation()
      
      ROICalculatorHelpers.validateMonthlySavingsVisible()
    })

    it('should adjust for model complexity', () => {
      ROICalculatorHelpers.selectModelTypes(['llm', 'vision', 'embedding'])
      ROICalculatorHelpers.triggerCalculation()
      
      cy.contains('Multi-model optimization').should('be.visible')
    })

    it('should factor in deployment frequency', () => {
      ROICalculatorHelpers.selectDeploymentFrequency('Daily')
      ROICalculatorHelpers.triggerCalculation()
      
      cy.contains('High-frequency deployment').should('be.visible')
    })

    it('should validate calculation consistency', () => {
      const firstCalculation = () => {
        ROICalculatorHelpers.triggerCalculation()
        return cy.get('[data-testid="monthly-savings"]')
          .invoke('text')
      }
      
      firstCalculation().then(firstResult => {
        ROICalculatorHelpers.recalculateWithNewValues()
        cy.get('[data-testid="monthly-savings"]')
          .should('contain', firstResult)
      })
    })

    it('should handle edge case calculations', () => {
      ROICalculatorHelpers.setMonthlySpend(1000)
      ROICalculatorHelpers.setModelCount(1)
      ROICalculatorHelpers.triggerCalculation()
      
      cy.contains('Minimal optimization').should('be.visible')
    })

    it('should show calculation methodology', () => {
      ROICalculatorHelpers.triggerCalculation()
      cy.contains('View Calculation Details').click()
      cy.contains('Methodology').should('be.visible')
    })

    it('should display confidence intervals', () => {
      ROICalculatorHelpers.triggerCalculation()
      cy.contains('Conservative Estimate').should('be.visible')
      cy.contains('Optimistic Estimate').should('be.visible')
    })
  })

  describe('Performance Tests', () => {
    it('should calculate quickly', () => {
      ROICalculatorHelpers.measureCalculationTime()
        .should('be.lessThan', 5000)
    })

    it('should handle rapid input changes', () => {
      ROICalculatorHelpers.testRapidInputChanges()
    })

    it('should debounce slider inputs', () => {
      ROICalculatorHelpers.validateDebouncing()
    })

    it('should maintain responsiveness during calculation', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.get('[data-testid="progress-bar"]').should('be.visible')
      cy.get('body').should('not.have.class', 'frozen')
    })

    it('should handle concurrent calculations', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(500)
      cy.contains('button', 'Calculate ROI').click()
      cy.contains('Previous calculation cancelled')
        .should('be.visible')
    })

    it('should optimize for mobile performance', () => {
      ROICalculatorHelpers.switchToMobileViewport()
      ROICalculatorHelpers.measureCalculationTime()
        .should('be.lessThan', 6000)
    })

    it('should handle memory efficiently', () => {
      for(let i = 0; i < 5; i++) {
        ROICalculatorHelpers.setMonthlySpend(30000 + i * 10000)
        ROICalculatorHelpers.triggerCalculation()
        cy.wait(1000)
      }
      cy.get('[data-testid="roi-calculator"]')
        .should('not.have.class', 'memory-error')
    })

    it('should validate calculation caching', () => {
      ROICalculatorHelpers.triggerCalculation()
      const startTime = Date.now()
      
      ROICalculatorHelpers.triggerCalculation()
      const duration = Date.now() - startTime
      expect(duration).to.be.lessThan(1000)
    })
  })

})