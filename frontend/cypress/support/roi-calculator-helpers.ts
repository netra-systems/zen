/// <reference types="cypress" />

// ROI Calculator Test Helper Utilities
// Supports Enterprise segment value demonstration and sales conversion
// Modular design following 450-line limit and 25-line function requirements

export class ROICalculatorHelpers {
  // Navigation and setup helpers
  static navigateToCalculator() {
    cy.viewport(1920, 1080)
    cy.visit('/demo')
    cy.contains('Technology').click()
    cy.contains('ROI Calculator').click()
    cy.wait(500)
  }

  static navigateToIndustry(industry: string) {
    cy.visit('/demo')
    cy.contains(industry).click()
    cy.contains('ROI Calculator').click()
    cy.wait(500)
  }

  // Input interaction helpers - Updated for current SUT
  static setMonthlySpend(amount: number) {
    cy.get('input[id="spend"]')
      .clear()
      .type(amount.toString())
  }

  static setMonthlyRequests(requests: number) {
    cy.get('input[id="requests"]')
      .clear()
      .type(requests.toString())
  }

  static setTeamSize(size: number) {
    cy.get('input[id="team"]')
      .invoke('val', size)
      .trigger('input')
  }

  static setLatency(ms: number) {
    cy.get('input[id="latency"]')
      .invoke('val', ms)
      .trigger('input')
  }

  static setModelAccuracy(accuracy: number) {
    cy.get('input[id="accuracy"]')
      .invoke('val', accuracy)
      .trigger('input')
  }

  // Model type selection helpers
  static selectModelTypes(types: string[]) {
    types.forEach(type => {
      cy.get(`input[value="${type}"]`).check()
    })
  }

  static unselectAllModelTypes() {
    cy.get('input[type="checkbox"]:checked').uncheck()
  }

  // Calculation helpers
  static triggerCalculation() {
    cy.contains('button', 'Calculate ROI').click()
    cy.wait(3000)
  }

  static triggerCalculationAndWait() {
    cy.contains('button', 'Calculate ROI').click()
    cy.contains('Results').should('be.visible')
  }

  static recalculateWithNewValues() {
    cy.contains('Adjust Values').click()
    cy.contains('button', 'Recalculate').click()
    cy.wait(3000)
  }

  // Validation helpers
  static validateCalculationEnabled() {
    cy.contains('button', 'Calculate ROI')
      .should('not.be.disabled')
  }

  static validateCalculationDisabled() {
    cy.contains('button', 'Calculate ROI')
      .should('be.disabled')
  }

  static validateProgressIndicators() {
    cy.contains('Calculating').should('be.visible')
    cy.get('.animate-spin').should('exist')
    cy.get('[data-testid="calculation-progress"]')
      .should('be.visible')
  }

  // Results validation helpers
  static validateAllResults() {
    cy.contains('Monthly Savings').should('be.visible')
    cy.contains('Annual Savings').should('be.visible')
    cy.contains('ROI').should('be.visible')
    cy.contains('Payback Period').should('be.visible')
    cy.contains('3-Year TCO Reduction').should('be.visible')
  }

  // Breakdown validation helpers
  static validateSavingsBreakdown() {
    cy.contains('Savings Breakdown').should('be.visible')
    cy.contains('Infrastructure Optimization')
      .should('be.visible')
    cy.contains('Operational Efficiency')
      .should('be.visible')
  }

  static validatePerformanceGains() {
    cy.contains('Performance Gains').should('be.visible')
    cy.contains('Latency Reduction').should('be.visible')
    cy.contains(/\d+% faster/).should('be.visible')
  }

  static validateVisualChart() {
    cy.get('[data-testid="savings-chart"]')
      .should('be.visible')
    cy.get('svg').should('exist')
  }

  // Industry-specific validation helpers
  static validateIndustryMultiplier(industry: string) {
    const industryTexts = {
      Technology: 'Technology Optimization',
      Healthcare: 'Healthcare Compliance',
      'Financial Services': 'Financial Regulations'
    }
    
    const expectedText = industryTexts[industry as keyof typeof industryTexts]
    if (expectedText) {
      cy.contains(expectedText).should('be.visible')
    }
  }

  static validateIndustryBenefits() {
    cy.contains('Industry Benefits').should('be.visible')
    cy.get('[data-testid="industry-benefit"]')
      .should('have.length.at.least', 3)
  }

  // Export and sharing helpers
  static validateExportOptions() {
    cy.contains('Export Results').should('be.visible')
    cy.contains('Download PDF').should('be.visible')
    cy.contains('Export to Excel').should('be.visible')
  }

  // Comparison helpers
  static openComparisonView() {
    cy.contains('Compare with Alternatives').click()
  }

  static validateCompetitorComparison() {
    cy.contains('Competitor A').should('be.visible')
    cy.contains('Competitor B').should('be.visible')
    cy.contains('Netra Advantage').should('be.visible')
  }

  static validateComparisonMatrix() {
    cy.get('[data-testid="comparison-table"]')
      .should('be.visible')
    cy.contains('Multi-agent').should('be.visible')
    cy.contains('Real-time').should('be.visible')
  }

  // Error handling helpers
  static mockAPIError() {
    cy.intercept('POST', '/api/demo/roi', { statusCode: 500 })
  }

  static validateErrorFallback() {
    cy.contains('Using estimated values')
      .should('be.visible')
  }

  static validateGracefulDegradation() {
    cy.contains('Monthly Savings').should('be.visible')
    cy.contains(/\$[\d,]+/).should('be.visible')
  }

  // UI validation helpers
  static validateAccessibility() {
    cy.get('[aria-label="Monthly spend slider"]').should('exist')
    cy.get('[aria-label="Calculate ROI"]').should('exist')
    cy.get('label[for="monthly-spend"]').should('contain', 'Monthly')
  }

  static switchToMobileViewport() {
    cy.viewport('iphone-x')
  }

  // Performance helpers
  static validatePerformance() {
    const start = Date.now()
    cy.contains('button', 'Calculate ROI').click()
    cy.contains('Results').should('be.visible')
    cy.then(() => expect(Date.now() - start).to.be.lessThan(5000))
  }
}

// Common test data configurations
export const TestData = {
  defaultSpend: 50000,
  highSpend: 100000,
  lowSpend: 10000,
  defaultModels: 15,
  defaultLatency: 200,
  defaultHours: 160,
  defaultTeamSize: 8,
  defaultRequests: 1000000,
  
  modelTypes: ['llm', 'vision', 'embedding'],
  cloudProviders: ['AWS', 'Azure', 'GCP'],
  deploymentFrequencies: ['Daily', 'Weekly', 'Monthly'],
  industries: ['Technology', 'Healthcare', 'Financial Services']
}

// Assertion helpers for common validations
export const Assertions = {
  hasValidCurrency: (selector: string) => {
    cy.get(selector).should('match', /\$[\d,]+/)
  },
  
  hasValidPercentage: (selector: string) => {
    cy.get(selector).should('match', /\d+%/)
  },
  
  hasValidTimeframe: (selector: string) => {
    cy.get(selector).should('match', /\d+ months?/)
  },
  
  hasGreenIndicator: (selector: string) => {
    cy.get(selector).should('have.class', 'text-green-500')
  }
}