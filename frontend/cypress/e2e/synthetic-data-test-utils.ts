/// <reference types="cypress" />

/**
 * Shared test utilities and factories for synthetic data generator tests
 * Business Value: Enables faster test development and maintenance
 */

export class SyntheticDataTestUtils {
  static setupViewport(): void {
    cy.viewport(1920, 1080)
  }

  static visitComponent(): void {
    cy.visit('/synthetic-data-generation')
    cy.wait(500)
  }

  static getGenerator(): Cypress.Chainable {
    return cy.get('[data-testid="synthetic-data-generator"]')
  }

  static getGenerateButton(): Cypress.Chainable {
    return cy.get('[data-testid="generate-btn"]')
  }
}

export class ConfigurationFactory {
  static setTraceCount(count: number): void {
    cy.get('input[name="traceCount"]').clear().type(count.toString())
  }

  static setUserCount(count: number): void {
    cy.get('input[name="userCount"]').clear().type(count.toString())
  }

  static setErrorRate(rate: number): void {
    cy.get('input[type="range"][name="errorRate"]').invoke('val', rate).trigger('input')
  }

  static setWorkloadPattern(pattern: string): void {
    cy.get('select[name="workloadPattern"]').select(pattern)
  }
}

export class GenerationActions {
  static startGeneration(): void {
    SyntheticDataTestUtils.getGenerateButton().click()
  }

  static waitForCompletion(timeout = 3000): void {
    cy.wait(timeout)
    cy.contains('Generation Complete').should('be.visible')
  }

  static cancelGeneration(): void {
    cy.get('[data-testid="cancel-btn"]').click()
  }

  static verifyProgress(): void {
    cy.get('[data-testid="progress-bar"]').should('be.visible')
    cy.get('[data-testid="progress-percent"]').should('contain', '%')
  }
}

export class ValidationHelpers {
  static runValidation(): void {
    cy.get('[data-testid="validate-btn"]').click()
    cy.wait(2000)
  }

  static verifyValidationComplete(): void {
    cy.contains('Validation Complete').should('be.visible')
  }

  static checkValidationResults(): void {
    cy.contains('Schema Compliance').should('be.visible')
    cy.contains('Data Integrity').should('be.visible')
    cy.contains('Range Validation').should('be.visible')
  }
}

export class ExportActions {
  static openExportMenu(): void {
    cy.get('[data-testid="export-menu"]').click()
  }

  static exportAsFormat(format: 'CSV' | 'JSON' | 'Parquet'): void {
    this.openExportMenu()
    cy.contains(format).click()
  }

  static verifyExportFile(filename: string): void {
    cy.readFile(`cypress/downloads/${filename}`).should('exist')
  }

  static copyToClipboard(): void {
    cy.get('[data-testid="copy-data"]').click()
    cy.contains('Copied to clipboard').should('be.visible')
  }
}

export class UIHelpers {
  static verifyElementVisible(testId: string): void {
    cy.get(`[data-testid="${testId}"]`).should('be.visible')
  }

  static verifyTextContent(text: string): void {
    cy.contains(text).should('be.visible')
  }

  static clickElement(testId: string): void {
    cy.get(`[data-testid="${testId}"]`).click()
  }

  static typeInField(name: string, value: string): void {
    cy.get(`input[name="${name}"]`).clear().type(value)
  }
}

export const TestData = {
  defaultTraceCount: 1000,
  defaultUserCount: 100,
  smallDataset: 10,
  largeDataset: 100000,
  workloadPatterns: ['Steady', 'Burst', 'Growth', 'Periodic', 'Random', 'Custom'],
  exportFormats: ['CSV', 'JSON', 'Parquet'],
  presets: ['E-commerce', 'IoT Sensors', 'API Gateway']
} as const

export const Selectors = {
  generator: '[data-testid="synthetic-data-generator"]',
  generateBtn: '[data-testid="generate-btn"]',
  configSection: '[data-testid="config-section"]',
  outputSection: '[data-testid="output-section"]',
  progressBar: '[data-testid="progress-bar"]',
  previewTable: '[data-testid="preview-table"]',
  validateBtn: '[data-testid="validate-btn"]',
  exportMenu: '[data-testid="export-menu"]',
  advancedToggle: '[data-testid="advanced-toggle"]',
  presetSelector: '[data-testid="preset-selector"]'
} as const