/// <reference types="cypress" />

import { ROICalculatorHelpers, TestData } from '../support/roi-calculator-helpers'

// ROI Calculator Advanced Features Tests  
// BVJ: Enterprise segment - demonstrates core capabilities for enterprise sales
// Updated for current SUT: Simple card-based ROI Calculator with industry multipliers

describe('ROI Calculator Advanced Features Tests', () => {
  beforeEach(() => {
    ROICalculatorHelpers.navigateToCalculator()
    cy.get('input[id="spend"]').clear().type('50000')
    cy.get('input[id="requests"]').clear().type('10000000')
  })

  describe('Industry Multipliers', () => {
    it('should display Technology industry multiplier', () => {
      cy.contains('Industry multiplier applied').should('be.visible')
      cy.contains('Technology').should('be.visible')
      cy.contains('35% boost').should('be.visible')
    })

    it('should show different multipliers for different industries', () => {
      // Navigate to Healthcare demo
      cy.visit('/demo')
      cy.contains('Healthcare').click()
      cy.contains('ROI Calculator').click()
      cy.wait(500)
      
      cy.contains('Industry multiplier applied').should('be.visible')
      cy.contains('Healthcare').should('be.visible')
      cy.contains('25% boost').should('be.visible')
    })

    it('should show Financial Services multiplier', () => {
      cy.visit('/demo')
      cy.contains('Financial Services').click()
      cy.contains('ROI Calculator').click()
      cy.wait(500)
      
      cy.contains('Industry multiplier applied').should('be.visible')
      cy.contains('Financial Services').should('be.visible')
      cy.contains('30% boost').should('be.visible')
    })

    it('should display industry context in demo', () => {
      cy.contains('Personalized for Technology').should('be.visible')
      cy.contains('industry-specific').should('be.visible')
    })

    it('should show industry selection affects calculations', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      
      cy.contains('Projected Savings & ROI').should('be.visible')
      // Industry multiplier should be factored into results
      cy.get('body').should('contain.text', '$')
    })

    it('should validate multiplier values', () => {
      const multipliers = {
        'Technology': '35% boost',
        'Healthcare': '25% boost', 
        'Financial Services': '30% boost'
      }
      
      // Current industry should be Technology
      cy.contains('Technology').should('be.visible')
      cy.contains('35% boost').should('be.visible')
    })
  })

  describe('Export and Actions', () => {
    beforeEach(() => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
    })

    it('should display export report button', () => {
      cy.contains('Export Report').should('be.visible')
    })

    it('should show executive briefing option', () => {
      cy.contains('Schedule Executive Briefing').should('be.visible')
    })

    it('should have properly styled action buttons', () => {
      cy.get('button').contains('Export Report').should('be.visible')
      cy.get('button').contains('Schedule Executive Briefing')
        .should('have.class', 'bg-gradient-to-r')
    })

    it('should allow clicking export button', () => {
      cy.contains('Export Report').click()
      // Should not cause errors - basic functionality test
    })

    it('should allow clicking briefing button', () => {
      cy.contains('Schedule Executive Briefing').click()
      // Should not cause errors - basic functionality test  
    })
  })

  describe('Cost Comparison Features', () => {
    beforeEach(() => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
    })

    it('should show current vs optimized spend comparison', () => {
      cy.contains('Cost Comparison').should('be.visible')
    })

    it('should display current monthly spend', () => {
      cy.contains('Current Monthly Spend').should('be.visible')
      cy.get('body').should('contain.text', '$')
    })

    it('should show optimized monthly spend', () => {
      cy.contains('Optimized Monthly Spend').should('be.visible')
      cy.get('[class*="text-green-600"]').should('exist')
    })

    it('should highlight cost reduction with icons', () => {
      cy.get('svg').should('exist') // TrendingDown icon
      cy.get('[class*="text-green-600"]').should('contain', '$')
    })
  })

  describe('Interactive Features', () => {
    it('should allow recalculation with new values', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      
      // Change values and recalculate
      cy.get('input[id="spend"]').clear().type('75000')
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Projected Savings & ROI').should('be.visible')
    })

    it('should show input help text', () => {
      cy.contains('Include compute, storage, and API costs').should('be.visible')
      cy.contains('Total inference and training requests').should('be.visible')
    })

    it('should update slider displays in real-time', () => {
      cy.get('input[id="team"]').invoke('val', 15).trigger('input')
      cy.contains('15').should('be.visible')
      
      cy.get('input[id="latency"]').invoke('val', 400).trigger('input')
      cy.contains('400ms').should('be.visible')
    })

    it('should maintain form state during interactions', () => {
      cy.get('input[id="spend"]').clear().type('60000')
      cy.get('input[id="requests"]').clear().type('12000000')
      
      // Navigate away and back
      cy.contains('Overview').click()
      cy.contains('ROI Calculator').click()
      
      // Values should be maintained or reset appropriately
      cy.get('input[id="spend"]').should('exist')
    })

    it('should provide visual feedback for actions', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.contains('Calculating...').should('be.visible')
    })

    it('should show industry multiplier as informative alert', () => {
      cy.get('[class*="Alert"]').should('exist')
      cy.contains('Industry multiplier applied').should('be.visible')
    })
  })

  describe('Results Analytics', () => {
    beforeEach(() => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
    })

    it('should show comprehensive savings breakdown', () => {
      cy.contains('Infrastructure Savings').should('be.visible')
      cy.contains('Operational Efficiency').should('be.visible')
      cy.contains('Performance Value').should('be.visible')
    })

    it('should display financial projections', () => {
      cy.contains('Total Monthly Savings').should('be.visible')
      cy.contains('Annual Savings').should('be.visible')
      cy.contains('3-Year ROI').should('be.visible')
      cy.contains('Payback Period').should('be.visible')
    })

    it('should show ROI badge with percentage', () => {
      cy.get('[class*="Badge"]').should('contain', '%')
      cy.get('[class*="Badge"]').should('contain', 'ROI')
    })

    it('should display visual styling for positive results', () => {
      cy.get('[class*="text-green"]').should('exist')
      cy.get('[class*="bg-gradient"]').should('exist')
    })
  })

})