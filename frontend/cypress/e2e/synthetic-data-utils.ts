/// <reference types="cypress" />

/**
 * Shared utilities for synthetic data e2e tests
 * Used across all synthetic data test modules
 */

export class SyntheticDataUtils {
  // Navigation utilities
  static navigateToDemo(): void {
    cy.visit('/demo')
    cy.wait(1000) // Increased wait time for component loading
  }

  static selectIndustry(industry: string): void {
    cy.contains(industry).click()
    cy.contains('Data Insights').click()
    cy.wait(1000) // Wait for SyntheticDataViewer to load
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
    cy.contains('button', 'Generate').click()
    cy.wait(2000) // Wait for generation animation to complete
  }

  static generateMultiple(count: number): void {
    for (let i = 0; i < count; i++) {
      cy.contains('button', 'Generate').click()
      cy.wait(1000) // Increased wait between generations
    }
  }

  // Sample interaction utilities
  static selectFirstSample(): void {
    cy.contains('Live Stream').click() // Ensure we're on the right tab
    cy.get('[class*="border"]').first().click()
  }

  static selectSampleByIndex(index: number): void {
    cy.contains('Live Stream').click()
    cy.get('[class*="border"]').eq(index).click()
  })

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
    // Updated to match actual e-commerce data structure
    cy.contains(/session_id|user_id|customer_id/).should('be.visible')
    cy.contains(/cart|product|purchase/).should('be.visible')
  })

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
  static readonly samples = '[class*="border"]' // Updated to match actual class patterns
  static readonly jsonPreview = 'pre, code' // Include both pre and code elements
  static readonly copyButton = 'button:contains("Copy")'
  static readonly liveStreamTab = 'button:contains("Live Stream")'
  static readonly explorerTab = 'button:contains("Data Explorer")'
  static readonly schemaTab = 'button:contains("Schema View")'
  static readonly statisticsCards = '[class*="card"]:contains("Total Samples")'  
}

export class SyntheticDataExpectations {
  static readonly maxSampleLimit = 10 // Updated to match component limit
  static readonly maxProcessingTime = 3000
  static readonly minProcessingTime = 0
  static readonly generationAnimationTime = 1500 // Time for generation animation
  static readonly tabSwitchDelay = 300
  static readonly sampleLoadDelay = 500
}