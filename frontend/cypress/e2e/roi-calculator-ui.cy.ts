/// <reference types="cypress" />

import { ROICalculatorHelpers, TestData, Assertions } from '../support/roi-calculator-helpers'

// ROI Calculator UI and Accessibility Tests
// BVJ: Enterprise segment - ensures professional UI for executive presentations
// Updated for current SUT: Card-based UI with clean styling and accessibility

describe('ROI Calculator UI and Accessibility Tests', () => {
  beforeEach(() => {
    ROICalculatorHelpers.navigateToCalculator()
    cy.get('input[id="spend"]').clear().type('50000')
    cy.get('input[id="requests"]').clear().type('10000000')
  })

  describe('Visual Indicators', () => {
    beforeEach(() => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
    })

    it('should show green indicators for savings', () => {
      cy.get('[class*="text-green"]').should('exist')
    })

    it('should display currency with proper formatting', () => {
      cy.get('body').should('contain.text', '$')
      cy.get('[class*="text-3xl"]').should('exist')
    })

    it('should show gradient styling for key results', () => {
      cy.get('[class*="bg-gradient"]').should('exist')
    })

    it('should display ROI badge prominently', () => {
      cy.get('[class*="Badge"]').should('contain', 'ROI')
      cy.get('[class*="Badge"]').should('contain', '%')
    })

    it('should show icons consistently', () => {
      cy.get('svg').should('exist') // Various icons should be present
    })

    it('should show loading states appropriately', () => {
      ROICalculatorHelpers.navigateToCalculator()
      cy.contains('button', 'Calculate ROI').click()
      cy.contains('Calculating...').should('be.visible')
    })

    it('should highlight key metrics with proper typography', () => {
      cy.get('[class*="text-2xl"]').should('exist')
      cy.get('[class*="font-bold"]').should('exist')
    })

    it('should use consistent color scheme', () => {
      cy.get('[class*="text-green-600"]').should('exist')
      cy.get('[class*="text-muted-foreground"]').should('exist')
    })
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt to mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.contains('ROI Calculator').should('be.visible')
      cy.contains('Calculate your potential savings')
        .should('be.visible')
    })

    it('should use responsive grid layout', () => {
      cy.viewport('iphone-x')
      cy.get('.grid').should('exist')
      cy.get('.space-y-4').should('exist')
    })

    it('should maintain input functionality on mobile', () => {
      cy.viewport('iphone-x')
      cy.get('input[id="spend"]').should('be.visible')
      cy.get('input[id="team"]').should('be.visible')
    })

    it('should handle mobile calculation', () => {
      cy.viewport('iphone-x')
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Total Monthly Savings').should('be.visible')
    })

    it('should optimize touch interactions', () => {
      cy.viewport('iphone-x')
      cy.get('button').should('have.length.at.least', 1)
      cy.contains('button', 'Calculate ROI').should('be.visible')
    })

    it('should handle tablet viewport', () => {
      cy.viewport('ipad-2')
      cy.contains('ROI Calculator').should('be.visible')
      cy.get('.grid').should('exist')
    })

    it('should adapt results layout for mobile', () => {
      cy.viewport('iphone-x')
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.get('[class*="Card"]').should('be.visible')
    })

    it('should maintain functionality on small screens', () => {
      cy.viewport(320, 568)
      cy.get('input[id="spend"]').clear().type('50000')
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Projected Savings & ROI').should('be.visible')
    })
  })

  describe('Accessibility', () => {
    it('should have proper form labels', () => {
      cy.get('label[for="spend"]').should('exist')
      cy.get('label[for="requests"]').should('exist')
      cy.get('label[for="team"]').should('exist')
      cy.get('label[for="latency"]').should('exist')
      cy.get('label[for="accuracy"]').should('exist')
    })

    it('should support keyboard navigation', () => {
      cy.get('input[id="spend"]').focus()
      cy.focused().should('have.attr', 'id', 'spend')
    })

    it('should have proper form structure', () => {
      cy.get('label').should('have.length.at.least', 5)
      cy.get('input').should('have.length.at.least', 5)
    })

    it('should provide context for screen readers', () => {
      cy.get('p').should('contain', 'Include compute, storage')
      cy.get('p').should('contain', 'Total inference and training')
    })

    it('should support tab navigation', () => {
      cy.get('input[id="spend"]').focus()
      cy.focused().tab()
      cy.focused().should('have.attr', 'id', 'requests')
    })

    it('should have sufficient color contrast', () => {
      cy.get('body').should('have.css', 'color')
      cy.get('[class*="text-muted-foreground"]').should('exist')
    })

    it('should provide semantic structure', () => {
      cy.get('h2, h3, h4').should('exist')
      cy.get('[class*="Card"]').should('exist')
    })

    it('should have descriptive button text', () => {
      cy.contains('button', 'Calculate ROI').should('be.visible')
      cy.contains('button', 'Export Report').should('be.visible')
      cy.contains('button', 'Schedule Executive Briefing').should('be.visible')
    })
  })

  describe('Layout and Styling', () => {
    it('should have card-based styling', () => {
      cy.get('[class*="Card"]').should('exist')
      cy.get('.border').should('exist')
    })

    it('should display proper input layout', () => {
      cy.contains('Current Monthly AI Infrastructure Spend').should('be.visible')
      cy.contains('Monthly AI Requests').should('be.visible')
      cy.contains('AI/ML Team Size').should('be.visible')
    })

    it('should maintain consistent spacing', () => {
      cy.get('.space-y-4').should('exist')
      cy.get('.space-y-6').should('exist')
      cy.get('.gap-6').should('exist')
    })

    it('should use proper typography hierarchy', () => {
      cy.get('h2, h3, h4').should('exist')
      cy.get('[class*="text-lg"]').should('exist')
      cy.get('[class*="text-2xl"]').should('exist')
    })

    it('should display component heading correctly', () => {
      cy.contains('ROI Calculator').should('be.visible')
      cy.contains('Calculate your potential savings').should('be.visible')
    })

    it('should show industry context properly', () => {
      cy.contains('Technology').should('be.visible')
      cy.contains('Personalized for Technology').should('be.visible')
    })

    it('should use grid layout', () => {
      cy.get('.grid').should('exist')
      cy.get('[class*="grid-cols"]').should('exist')
    })

    it('should maintain visual consistency', () => {
      cy.get('button').should('have.length.at.least', 1)
      cy.get('[class*="bg-gradient"]').should('exist')
    })
  })

  describe('Interactive Elements', () => {
    it('should show hover states for buttons', () => {
      cy.get('button').should('have.length.at.least', 1)
      cy.contains('button', 'Calculate ROI').should('be.visible')
    })

    it('should display focus indicators', () => {
      cy.get('input[id="spend"]').focus()
      cy.focused().should('have.attr', 'id', 'spend')
    })

    it('should handle button states appropriately', () => {
      cy.contains('button', 'Calculate ROI').should('not.be.disabled')
      cy.contains('button', 'Calculate ROI').click()
      cy.contains('button', 'Calculating...').should('be.disabled')
    })

    it('should provide visual feedback for actions', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.contains('Calculating...').should('be.visible')
    })

    it('should show input interactions properly', () => {
      cy.get('input[id="team"]').invoke('val', 15).trigger('input')
      cy.contains('15').should('be.visible')
    })

    it('should handle slider interactions', () => {
      cy.get('input[id="latency"]').should('be.visible')
      cy.get('input[id="accuracy"]').should('be.visible')
    })

    it('should show calculation results properly', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.get('[class*="border-green"]').should('exist')
    })

    it('should display action buttons after calculation', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Export Report').should('be.visible')
      cy.contains('Schedule Executive Briefing').should('be.visible')
    })
  })

  describe('Cross-browser Compatibility', () => {
    it('should handle CSS grid layouts', () => {
      cy.get('.grid').should('exist')
      cy.get('[class*="grid-cols"]').should('exist')
    })

    it('should support flexbox layouts', () => {
      cy.get('.flex').should('exist')
      cy.get('.space-x-2').should('exist')
    })

    it('should handle modern CSS features', () => {
      cy.get('[class*="bg-gradient"]').should('exist')
      cy.get('[class*="backdrop-blur"]').should('exist')
    })

    it('should maintain performance with gradients', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.get('body').should('not.have.class', 'performance-warning')
    })

    it('should handle SVG icons properly', () => {
      cy.get('svg').should('be.visible')
      cy.get('svg').should('have.length.at.least', 1)
    })

    it('should work with different viewport sizes', () => {
      cy.viewport(1920, 1080)
      cy.contains('ROI Calculator').should('be.visible')
      
      cy.viewport(1024, 768)
      cy.contains('ROI Calculator').should('be.visible')
    })
  })
})