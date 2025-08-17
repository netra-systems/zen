/// <reference types="cypress" />

/**
 * Shared utilities for synthetic data e2e tests
 * Used across all synthetic data test modules
 */

export class SyntheticDataUtils {
  // Navigation utilities
  static navigateToDemo(): void {
    cy.visit('/demo')
    cy.wait(500)
  }

  static selectIndustry(industry: string): void {
    cy.contains(industry).click()
    cy.contains('Data Insights').click()
    cy.wait(500)
  }

  // Setup utilities
  static setupViewport(): void {
    cy.viewport(1920, 1080)
  }

  static setupEcommerce(): void {
    this.setupViewport()
    this.navigateToDemo()
    this.selectIndustry('E-commerce')
  }

  // Data generation utilities
  static generateData(): void {
    cy.contains('Generate').click()
    cy.wait(2000)
  }

  static generateMultiple(count: number): void {
    for (let i = 0; i < count; i++) {
      cy.contains('Generate').click()
      cy.wait(500)
    }
  }

  // Sample interaction utilities
  static selectFirstSample(): void {
    cy.get('.border').first().click()
  }

  static selectSampleByIndex(index: number): void {
    cy.get('.border').eq(index).click()
  }

  // Tab navigation utilities
  static switchToTab(tabName: string): void {
    cy.contains(tabName).click()
    cy.wait(300)
  }

  static switchToExplorer(): void {
    this.switchToTab('Data Explorer')
  }

  static switchToSchema(): void {
    this.switchToTab('Schema View')
  }

  // Validation utilities
  static validateJsonFormat(jsonText: string): void {
    expect(() => JSON.parse(jsonText)).to.not.throw()
  }

  static validateDataRange(value: number, min: number, max: number): void {
    expect(value).to.be.at.least(min)
    expect(value).to.be.at.most(max)
  }

  // Industry data validators
  static validateEcommerceFields(): void {
    cy.contains('session_id').should('be.visible')
    cy.contains('cart_value').should('be.visible')
    cy.contains('products_viewed').should('be.visible')
    cy.contains('recommendations').should('be.visible')
  }

  static validateHealthcareFields(): void {
    cy.contains('patient_id').should('be.visible')
    cy.contains('vital_signs').should('be.visible')
    cy.contains('diagnosis_code').should('be.visible')
  }

  static validateFinancialFields(): void {
    cy.contains('transaction_id').should('be.visible')
    cy.contains('risk_score').should('be.visible')
    cy.contains('fraud_probability').should('be.visible')
  }
}

export class SyntheticDataSelectors {
  static readonly generateButton = 'button:contains("Generate")'
  static readonly exportButton = 'button:contains("Export")'
  static readonly samples = '.border'
  static readonly jsonPreview = 'pre'
  static readonly copyButton = 'button:contains("Copy")'
  static readonly explorerSample = '[data-testid="explorer-sample"]'
  static readonly statTotalSamples = '[data-testid="stat-total-samples"]'
  static readonly statAvgProcessing = '[data-testid="stat-avg-processing"]'
  static readonly statDataPoints = '[data-testid="stat-data-points"]'
  static readonly statDataTypes = '[data-testid="stat-data-types"]'
  static readonly sampleTimestamp = '[data-testid="sample-timestamp"]'
}

export class SyntheticDataExpectations {
  static readonly maxSampleLimit = 15
  static readonly maxProcessingTime = 10000
  static readonly minProcessingTime = 0
  static readonly maxCartValue = 10000
  static readonly minCartValue = 0
  static readonly maxProductsViewed = 100
  static readonly minProductsViewed = 0
  static readonly maxDataTypes = 4
  static readonly minDataTypes = 1
}