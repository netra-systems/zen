/// <reference types="cypress" />

/**
 * Page Object for Synthetic Data Generation Page
 * Provides reusable selectors and actions for E2E tests
 * Business Value: Growth segment - validates data generation UI, improves user experience
 */

export class SyntheticDataPageObject {
  // Page selectors
  static readonly selectors = {
    // Main components
    page: '[data-testid="synthetic-data-generator"]',
    configPanel: 'text=Configuration',
    parametersPanel: 'text=Parameters',
    
    // Input fields
    tracesInput: 'input[name="traces"]',
    usersInput: 'input[name="users"]',
    errorRateInput: 'input[name="errorRate"]',
    errorRateSlider: 'input[type="range"][name="errorRate"]',
    
    // Tooltips
    tracesTooltip: '[data-testid="traces-tooltip"]',
    
    // Table management
    targetTableSelect: 'select[name="targetTable"]',
    newTableModal: '[data-testid="new-table-modal"]',
    tableNameInput: 'input[name="tableName"]',
    
    // Generation process
    generateButton: 'button:contains("Generate Data")',
    cancelButton: 'button:contains("Cancel")',
    progressBar: '[data-testid="progress-bar"]',
    progressPercentage: '[data-testid="progress-percentage"]',
    
    // Preview and validation
    previewTable: '[data-testid="data-preview-table"]',
    previewRow: '[data-testid="preview-row"]',
    previewLoading: '[data-testid="preview-loading"]',
    
    // Advanced options
    advancedOptions: 'text=Advanced Options',
    minLatencyInput: 'input[name="minLatency"]',
    maxLatencyInput: 'input[name="maxLatency"]',
    distributionSelect: 'select[name="distribution"]',
    serviceNameInput: 'input[name="serviceName"]',
    fieldNameInput: 'input[name="fieldName"]',
    fieldTypeSelect: 'select[name="fieldType"]',
    templateNameInput: 'input[name="templateName"]',
    
    // History
    historyTab: 'text=History',
    historyItem: '[data-testid="history-item"]',
    reuseConfigButton: '[data-testid="reuse-config"]',
    deleteHistoryButton: '[data-testid="delete-history"]',
    
    // Monitoring
    throughputMetric: '[data-testid="throughput-metric"]',
    memoryBar: '[data-testid="memory-bar"]',
    errorLog: '[data-testid="error-log"]',
    
    // Pattern preview
    patternPreview: '[data-testid="pattern-preview"]',
    burstIntensity: '[data-testid="burst-intensity"]',
    burstFrequency: '[data-testid="burst-frequency"]',
    
    // Code examples
    copyCodeButton: '[data-testid="copy-code"]'
  }

  // Navigation actions
  static visitPage(): void {
    cy.viewport(1920, 1080)
    cy.visit('/synthetic-data-generation')
  }

  static verifyPageLoad(): void {
    cy.url().should('include', '/synthetic-data-generation')
    cy.contains('Synthetic Data Generation').should('be.visible')
  }

  // Configuration actions
  static setTraceCount(count: string): void {
    cy.get(this.selectors.tracesInput).clear().type(count)
  }

  static setUserCount(count: string): void {
    cy.get(this.selectors.usersInput).clear().type(count)
  }

  static setErrorRate(rate: number): void {
    cy.get(this.selectors.errorRateSlider)
      .invoke('val', rate)
      .trigger('input')
  }

  // Pattern selection actions
  static selectWorkloadPattern(pattern: string): void {
    cy.contains(pattern).click()
  }

  static verifyPatternSelected(pattern: string): void {
    cy.contains(pattern).parent().should('have.class', 'ring-2')
  }

  // Table management actions
  static selectTable(tableName: string): void {
    cy.get(this.selectors.targetTableSelect).select(tableName)
  }

  static createNewTable(tableName: string): void {
    cy.contains('Create New Table').click()
    cy.get(this.selectors.tableNameInput).type(tableName)
    cy.contains('button', 'Create').click()
  }

  // Generation actions
  static startGeneration(): void {
    cy.contains('button', 'Generate Data').click()
  }

  static cancelGeneration(): void {
    cy.contains('button', 'Cancel').click()
  }

  static waitForCompletion(timeout = 5000): void {
    cy.wait(timeout)
    cy.contains('Generation Complete').should('be.visible')
  }

  // Export actions
  static exportAsCSV(): void {
    cy.contains('Export as CSV').click()
  }

  static exportAsJSON(): void {
    cy.contains('Export as JSON').click()
  }

  static copyToClipboard(): void {
    cy.contains('Copy to Clipboard').click()
  }

  // Advanced configuration actions
  static openAdvancedOptions(): void {
    cy.contains('Advanced Options').click()
  }

  static setLatencyRange(min: string, max: string): void {
    cy.get(this.selectors.minLatencyInput).type(min)
    cy.get(this.selectors.maxLatencyInput).type(max)
  }

  static addServiceName(serviceName: string): void {
    cy.get(this.selectors.serviceNameInput).type(serviceName)
    cy.contains('button', 'Add Service').click()
  }

  static addCustomField(name: string, type: string): void {
    cy.contains('Add Custom Field').click()
    cy.get(this.selectors.fieldNameInput).type(name)
    cy.get(this.selectors.fieldTypeSelect).select(type)
    cy.contains('button', 'Add Field').click()
  }

  static saveTemplate(templateName: string): void {
    cy.contains('Save as Template').click()
    cy.get(this.selectors.templateNameInput).type(templateName)
    cy.contains('button', 'Save').click()
  }

  // History actions
  static openHistory(): void {
    cy.contains('History').click()
  }

  static reuseFirstConfig(): void {
    cy.get(this.selectors.reuseConfigButton).first().click()
  }

  static deleteFirstHistoryItem(): void {
    cy.get(this.selectors.deleteHistoryButton).first().click()
    cy.contains('Confirm Delete').click()
  }

  // Validation utilities
  static verifyDefaultValues(): void {
    cy.get(this.selectors.tracesInput).should('have.value', '1000')
    cy.get(this.selectors.usersInput).should('have.value', '100')
    cy.get(this.selectors.errorRateInput).should('have.value', '5')
  }

  static verifyGenerationInProgress(): void {
    cy.contains('Generating').should('be.visible')
    cy.get(this.selectors.progressBar).should('be.visible')
  }

  static verifyPreviewData(): void {
    cy.get(this.selectors.previewRow).should('have.length.at.least', 5)
  }

  // Accessibility utilities
  static verifyAccessibility(): void {
    cy.get('[aria-label]').should('have.length.at.least', 10)
    cy.get('[role="status"]').should('exist')
  }

  // Mobile utilities
  static setMobileViewport(): void {
    cy.viewport('iphone-x')
  }

  static verifyMobileLayout(): void {
    cy.get(this.selectors.tracesInput).should('have.css', 'width', '100%')
  }

  // Error handling utilities
  static simulateNetworkError(): void {
    cy.intercept('POST', '/api/synthetic-data/generate', { statusCode: 500 })
  }

  static simulateTimeout(): void {
    cy.intercept('POST', '/api/synthetic-data/generate', (req) => {
      req.reply((res) => {
        res.delay(30000)
        res.send({ success: true })
      })
    })
  }

  static simulateInvalidResponse(): void {
    cy.intercept('POST', '/api/synthetic-data/generate', { body: null })
  }
}

// Export workload patterns for reuse
export const WORKLOAD_PATTERNS = [
  'Steady', 'Burst', 'Growth', 'Periodic', 'Random'
] as const

// Export table options for reuse
export const TABLE_OPTIONS = [
  'traces_synthetic', 'metrics_synthetic', 'logs_synthetic'
] as const

// Export validation messages for reuse
export const VALIDATION_MESSAGES = {
  mustBePositive: 'Must be positive',
  invalidTableName: 'Invalid table name',
  exceedsMaxLimit: 'Exceeds maximum limit',
  highResourceUsage: 'High resource usage',
  largeDatasetWarning: 'Large dataset warning'
} as const