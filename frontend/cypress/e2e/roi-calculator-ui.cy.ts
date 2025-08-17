/// <reference types="cypress" />

import { ROICalculatorHelpers, TestData, Assertions } from '../support/roi-calculator-helpers'

// ROI Calculator UI and Accessibility Tests
// BVJ: Enterprise segment - ensures professional UI for executive presentations
// Modular design following 300-line limit and 8-line function requirements

describe('ROI Calculator UI and Accessibility Tests', () => {
  beforeEach(() => {
    ROICalculatorHelpers.navigateToCalculator()
    ROICalculatorHelpers.setMonthlySpend(TestData.defaultSpend)
    ROICalculatorHelpers.setModelCount(TestData.defaultModels)
    ROICalculatorHelpers.selectModelTypes(['llm'])
  })

  describe('Visual Indicators', () => {
    beforeEach(() => {
      ROICalculatorHelpers.triggerCalculation()
    })

    it('should show green indicators for savings', () => {
      Assertions.hasGreenIndicator('[data-testid="savings-indicator"]')
    })

    it('should display progress bars', () => {
      cy.get('[data-testid="savings-progress"]').should('be.visible')
      cy.get('[data-testid="savings-progress"]')
        .should('have.css', 'width')
    })

    it('should animate value changes', () => {
      cy.get('[data-testid="animated-value"]')
        .should('have.class', 'animate-pulse')
    })

    it('should show check marks for benefits', () => {
      cy.get('[data-testid="benefit-check"]')
        .should('have.length.at.least', 5)
      Assertions.hasGreenIndicator('[data-testid="benefit-check"]')
    })

    it('should display status icons consistently', () => {
      cy.get('[data-testid="status-icon"]').each($icon => {
        cy.wrap($icon).should('have.attr', 'aria-label')
      })
    })

    it('should show loading states appropriately', () => {
      ROICalculatorHelpers.navigateToCalculator()
      cy.contains('button', 'Calculate ROI').click()
      cy.get('.loading-spinner').should('be.visible')
      cy.get('.loading-text').should('contain', 'Calculating')
    })

    it('should highlight key metrics visually', () => {
      cy.get('[data-testid="key-metric"]').each($metric => {
        cy.wrap($metric).should('have.class', 'highlight')
      })
    })

    it('should use consistent color scheme', () => {
      cy.get('[data-testid="savings-indicator"]')
        .should('have.css', 'color', 'rgb(34, 197, 94)')
      cy.get('[data-testid="warning-indicator"]')
        .should('have.css', 'color', 'rgb(245, 158, 11)')
    })
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt to mobile viewport', () => {
      ROICalculatorHelpers.switchToMobileViewport()
      cy.get('[data-testid="roi-calculator"]').should('be.visible')
      cy.contains('Calculate Your AI Optimization Savings')
        .should('be.visible')
    })

    it('should stack inputs vertically on mobile', () => {
      ROICalculatorHelpers.switchToMobileViewport()
      ROICalculatorHelpers.validateMobileLayout()
    })

    it('should show mobile-optimized sliders', () => {
      ROICalculatorHelpers.switchToMobileViewport()
      cy.get('input[type="range"]').first()
        .should('have.css', 'width', '100%')
    })

    it('should handle mobile calculation', () => {
      ROICalculatorHelpers.switchToMobileViewport()
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Monthly Savings').should('be.visible')
    })

    it('should optimize touch interactions', () => {
      ROICalculatorHelpers.switchToMobileViewport()
      cy.get('button').each($btn => {
        cy.wrap($btn).should('have.css', 'min-height', '44px')
      })
    })

    it('should handle mobile navigation', () => {
      ROICalculatorHelpers.switchToMobileViewport()
      cy.get('[data-testid="mobile-menu"]').should('be.visible')
      cy.get('[data-testid="mobile-menu"]').click()
      cy.contains('Results').should('be.visible')
    })

    it('should scale charts for mobile', () => {
      ROICalculatorHelpers.switchToMobileViewport()
      ROICalculatorHelpers.triggerCalculation()
      cy.get('[data-testid="savings-chart"]')
        .should('have.css', 'max-width', '100%')
    })

    it('should maintain functionality on small screens', () => {
      cy.viewport(320, 568)
      ROICalculatorHelpers.setMonthlySpend(TestData.defaultSpend)
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      cy.contains('Results').should('be.visible')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      ROICalculatorHelpers.validateARIALabels()
    })

    it('should support keyboard navigation', () => {
      cy.get('input[type="range"][data-testid="monthly-spend"]').focus()
      cy.focused().type('{rightarrow}{rightarrow}')
      cy.contains('$52,000').should('be.visible')
    })

    it('should have proper form labels', () => {
      ROICalculatorHelpers.validateFormLabels()
    })

    it('should announce results to screen readers', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      ROICalculatorHelpers.validateScreenReaderAnnouncement()
    })

    it('should support tab navigation', () => {
      cy.get('input[data-testid="monthly-spend"]').focus()
      cy.focused().tab()
      cy.focused().should('have.attr', 'data-testid', 'model-count')
    })

    it('should have sufficient color contrast', () => {
      cy.get('[data-testid="roi-calculator"]')
        .should('have.css', 'color')
        .and('not.equal', 'rgba(0, 0, 0, 0)')
    })

    it('should support screen reader navigation', () => {
      cy.get('[role="main"]').should('exist')
      cy.get('[role="banner"]').should('exist')
      cy.get('[role="contentinfo"]').should('exist')
    })

    it('should have descriptive button text', () => {
      cy.get('button').each($btn => {
        cy.wrap($btn).should('not.be.empty')
        cy.wrap($btn).invoke('text').should('have.length.above', 2)
      })
    })
  })

  describe('Layout and Styling', () => {
    it('should have glassmorphic styling', () => {
      cy.get('.backdrop-blur-md').should('exist')
      cy.get('.bg-opacity-10').should('exist')
    })

    it('should display all input sections', () => {
      cy.contains('Infrastructure Metrics').should('be.visible')
      cy.contains('Operational Metrics').should('be.visible')
      cy.contains('AI Workload Details').should('be.visible')
    })

    it('should maintain consistent spacing', () => {
      cy.get('[data-testid="input-section"]').each($section => {
        cy.wrap($section).should('have.css', 'margin-bottom')
      })
    })

    it('should use proper typography hierarchy', () => {
      cy.get('h1').should('have.css', 'font-size')
        .and('not.equal', cy.get('h2').invoke('css', 'font-size'))
      cy.get('h2').should('have.css', 'font-size')
        .and('not.equal', cy.get('h3').invoke('css', 'font-size'))
    })

    it('should display component heading', () => {
      cy.contains('h2', 'Calculate Your AI Optimization Savings')
        .should('be.visible')
    })

    it('should show industry context', () => {
      cy.contains('Technology').should('be.visible')
      cy.contains('industry-specific').should('be.visible')
    })

    it('should handle overflow content gracefully', () => {
      cy.get('[data-testid="roi-calculator"]')
        .should('have.css', 'overflow-x', 'hidden')
    })

    it('should maintain visual consistency', () => {
      cy.get('.btn-primary').should('have.length.at.least', 1)
      cy.get('.btn-primary').first()
        .should('have.css', 'background-color')
    })
  })

  describe('Interactive Elements', () => {
    it('should show hover states for interactive elements', () => {
      cy.get('button').first().trigger('mouseover')
      cy.get('button').first().should('have.class', 'hover:bg-opacity-20')
    })

    it('should display focus indicators', () => {
      cy.get('input[type="range"]').first().focus()
      cy.focused().should('have.css', 'outline-width')
        .and('not.equal', '0px')
    })

    it('should handle disabled states', () => {
      ROICalculatorHelpers.setMonthlySpend(0)
      cy.contains('button', 'Calculate ROI').should('be.disabled')
      cy.contains('button', 'Calculate ROI')
        .should('have.class', 'opacity-50')
    })

    it('should provide visual feedback for actions', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.get('.animate-spin').should('exist')
    })

    it('should show tooltips consistently', () => {
      cy.get('[data-testid="info-icon"]').each($icon => {
        cy.wrap($icon).trigger('mouseenter')
        cy.get('[role="tooltip"]').should('be.visible')
        cy.wrap($icon).trigger('mouseleave')
      })
    })

    it('should handle error states visually', () => {
      ROICalculatorHelpers.setModelCount(-1)
      cy.get('input[data-testid="model-count"]')
        .should('have.class', 'border-red-500')
    })

    it('should show loading animations', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.get('[data-testid="loading-animation"]')
        .should('have.class', 'animate-pulse')
    })

    it('should display success states', () => {
      ROICalculatorHelpers.triggerCalculation()
      cy.get('[data-testid="success-indicator"]')
        .should('have.class', 'text-green-500')
    })
  })

  describe('Cross-browser Compatibility', () => {
    it('should handle CSS grid layouts', () => {
      cy.get('[data-testid="roi-calculator"]')
        .should('have.css', 'display', 'grid')
    })

    it('should support flexbox layouts', () => {
      cy.get('[data-testid="input-section"]')
        .should('have.css', 'display', 'flex')
    })

    it('should handle modern CSS features', () => {
      cy.get('.backdrop-blur-md')
        .should('have.css', 'backdrop-filter')
    })

    it('should maintain performance with animations', () => {
      cy.contains('button', 'Calculate ROI').click()
      cy.get('body').should('not.have.class', 'performance-warning')
    })

    it('should handle high DPI displays', () => {
      cy.get('svg').should('be.visible')
      cy.get('svg').should('have.attr', 'viewBox')
    })
  })
})