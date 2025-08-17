/// <reference types="cypress" />

import { 
  SyntheticDataTestUtils, 
  ConfigurationFactory, 
  GenerationActions, 
  ValidationHelpers, 
  ExportActions, 
  UIHelpers, 
  TestData, 
  Selectors 
} from './synthetic-data-test-utils'

/**
 * Output display and validation tests for synthetic data generator
 * BVJ: Growth segment - ensures data quality and export capabilities for customer value
 */
describe('SyntheticDataGenerator - Output and Validation Tests', () => {
  beforeEach(() => {
    SyntheticDataTestUtils.setupViewport()
    SyntheticDataTestUtils.visitComponent()
    setupGeneratedData()
  })

  function setupGeneratedData(): void {
    ConfigurationFactory.setTraceCount(TestData.smallDataset)
    GenerationActions.startGeneration()
    GenerationActions.waitForCompletion()
  }

  describe('Output Display', () => {
    it('should display output section after generation', () => {
      UIHelpers.verifyElementVisible('output-section')
    })

    it('should show data preview table', () => {
      UIHelpers.verifyElementVisible('preview-table')
      cy.get('[data-testid="preview-row"]').should('have.length.at.least', 5)
    })

    it('should display proper column headers', () => {
      cy.contains('th', 'Trace ID').should('be.visible')
      cy.contains('th', 'Timestamp').should('be.visible')
      cy.contains('th', 'Duration').should('be.visible')
      cy.contains('th', 'Status').should('be.visible')
    })

    it('should show generated data statistics', () => {
      UIHelpers.verifyTextContent('Statistics')
      UIHelpers.verifyTextContent('Total Records')
      UIHelpers.verifyTextContent('Success Rate')
      UIHelpers.verifyTextContent('Avg Duration')
    })

    it('should support data preview pagination', () => {
      UIHelpers.clickElement('next-page')
      cy.get('[data-testid="page-indicator"]').should('contain', '2')
    })

    it('should allow refreshing preview data', () => {
      UIHelpers.clickElement('refresh-preview')
      UIHelpers.verifyElementVisible('preview-loading')
    })
  })

  describe('Data Validation Functions', () => {
    it('should display validation button', () => {
      UIHelpers.verifyElementVisible('validate-btn')
    })

    it('should start validation process', () => {
      ValidationHelpers.runValidation()
      UIHelpers.verifyTextContent('Validating')
    })

    it('should complete validation successfully', () => {
      ValidationHelpers.runValidation()
      ValidationHelpers.verifyValidationComplete()
    })

    it('should display validation check results', () => {
      ValidationHelpers.runValidation()
      ValidationHelpers.checkValidationResults()
    })

    it('should show validation warnings with high error rate', () => {
      ConfigurationFactory.setErrorRate(100)
      GenerationActions.startGeneration()
      GenerationActions.waitForCompletion()
      ValidationHelpers.runValidation()
      UIHelpers.verifyTextContent('Warning')
    })
  })

  describe('Export Functionality', () => {
    it('should display export options menu', () => {
      ExportActions.openExportMenu()
      TestData.exportFormats.forEach(format => {
        UIHelpers.verifyTextContent(format)
      })
    })

    it('should export data as CSV format', () => {
      ExportActions.exportAsFormat('CSV')
      ExportActions.verifyExportFile('synthetic_data.csv')
    })

    it('should export data as JSON format', () => {
      ExportActions.exportAsFormat('JSON')
      ExportActions.verifyExportFile('synthetic_data.json')
    })

    it('should show export progress indicator', () => {
      ExportActions.openExportMenu()
      cy.contains('CSV').click()
      UIHelpers.verifyTextContent('Exporting')
    })

    it('should copy data to clipboard', () => {
      ExportActions.copyToClipboard()
    })
  })

  describe('Data Quality Validation', () => {
    it('should validate schema compliance', () => {
      ValidationHelpers.runValidation()
      UIHelpers.verifyTextContent('Schema Compliance')
      cy.get('[data-testid="schema-check"]').should('contain', 'Passed')
    })

    it('should check data integrity', () => {
      ValidationHelpers.runValidation()
      UIHelpers.verifyTextContent('Data Integrity')
      cy.get('[data-testid="integrity-check"]').should('contain', 'Passed')
    })

    it('should validate value ranges', () => {
      ValidationHelpers.runValidation()
      UIHelpers.verifyTextContent('Range Validation')
      cy.get('[data-testid="range-check"]').should('contain', 'Passed')
    })

    it('should detect data anomalies', () => {
      ValidationHelpers.runValidation()
      cy.get('[data-testid="anomaly-count"]').should('contain', /\d+/)
    })

    it('should validate timestamp ordering', () => {
      ValidationHelpers.runValidation()
      cy.get('[data-testid="timestamp-validation"]').should('contain', 'Valid')
    })

    it('should check for duplicate records', () => {
      ValidationHelpers.runValidation()
      cy.get('[data-testid="duplicate-check"]').should('contain', 'No duplicates')
    })
  })

  describe('Data Statistics and Metrics', () => {
    it('should display record count statistics', () => {
      cy.get('[data-testid="total-records"]').should('contain', TestData.smallDataset.toString())
    })

    it('should show success rate percentage', () => {
      cy.get('[data-testid="success-rate"]').should('contain', '%')
    })

    it('should display average duration metrics', () => {
      cy.get('[data-testid="avg-duration"]').should('contain', 'ms')
    })

    it('should show min and max duration values', () => {
      UIHelpers.verifyTextContent('Min Duration')
      UIHelpers.verifyTextContent('Max Duration')
    })

    it('should display error distribution', () => {
      UIHelpers.verifyTextContent('Error Distribution')
      cy.get('[data-testid="error-chart"]').should('be.visible')
    })

    it('should show throughput statistics', () => {
      UIHelpers.verifyTextContent('Throughput')
      cy.get('[data-testid="throughput-value"]').should('contain', 'req/s')
    })
  })

  describe('Preview Table Interactions', () => {
    it('should sort table by column headers', () => {
      cy.contains('th', 'Duration').click()
      cy.get('[data-testid="sort-indicator"]').should('be.visible')
    })

    it('should filter data in preview table', () => {
      cy.get('[data-testid="filter-input"]').type('error')
      cy.get('[data-testid="preview-row"]').should('contain', 'error')
    })

    it('should show row details on click', () => {
      cy.get('[data-testid="preview-row"]').first().click()
      UIHelpers.verifyElementVisible('row-details-modal')
    })

    it('should select multiple rows', () => {
      cy.get('[data-testid="row-checkbox"]').first().click()
      cy.get('[data-testid="row-checkbox"]').eq(1).click()
      cy.get('[data-testid="selected-count"]').should('contain', '2')
    })

    it('should export selected rows only', () => {
      cy.get('[data-testid="row-checkbox"]').first().click()
      ExportActions.openExportMenu()
      cy.contains('Export Selected').click()
    })
  })

  describe('Output Visualization', () => {
    it('should display data distribution charts', () => {
      UIHelpers.clickElement('visualization-tab')
      UIHelpers.verifyElementVisible('distribution-chart')
    })

    it('should show timeline visualization', () => {
      UIHelpers.clickElement('visualization-tab')
      UIHelpers.verifyElementVisible('timeline-chart')
    })

    it('should display status code distribution', () => {
      UIHelpers.clickElement('visualization-tab')
      UIHelpers.verifyElementVisible('status-chart')
    })

    it('should show duration histogram', () => {
      UIHelpers.clickElement('visualization-tab')
      UIHelpers.verifyElementVisible('duration-histogram')
    })
  })

  describe('Mobile Output Display', () => {
    beforeEach(() => {
      cy.viewport('iphone-x')
    })

    it('should adapt table for mobile viewing', () => {
      cy.get(Selectors.previewTable).should('have.css', 'overflow-x', 'auto')
    })

    it('should stack statistics vertically', () => {
      cy.get('[data-testid="stats-container"]').should('have.css', 'flex-direction', 'column')
    })

    it('should provide mobile-friendly export options', () => {
      ExportActions.openExportMenu()
      cy.get('[data-testid="mobile-export-menu"]').should('be.visible')
    })
  })

  describe('Accessibility in Output Display', () => {
    it('should have accessible table headers', () => {
      cy.get('th[scope="col"]').should('have.length.at.least', 4)
    })

    it('should support screen reader navigation', () => {
      cy.get('[role="table"]').should('be.visible')
      cy.get('[role="row"]').should('have.length.at.least', 5)
    })

    it('should have proper ARIA labels for statistics', () => {
      cy.get('[aria-label*="Total records"]').should('exist')
      cy.get('[aria-label*="Success rate"]').should('exist')
    })
  })
})