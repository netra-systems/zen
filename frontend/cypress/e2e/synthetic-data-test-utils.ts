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
    cy.wait(1000) // Increased wait for component loading
  }

  static getGenerator(): Cypress.Chainable {
    return cy.get('[class*="card"]') // Updated to match actual card class
  }

  static getGenerateButton(): Cypress.Chainable {
    return cy.contains('button', 'Generate Data')
  }
}

export class ConfigurationFactory {
  static setTraceCount(count: number): void {
    cy.get('input[name="num_traces"]').clear().type(count.toString())
  }

  static setUserCount(count: number): void {
    cy.get('input[name="num_users"]').clear().type(count.toString())
  }

  static setErrorRate(rate: number): void {
    cy.get('input[name="error_rate"]').clear().type(rate.toString())
  }

  static setWorkloadPattern(pattern: string): void {
    cy.get('button[role="combobox"]').click()
    cy.contains(pattern).click()
  }
}

export class GenerationActions {
  static startGeneration(): void {
    SyntheticDataTestUtils.getGenerateButton().click()
  }

  static waitForCompletion(timeout = 3000): void {
    cy.wait(timeout)
    // Generation completion is handled internally, no visible success message
    cy.contains('button', 'Generate Data').should('not.be.disabled')
  }

  static verifyGenerationInProgress(): void {
    cy.contains('button', 'Generating...').should('be.visible')
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
  defaultTraceCount: 100, // Updated to match actual defaults
  defaultUserCount: 10,
  defaultErrorRate: 0.1,
  smallDataset: 10,
  largeDataset: 10000,
  workloadPatterns: ['Default Workload', 'Cost-Sensitive', 'Latency-Sensitive', 'High Error Rate'],
  eventTypes: 'search,login',
  destinationTable: 'default.synthetic_data_'
} as const

export const Selectors = {
  generator: '[class*="card"]',
  generateBtn: 'button:contains("Generate Data")',
  tracesInput: 'input[name="num_traces"]',
  usersInput: 'input[name="num_users"]',
  errorRateInput: 'input[name="error_rate"]',
  workloadSelect: 'button[role="combobox"]',
  eventTypesInput: 'input[name="event_types"]',
  sourceTableSelect: 'button[role="combobox"]',
  errorAlert: '[class*="alert"]'
} as const