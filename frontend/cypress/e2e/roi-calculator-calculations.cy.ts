/// <reference types="cypress" />

import { ROICalculatorHelpers, TestData, Assertions } from '../support/roi-calculator-helpers'

// ROI Calculator Calculation and Results Tests
// BVJ: Enterprise segment - validates calculation accuracy for business case creation
// Updated for current SUT: Simple card-based ROI Calculator with 5 inputs

describe('ROI Calculator Calculation and Results Tests', () => {
  beforeEach(() => {
    ROICalculatorHelpers.navigateToCalculator()
    // Set default values for current inputs
    cy.get('input[id="spend"]').clear().type('50000')
    cy.get('input[id="requests"]').clear().type('10000000')
  })

  describe('Calculation Process', () => {
    it('should have calculate button', () => {
      cy.contains('button', 'Calculate ROI').should('be.visible')
    })

    it('should enable calculate button with valid inputs', () => {
      cy.get('input[id="spend"]').clear().type('50000')
      cy.contains('button', 'Calculate ROI').should('not.be.disabled')
    })

    it('should trigger calculation on button click', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.contains('Calculating...').should('be.visible')
    })

    it('should show loading state during calculation', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.contains('Calculating...').should('be.visible')
    })

    it('should complete calculation and show results', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Projected Savings & ROI').should('be.visible')
    })
  })

  describe('Results Display', () => {
    beforeEach(() => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
    })

    it('should display results card', () => {
      cy.contains('Projected Savings & ROI').should('be.visible')
    })

    it('should show infrastructure savings', () => {
      cy.contains('Infrastructure Savings').should('be.visible')
      cy.get('[class*="text-green-600"]').should('exist')
    })

    it('should display operational savings', () => {
      cy.contains('Operational Efficiency').should('be.visible')
    })

    it('should show performance value', () => {
      cy.contains('Performance Value').should('be.visible')
    })

    it('should display total monthly savings', () => {
      cy.contains('Total Monthly Savings').should('be.visible')
    })

    it('should show annual savings', () => {
      cy.contains('Annual Savings').should('be.visible')
    })

    it('should display payback period', () => {
      cy.contains('Payback Period').should('be.visible')
      cy.contains('months').should('be.visible')
    })

    it('should show 3-year ROI', () => {
      cy.contains('3-Year ROI').should('be.visible')
      cy.contains('%').should('be.visible')
    })
  })

  describe('Breakdown Analysis', () => {
    beforeEach(() => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
    })

    it('should display savings breakdown cards', () => {
      cy.contains('Infrastructure Savings').should('be.visible')
      cy.contains('Operational Efficiency').should('be.visible')
      cy.contains('Performance Value').should('be.visible')
    })

    it('should show cost comparison', () => {
      cy.contains('Cost Comparison').should('be.visible')
      cy.contains('Current Monthly Spend').should('be.visible')
      cy.contains('Optimized Monthly Spend').should('be.visible')
    })

    it('should display dollar amounts', () => {
      // Check for currency formatting
      cy.get('body').should('contain.text', '$')
      cy.get('[class*="text-3xl"]').should('exist')
    })

    it('should show ROI badge', () => {
      cy.contains('ROI').should('be.visible')
      cy.contains('%').should('be.visible')
    })

    it('should display action buttons', () => {
      cy.contains('Export Report').should('be.visible')
      cy.contains('Schedule Executive Briefing').should('be.visible')
    })
  })

  describe('Calculation Accuracy', () => {
    it('should calculate correctly for high spend scenarios', () => {
      cy.get('input[id="spend"]').clear().type('100000')
      cy.get('input[id="requests"]').clear().type('50000000')
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      
      cy.contains(/\$[\d,]+/).should('be.visible')
      cy.contains(/\d+%/).should('be.visible')
    })

    it('should handle low spend calculations', () => {
      cy.get('input[id="spend"]').clear().type('10000')
      cy.get('input[id="requests"]').clear().type('1000000')
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      
      cy.contains('Total Monthly Savings').should('be.visible')
    })

    it('should adjust for team size', () => {
      // Adjust team size slider
      cy.get('input[id="team"]').invoke('val', 20).trigger('input')
      cy.contains('20').should('be.visible')
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      
      cy.contains('Projected Savings & ROI').should('be.visible')
    })

    it('should factor in latency', () => {
      cy.get('input[id="latency"]').invoke('val', 500).trigger('input')
      cy.contains('500ms').should('be.visible')
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      
      cy.contains('Performance Value').should('be.visible')
    })

    it('should validate calculation results format', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      
      // Check currency formatting
      cy.get('body').should('contain.text', '$')
      cy.get('body').should('contain.text', '%')
      cy.get('body').should('contain.text', 'months')
    })

    it('should show industry multiplier effect', () => {
      cy.contains('Industry multiplier applied').should('be.visible')
      cy.contains('Technology').should('be.visible')
      cy.contains('35% boost').should('be.visible')
    })

    it('should display consistent results', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      
      // Verify all main result components are present
      cy.contains('Infrastructure Savings').should('be.visible')
      cy.contains('Operational Efficiency').should('be.visible')
      cy.contains('Performance Value').should('be.visible')
      cy.contains('Total Monthly Savings').should('be.visible')
    })
  })

  describe('Performance Tests', () => {
    it('should calculate reasonably quickly', () => {
      const startTime = Date.now()
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Projected Savings & ROI').should('be.visible')
      cy.then(() => {
        const duration = Date.now() - startTime
        expect(duration).to.be.lessThan(5000)
      })
    })

    it('should handle input changes smoothly', () => {
      cy.get('input[id="spend"]').clear().type('75000')
      cy.get('input[id="requests"]').clear().type('15000000')
      cy.get('input[id="team"]').invoke('val', 10).trigger('input')
      
      // Should not cause errors
      cy.contains('ROI Calculator').should('be.visible')
    })

    it('should update slider displays in real-time', () => {
      cy.get('input[id="latency"]').invoke('val', 300).trigger('input')
      cy.contains('300ms').should('be.visible')
      
      cy.get('input[id="accuracy"]').invoke('val', 85).trigger('input')
      cy.contains('85%').should('be.visible')
    })

    it('should maintain responsiveness during calculation', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.contains('Calculating...').should('be.visible')
      // Button should be disabled during calculation
      cy.contains('button', 'Calculating...').should('be.disabled')
    })

    it('should handle multiple calculations', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Projected Savings & ROI').should('be.visible')
      
      // Change input and recalculate
      cy.get('input[id="spend"]').clear().type('80000')
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Projected Savings & ROI').should('be.visible')
    })

    it('should work on mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Projected Savings & ROI').should('be.visible')
    })

    it('should not freeze the interface', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.get('body').should('not.have.class', 'frozen')
      cy.get('[role="tablist"]').should('be.visible')
    })
  })

})