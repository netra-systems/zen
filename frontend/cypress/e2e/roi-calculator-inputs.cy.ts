/// <reference types="cypress" />

import { ROICalculatorHelpers, TestData } from '../support/roi-calculator-helpers'

// ROI Calculator Input Validation Tests
// BVJ: Enterprise segment - validates input accuracy for decision maker confidence
// Modular design following 300-line limit and 8-line function requirements

describe('ROI Calculator Input Validation Tests', () => {
  beforeEach(() => {
    ROICalculatorHelpers.navigateToCalculator()
  })

  describe('Infrastructure Metrics Inputs', () => {
    it('should display monthly spend slider', () => {
      cy.contains('Current Monthly AI Spend').should('be.visible')
      cy.get('input[type="range"][data-testid="monthly-spend"]')
        .should('be.visible')
    })

    it('should update spend value on slider change', () => {
      ROICalculatorHelpers.setMonthlySpend(75000)
      cy.contains('$75,000').should('be.visible')
    })

    it('should display number of models input', () => {
      cy.contains('Number of AI Models').should('be.visible')
      cy.get('input[type="number"][data-testid="model-count"]')
        .should('be.visible')
    })

    it('should update model count', () => {
      ROICalculatorHelpers.setModelCount(25)
      cy.get('input[type="number"][data-testid="model-count"]')
        .should('have.value', '25')
    })

    it('should display average latency slider', () => {
      cy.contains('Average Latency').should('be.visible')
      cy.get('input[type="range"][data-testid="latency"]')
        .should('be.visible')
    })

    it('should show latency in milliseconds', () => {
      ROICalculatorHelpers.setLatency(250)
      cy.contains('250ms').should('be.visible')
    })

  })

  describe('Operational Metrics Inputs', () => {
    it('should display engineering hours slider', () => {
      cy.contains('Engineering Hours/Month').should('be.visible')
      cy.get('input[type="range"][data-testid="engineering-hours"]')
        .should('be.visible')
    })

    it('should update engineering hours', () => {
      ROICalculatorHelpers.setEngineeringHours(200)
      cy.contains('200 hours').should('be.visible')
    })

    it('should display team size input', () => {
      cy.contains('Team Size').should('be.visible')
      cy.get('input[type="number"][data-testid="team-size"]')
        .should('be.visible')
    })

    it('should validate team size input', () => {
      ROICalculatorHelpers.setTeamSize(0)
      cy.contains('Minimum 1').should('be.visible')
    })

    it('should display deployment frequency', () => {
      cy.contains('Deployment Frequency').should('be.visible')
      cy.get('select[data-testid="deployment-frequency"]')
        .should('be.visible')
    })

    it('should allow selecting deployment frequency', () => {
      ROICalculatorHelpers.selectDeploymentFrequency('Daily')
      cy.get('select[data-testid="deployment-frequency"]')
        .should('have.value', 'daily')
    })

  })

  describe('AI Workload Details', () => {
    it('should display requests per day slider', () => {
      cy.contains('Requests/Day').should('be.visible')
      cy.get('input[type="range"][data-testid="requests-per-day"]')
        .should('be.visible')
    })

    it('should format large request numbers', () => {
      ROICalculatorHelpers.setRequestsPerDay(5000000)
      cy.contains('5M').should('be.visible')
    })

    it('should display model types selection', () => {
      cy.contains('Model Types').should('be.visible')
      cy.get('[data-testid="model-type-checkbox"]')
        .should('have.length.at.least', 3)
    })

    it('should allow selecting multiple model types', () => {
      ROICalculatorHelpers.selectModelTypes(TestData.modelTypes)
      cy.get('input:checked').should('have.length', 3)
    })

    it('should display cloud provider selection', () => {
      cy.contains('Cloud Provider').should('be.visible')
      cy.get('select[data-testid="cloud-provider"]')
        .should('be.visible')
    })

    it('should show provider-specific optimizations', () => {
      ROICalculatorHelpers.selectCloudProvider('AWS')
      cy.contains('AWS optimization').should('be.visible')
    })

    it('should validate requests per day formatting', () => {
      ROICalculatorHelpers.setRequestsPerDay(1500000)
      cy.contains('1.5M').should('be.visible')
    })

    it('should handle model type deselection', () => {
      ROICalculatorHelpers.selectModelTypes(['llm', 'vision'])
      cy.get('input[value="llm"]').uncheck()
      cy.get('input:checked').should('have.length', 1)
    })
  })

  describe('Input Validation and Error Handling', () => {
    it('should validate minimum spend', () => {
      ROICalculatorHelpers.setMonthlySpend(0)
      ROICalculatorHelpers.validateCalculationDisabled()
      cy.contains('Minimum spend required').should('be.visible')
    })

    it('should validate model count', () => {
      cy.get('input[type="number"][data-testid="model-count"]')
        .clear()
        .type('-5')
      cy.contains('Invalid model count').should('be.visible')
    })

    it('should require at least one model type', () => {
      ROICalculatorHelpers.unselectAllModelTypes()
      cy.contains('button', 'Calculate ROI').click()
      cy.contains('Select at least one model type')
        .should('be.visible')
    })

    it('should handle API errors gracefully', () => {
      ROICalculatorHelpers.mockAPIError()
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(2000)
      ROICalculatorHelpers.validateErrorFallback()
    })

    it('should show fallback calculations on error', () => {
      ROICalculatorHelpers.mockAPIError()
      cy.contains('button', 'Calculate ROI').click()
      cy.wait(3000)
      ROICalculatorHelpers.validateGracefulDegradation()
    })

    it('should validate team size minimum', () => {
      ROICalculatorHelpers.setTeamSize(-1)
      cy.contains('Team size must be positive')
        .should('be.visible')
    })

    it('should handle large numeric inputs', () => {
      ROICalculatorHelpers.setModelCount(9999)
      cy.get('input[type="number"][data-testid="model-count"]')
        .should('have.value', '9999')
    })

    it('should validate cloud provider selection', () => {
      ROICalculatorHelpers.selectCloudProvider('Azure')
      cy.get('select[data-testid="cloud-provider"]')
        .should('have.value', 'azure')
    })
  })

  describe('Input Interaction Flows', () => {
    it('should maintain state across input changes', () => {
      ROICalculatorHelpers.setMonthlySpend(TestData.defaultSpend)
      ROICalculatorHelpers.setModelCount(TestData.defaultModels)
      ROICalculatorHelpers.setLatency(TestData.defaultLatency)
      
      cy.contains(`$${TestData.defaultSpend.toLocaleString()}`)
        .should('be.visible')
      cy.get('input[type="number"][data-testid="model-count"]')
        .should('have.value', TestData.defaultModels.toString())
    })

    it('should enable calculation with valid inputs', () => {
      ROICalculatorHelpers.setMonthlySpend(TestData.defaultSpend)
      ROICalculatorHelpers.setModelCount(TestData.defaultModels)
      ROICalculatorHelpers.selectModelTypes(['llm'])
      
      ROICalculatorHelpers.validateCalculationEnabled()
    })

    it('should update display values in real-time', () => {
      ROICalculatorHelpers.setMonthlySpend(75000)
      cy.contains('$75,000').should('be.visible')
      
      ROICalculatorHelpers.setLatency(300)
      cy.contains('300ms').should('be.visible')
    })

    it('should handle rapid input changes', () => {
      for(let i = 1; i <= 5; i++) {
        ROICalculatorHelpers.setModelCount(i * 5)
        cy.get('input[type="number"][data-testid="model-count"]')
          .should('have.value', (i * 5).toString())
      }
    })

    it('should validate input combinations', () => {
      ROICalculatorHelpers.setMonthlySpend(TestData.lowSpend)
      ROICalculatorHelpers.setModelCount(1)
      ROICalculatorHelpers.selectModelTypes(['llm'])
      
      ROICalculatorHelpers.validateCalculationEnabled()
    })

    it('should show tooltips for input guidance', () => {
      cy.get('[data-testid="info-icon"]').first()
        .trigger('mouseenter')
      cy.contains('This represents').should('be.visible')
    })

    it('should handle form reset functionality', () => {
      ROICalculatorHelpers.setMonthlySpend(TestData.highSpend)
      ROICalculatorHelpers.setModelCount(TestData.defaultModels)
      
      cy.contains('Reset Form').click()
      cy.get('input[type="number"][data-testid="model-count"]')
        .should('have.value', '15')
    })

    it('should validate input field focus states', () => {
      cy.get('input[type="number"][data-testid="model-count"]').focus()
      cy.focused().should('have.attr', 'data-testid', 'model-count')
    })
  })

})