/// <reference types="cypress" />
import { 
  SyntheticDataPageObject, 
  VALIDATION_MESSAGES 
} from './utils/synthetic-data-page-object'

/**
 * Generation Workflow Tests for Synthetic Data Generation Page
 * Tests: Data generation process, preview, validation, and export
 * Business Value: Growth segment - validates data generation workflow and export capabilities
 */

describe('Synthetic Data Generation - Workflow', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/synthetic-data-generation')
    cy.wait(1000)
  })

  describe('Data Generation Process', () => {
    it('should start generation on button click', () => {
      cy.contains('button', 'Generate Data').click()
      cy.contains('Generating...').should('be.visible')
    })

    it('should disable button during generation', () => {
      cy.contains('button', 'Generate Data').click()
      cy.contains('button', 'Generating...').should('be.disabled')
    })

    it('should display estimated time', () => {
      SyntheticDataPageObject.startGeneration()
      cy.contains('Estimated time').should('be.visible')
      cy.contains(/\d+ seconds?/).should('be.visible')
    })

    it('should show completion message', () => {
      SyntheticDataPageObject.startGeneration()
      SyntheticDataPageObject.waitForCompletion()
      cy.contains('1000 traces generated').should('be.visible')
    })

    it('should allow canceling generation', () => {
      SyntheticDataPageObject.startGeneration()
      cy.get(SyntheticDataPageObject.selectors.cancelButton)
        .should('be.visible')
      SyntheticDataPageObject.cancelGeneration()
      cy.contains('Generation Cancelled').should('be.visible')
    })

    it('should handle generation with custom parameters', () => {
      SyntheticDataPageObject.setTraceCount('2000')
      SyntheticDataPageObject.setUserCount('200')
      SyntheticDataPageObject.selectWorkloadPattern('Burst')
      SyntheticDataPageObject.startGeneration()
      SyntheticDataPageObject.verifyGenerationInProgress()
    })

    it('should update generation status in real-time', () => {
      SyntheticDataPageObject.startGeneration()
      cy.contains('Initializing').should('be.visible')
      cy.contains('Generating').should('be.visible')
    })

    it('should display generation metrics', () => {
      SyntheticDataPageObject.startGeneration()
      cy.contains('Records/sec').should('be.visible')
      cy.get(SyntheticDataPageObject.selectors.throughputMetric)
        .should('contain', /\d+/)
    })
  })

  describe('Preview and Validation', () => {
    beforeEach(() => {
      SyntheticDataPageObject.startGeneration()
      cy.wait(3000) // Wait for generation to complete
    })

    it('should show data preview section', () => {
      cy.contains('Data Preview').should('be.visible')
      cy.get(SyntheticDataPageObject.selectors.previewTable)
        .should('be.visible')
    })

    it('should display sample records after generation', () => {
      SyntheticDataPageObject.verifyPreviewData()
    })

    it('should show data statistics', () => {
      cy.contains('Statistics').should('be.visible')
      cy.contains('Total Records').should('be.visible')
      cy.contains('Average Latency').should('be.visible')
      cy.contains('Error Count').should('be.visible')
    })

    it('should allow refreshing preview', () => {
      cy.contains('button', 'Refresh Preview').click()
      cy.get(SyntheticDataPageObject.selectors.previewLoading)
        .should('be.visible')
    })

    it('should validate generated data format', () => {
      cy.contains('Validate Data').click()
      cy.contains('Validation Successful').should('be.visible')
    })

    it('should show detailed record information', () => {
      cy.get(SyntheticDataPageObject.selectors.previewRow)
        .first()
        .click()
      cy.contains('Record Details').should('be.visible')
      cy.contains('trace_id').should('be.visible')
      cy.contains('timestamp').should('be.visible')
    })

    it('should filter preview data by criteria', () => {
      cy.contains('Filter Results').click()
      cy.get('input[name="statusFilter"]').select('error')
      cy.contains('Apply Filter').click()
      cy.get(SyntheticDataPageObject.selectors.previewRow)
        .should('contain', 'error')
    })

    it('should sort preview data by columns', () => {
      cy.contains('timestamp').click()
      cy.get(SyntheticDataPageObject.selectors.previewRow)
        .first()
        .should('be.visible')
    })
  })

  describe('Export and Download', () => {
    beforeEach(() => {
      SyntheticDataPageObject.startGeneration()
      cy.wait(3000) // Wait for generation to complete
    })

    it('should show export options after generation', () => {
      cy.contains('Export Options').should('be.visible')
    })

    it('should allow exporting as CSV', () => {
      SyntheticDataPageObject.exportAsCSV()
      cy.readFile('cypress/downloads/synthetic_data.csv').should('exist')
    })

    it('should allow exporting as JSON', () => {
      SyntheticDataPageObject.exportAsJSON()
      cy.readFile('cypress/downloads/synthetic_data.json').should('exist')
    })

    it('should allow copying to clipboard', () => {
      SyntheticDataPageObject.copyToClipboard()
      cy.contains('Copied!').should('be.visible')
    })

    it('should show export size warning for large datasets', () => {
      cy.visit('/synthetic-data-generation')
      SyntheticDataPageObject.setTraceCount('100000')
      SyntheticDataPageObject.startGeneration()
      cy.wait(3000)
      SyntheticDataPageObject.exportAsCSV()
      cy.contains(VALIDATION_MESSAGES.largeDatasetWarning)
        .should('be.visible')
    })

    it('should provide export format options', () => {
      cy.contains('Export Format').should('be.visible')
      cy.contains('CSV').should('be.visible')
      cy.contains('JSON').should('be.visible')
      cy.contains('Parquet').should('be.visible')
    })

    it('should allow selecting specific fields for export', () => {
      cy.contains('Select Fields').click()
      cy.get('input[name="trace_id"]').uncheck()
      cy.get('input[name="timestamp"]').should('be.checked')
      cy.contains('Export Selected').click()
    })

    it('should show export progress for large files', () => {
      SyntheticDataPageObject.setTraceCount('50000')
      SyntheticDataPageObject.startGeneration()
      cy.wait(3000)
      SyntheticDataPageObject.exportAsCSV()
      cy.contains('Preparing export').should('be.visible')
    })
  })

  describe('Generation Error Handling', () => {
    it('should handle network errors gracefully', () => {
      SyntheticDataPageObject.simulateNetworkError()
      SyntheticDataPageObject.startGeneration()
      cy.contains('Generation failed').should('be.visible')
      cy.contains('Retry').should('be.visible')
    })

    it('should timeout long-running generations', () => {
      SyntheticDataPageObject.simulateTimeout()
      SyntheticDataPageObject.startGeneration()
      cy.wait(10000)
      cy.contains('Generation timed out').should('be.visible')
    })

    it('should handle invalid server responses', () => {
      SyntheticDataPageObject.simulateInvalidResponse()
      SyntheticDataPageObject.startGeneration()
      cy.contains('Invalid response').should('be.visible')
    })

    it('should display error log if generation fails', () => {
      SyntheticDataPageObject.setTraceCount('999999999')
      SyntheticDataPageObject.startGeneration()
      cy.wait(2000)
      cy.contains('Error').should('be.visible')
      cy.get(SyntheticDataPageObject.selectors.errorLog)
        .should('be.visible')
    })

    it('should show warning for high resource usage', () => {
      SyntheticDataPageObject.setTraceCount('50000')
      SyntheticDataPageObject.startGeneration()
      cy.contains(VALIDATION_MESSAGES.highResourceUsage)
        .should('be.visible')
    })

    it('should allow retrying failed generations', () => {
      SyntheticDataPageObject.simulateNetworkError()
      SyntheticDataPageObject.startGeneration()
      cy.contains('Retry').click()
      cy.intercept('POST', '/api/synthetic-data/generate', 
        { success: true })
      SyntheticDataPageObject.verifyGenerationInProgress()
    })
  })

  describe('Workflow Integration', () => {
    it('should integrate with demo chat', () => {
      SyntheticDataPageObject.startGeneration()
      cy.wait(3000)
      cy.contains('Use in Demo').should('be.visible')
      cy.contains('Use in Demo').click()
      cy.url().should('include', '/demo')
    })

    it('should provide API endpoint information', () => {
      cy.contains('API Integration').click()
      cy.contains('/api/synthetic-data').should('be.visible')
      cy.contains('POST').should('be.visible')
    })

    it('should show code examples', () => {
      cy.contains('Code Examples').click()
      cy.contains('Python').should('be.visible')
      cy.contains('JavaScript').should('be.visible')
      cy.contains('curl').should('be.visible')
    })

    it('should copy code snippets', () => {
      cy.contains('Code Examples').click()
      cy.contains('Python').click()
      cy.get(SyntheticDataPageObject.selectors.copyCodeButton).click()
      cy.contains('Copied').should('be.visible')
    })

    it('should maintain state across workflow steps', () => {
      SyntheticDataPageObject.setTraceCount('3000')
      SyntheticDataPageObject.startGeneration()
      cy.wait(3000)
      cy.contains('Code Examples').click()
      cy.go('back')
      cy.get(SyntheticDataPageObject.selectors.tracesInput)
        .should('have.value', '3000')
    })
  })

  describe('Generation Performance', () => {
    it('should handle rapid successive generations', () => {
      SyntheticDataPageObject.setTraceCount('100')
      SyntheticDataPageObject.startGeneration()
      cy.wait(1000)
      SyntheticDataPageObject.cancelGeneration()
      SyntheticDataPageObject.startGeneration()
      SyntheticDataPageObject.verifyGenerationInProgress()
    })

    it('should show memory usage indicator', () => {
      SyntheticDataPageObject.startGeneration()
      cy.contains('Memory Usage').should('be.visible')
      cy.get(SyntheticDataPageObject.selectors.memoryBar)
        .should('be.visible')
    })

    it('should optimize for different data sizes', () => {
      SyntheticDataPageObject.setTraceCount('10')
      SyntheticDataPageObject.startGeneration()
      cy.contains('Quick generation').should('be.visible')
      
      SyntheticDataPageObject.setTraceCount('10000')
      SyntheticDataPageObject.startGeneration()
      cy.contains('Batch processing').should('be.visible')
    })
  })
})