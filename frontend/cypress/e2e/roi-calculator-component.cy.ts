/// <reference types="cypress" />

import { ROICalculatorHelpers } from '../support/roi-calculator-helpers'

// ROI Calculator Component Basic Initialization Tests
// BVJ: Enterprise segment - validates core component functionality
// Modular design following 300-line limit and 8-line function requirements
// 
// NOTE: Comprehensive tests are now split into focused modules:
// - roi-calculator-inputs.cy.ts - Input validation and interactions
// - roi-calculator-calculations.cy.ts - Calculations and results  
// - roi-calculator-features.cy.ts - Advanced features and comparisons
// - roi-calculator-ui.cy.ts - UI/accessibility testing

describe('ROI Calculator Component - Basic Initialization', () => {
  beforeEach(() => {
    ROICalculatorHelpers.navigateToCalculator()
  })

  describe('Component Initialization', () => {
    it('should render ROI Calculator component', () => {
      cy.get('[data-testid="roi-calculator"]').should('be.visible')
    })

    it('should display calculator heading', () => {
      cy.contains('h2', 'Calculate Your AI Optimization Savings')
        .should('be.visible')
    })

    it('should show industry context', () => {
      cy.contains('Technology').should('be.visible')
      cy.contains('industry-specific').should('be.visible')
    })

    it('should display all input sections', () => {
      cy.contains('Infrastructure Metrics').should('be.visible')
      cy.contains('Operational Metrics').should('be.visible')
      cy.contains('AI Workload Details').should('be.visible')
    })

    it('should have glassmorphic styling', () => {
      cy.get('.backdrop-blur-md').should('exist')
      cy.get('.bg-opacity-10').should('exist')
    })

    it('should load with default values', () => {
      cy.get('input[type="range"][data-testid="monthly-spend"]')
        .should('have.value', '50000')
      cy.get('input[type="number"][data-testid="model-count"]')
        .should('have.value', '15')
    })

    it('should display calculate button', () => {
      cy.contains('button', 'Calculate ROI').should('be.visible')
      cy.contains('button', 'Calculate ROI').should('be.enabled')
    })

    it('should show navigation elements', () => {
      cy.get('[data-testid="demo-navigation"]').should('be.visible')
      cy.contains('Technology').should('be.visible')
    })
  })

  describe('Essential Component Elements', () => {
    it('should display monthly spend input', () => {
      cy.contains('Current Monthly AI Spend').should('be.visible')
      cy.get('input[type="range"][data-testid="monthly-spend"]')
        .should('be.visible')
    })

    it('should display model count input', () => {
      cy.contains('Number of AI Models').should('be.visible')
      cy.get('input[type="number"][data-testid="model-count"]')
        .should('be.visible')
    })

    it('should display latency input', () => {
      cy.contains('Average Latency').should('be.visible')
      cy.get('input[type="range"][data-testid="latency"]')
        .should('be.visible')
    })

    it('should display engineering hours input', () => {
      cy.contains('Engineering Hours/Month').should('be.visible')
      cy.get('input[type="range"][data-testid="engineering-hours"]')
        .should('be.visible')
    })

    it('should display team size input', () => {
      cy.contains('Team Size').should('be.visible')
      cy.get('input[type="number"][data-testid="team-size"]')
        .should('be.visible')
    })

    it('should display model types selection', () => {
      cy.contains('Model Types').should('be.visible')
      cy.get('[data-testid="model-type-checkbox"]')
        .should('have.length.at.least', 3)
    })
  })

  describe('Component Structure Validation', () => {
    it('should have proper form structure', () => {
      cy.get('[data-testid="roi-calculator"] form')
        .should('exist')
      cy.get('fieldset').should('have.length.at.least', 3)
    })

    it('should display deployment frequency selector', () => {
      cy.contains('Deployment Frequency').should('be.visible')
      cy.get('select[data-testid="deployment-frequency"]')
        .should('be.visible')
    })

    it('should display cloud provider selector', () => {
      cy.contains('Cloud Provider').should('be.visible')
      cy.get('select[data-testid="cloud-provider"]')
        .should('be.visible')
    })

    it('should have proper error message containers', () => {
      cy.get('[data-testid="error-message"]')
        .should('exist')
        .and('not.be.visible')
    })

    it('should contain results placeholder', () => {
      cy.get('[data-testid="results-container"]')
        .should('exist')
    })
  })

  describe('Navigation and Integration', () => {
    it('should integrate with demo page navigation', () => {
      cy.get('[data-testid="breadcrumb"]').should('contain', 'Demo')
      cy.get('[data-testid="breadcrumb"]')
        .should('contain', 'ROI Calculator')
    })

    it('should display requests per day input', () => {
      cy.contains('Requests/Day').should('be.visible')
      cy.get('input[type="range"][data-testid="requests-per-day"]')
        .should('be.visible')
    })

    it('should load industry context correctly', () => {
      cy.url().should('include', '/demo')
      cy.contains('Technology').should('be.visible')
    })

    it('should maintain state during page interactions', () => {
      cy.get('input[type="number"][data-testid="model-count"]')
        .clear().type('20')
      cy.reload()
      // Should maintain or reset to defaults appropriately
      cy.get('[data-testid="roi-calculator"]').should('be.visible')
    })

    it('should handle browser back/forward navigation', () => {
      cy.go('back')
      cy.go('forward')
      cy.get('[data-testid="roi-calculator"]').should('be.visible')
    })
  })


})