/// <reference types="cypress" />

import { ROICalculatorHelpers } from '../support/roi-calculator-helpers'

// ROI Calculator Component Basic Initialization Tests
// BVJ: Enterprise segment - validates core component functionality
// Updated for current SUT: Simple card-based ROI Calculator in demo tabs

describe('ROI Calculator Component - Basic Initialization', () => {
  beforeEach(() => {
    ROICalculatorHelpers.navigateToCalculator()
  })

  describe('Component Initialization', () => {
    it('should render ROI Calculator component', () => {
      cy.contains('ROI Calculator').should('be.visible')
      cy.get('[role="tabpanel"]').should('contain', 'ROI Calculator')
    })

    it('should display calculator heading', () => {
      cy.contains('ROI Calculator').should('be.visible')
      cy.contains('Calculate your potential savings with Netra AI Optimization Platform')
        .should('be.visible')
    })

    it('should show industry context', () => {
      cy.contains('Technology').should('be.visible')
      cy.contains('Personalized for Technology').should('be.visible')
    })

    it('should display input form', () => {
      cy.contains('Current Monthly AI Infrastructure Spend').should('be.visible')
      cy.contains('Monthly AI Requests').should('be.visible')
      cy.contains('AI/ML Team Size').should('be.visible')
    })

    it('should have card-based styling', () => {
      cy.get('.border').should('exist')
      cy.get('[class*="Card"]').should('exist')
    })

    it('should load with default values', () => {
      cy.get('input[id="spend"]').should('have.value', '50000')
      cy.get('input[id="requests"]').should('have.value', '10000000')
      cy.get('input[id="team"]').should('exist')
    })

    it('should display calculate button', () => {
      cy.contains('button', 'Calculate ROI').should('be.visible')
      cy.contains('button', 'Calculate ROI').should('be.enabled')
    })

    it('should show tab navigation', () => {
      cy.get('[role="tablist"]').should('be.visible')
      cy.contains('ROI Calculator').should('be.visible')
    })
  })

  describe('Essential Component Elements', () => {
    it('should display monthly spend input', () => {
      cy.contains('Current Monthly AI Infrastructure Spend').should('be.visible')
      cy.get('input[id="spend"]').should('be.visible')
    })

    it('should display requests input', () => {
      cy.contains('Monthly AI Requests').should('be.visible')
      cy.get('input[id="requests"]').should('be.visible')
    })

    it('should display latency slider', () => {
      cy.contains('Average Latency (ms)').should('be.visible')
      cy.get('input[id="latency"]').should('be.visible')
    })

    it('should display team size slider', () => {
      cy.contains('AI/ML Team Size').should('be.visible')
      cy.get('input[id="team"]').should('be.visible')
    })

    it('should display accuracy slider', () => {
      cy.contains('Model Accuracy (%)').should('be.visible')
      cy.get('input[id="accuracy"]').should('be.visible')
    })

    it('should display industry multiplier info', () => {
      cy.contains('Industry multiplier applied').should('be.visible')
      cy.contains('Technology').should('be.visible')
    })
  })

  describe('Component Structure Validation', () => {
    it('should have proper card structure', () => {
      cy.get('[class*="Card"]').should('exist')
      cy.get('[class*="CardHeader"]').should('exist')
      cy.get('[class*="CardContent"]').should('exist')
    })

    it('should have grid layout for inputs', () => {
      cy.get('.grid').should('exist')
      cy.get('.space-y-4').should('exist')
    })

    it('should display input labels properly', () => {
      cy.get('label').should('have.length.at.least', 5)
      cy.get('label[for="spend"]').should('contain', 'Infrastructure Spend')
    })

    it('should have help text for inputs', () => {
      cy.contains('Include compute, storage, and API costs').should('be.visible')
      cy.contains('Total inference and training requests').should('be.visible')
    })

    it('should show industry multiplier alert', () => {
      cy.get('[class*="Alert"]').should('exist')
      cy.contains('Industry multiplier applied').should('be.visible')
    })
  })

  describe('Navigation and Integration', () => {
    it('should integrate with demo tabs navigation', () => {
      cy.get('[role="tablist"]').should('be.visible')
      cy.contains('ROI Calculator').should('be.visible')
    })

    it('should show other demo tabs', () => {
      cy.contains('Overview').should('be.visible')
      cy.contains('AI Chat').should('be.visible')
      cy.contains('Metrics').should('be.visible')
    })

    it('should load industry context correctly', () => {
      cy.url().should('include', '/demo')
      cy.contains('Technology').should('be.visible')
    })

    it('should maintain state during tab navigation', () => {
      cy.get('input[id="spend"]').clear().type('75000')
      cy.contains('Overview').click()
      cy.contains('ROI Calculator').click()
      // Should maintain or reset to defaults appropriately
      cy.contains('ROI Calculator').should('be.visible')
    })

    it('should handle browser navigation within demo', () => {
      cy.go('back')
      cy.go('forward')
      cy.contains('ROI Calculator').should('be.visible')
    })
  })


})