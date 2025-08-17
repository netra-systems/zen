/// <reference types="cypress" />

import { 
  SyntheticDataTestUtils, 
  ConfigurationFactory, 
  GenerationActions, 
  UIHelpers, 
  TestData 
} from './synthetic-data-test-utils'

/**
 * Data generation process tests for synthetic data generator
 * BVJ: Growth segment - ensures reliable data generation for customer value creation
 */
describe('SyntheticDataGenerator - Generation Process Tests', () => {
  beforeEach(() => {
    SyntheticDataTestUtils.setupViewport()
    SyntheticDataTestUtils.visitComponent()
  })

  describe('Generation Controls', () => {
    it('should display generate button with proper text', () => {
      SyntheticDataTestUtils.getGenerateButton().should('be.visible')
      UIHelpers.verifyTextContent('Generate Data')
    })

    it('should enable generate with valid configuration', () => {
      ConfigurationFactory.setTraceCount(100)
      SyntheticDataTestUtils.getGenerateButton().should('not.be.disabled')
    })

    it('should disable generate with invalid configuration', () => {
      cy.get('input[name="traceCount"]').clear()
      SyntheticDataTestUtils.getGenerateButton().should('be.disabled')
    })

    it('should show generation estimates', () => {
      ConfigurationFactory.setTraceCount(10000)
      UIHelpers.verifyTextContent('Estimated time')
      UIHelpers.verifyTextContent('Estimated size')
    })

    it('should display warning for large datasets', () => {
      ConfigurationFactory.setTraceCount(TestData.largeDataset)
      UIHelpers.verifyTextContent('Large dataset warning')
    })
  })

  describe('Generation Process Flow', () => {
    it('should start generation process successfully', () => {
      GenerationActions.startGeneration()
      UIHelpers.verifyTextContent('Generating')
    })

    it('should show progress indicators during generation', () => {
      GenerationActions.startGeneration()
      GenerationActions.verifyProgress()
    })

    it('should display progress percentage updates', () => {
      GenerationActions.startGeneration()
      cy.get('[data-testid="progress-percent"]').should('contain', '%')
    })

    it('should show records generated count', () => {
      GenerationActions.startGeneration()
      cy.get('[data-testid="records-count"]').should('contain', /\d+/)
    })

    it('should display generation speed metrics', () => {
      GenerationActions.startGeneration()
      UIHelpers.verifyTextContent('records/sec')
    })

    it('should allow canceling generation', () => {
      GenerationActions.startGeneration()
      cy.get('[data-testid="cancel-btn"]').should('be.visible')
      GenerationActions.cancelGeneration()
      UIHelpers.verifyTextContent('Cancelled')
    })

    it('should complete small generation successfully', () => {
      ConfigurationFactory.setTraceCount(TestData.smallDataset)
      GenerationActions.startGeneration()
      GenerationActions.waitForCompletion()
    })
  })

  describe('Real-time Monitoring During Generation', () => {
    beforeEach(() => {
      GenerationActions.startGeneration()
    })

    it('should display monitoring panel', () => {
      UIHelpers.verifyElementVisible('monitoring-panel')
    })

    it('should show CPU usage metrics', () => {
      UIHelpers.verifyTextContent('CPU Usage')
      UIHelpers.verifyElementVisible('cpu-meter')
    })

    it('should display memory usage information', () => {
      UIHelpers.verifyTextContent('Memory')
      UIHelpers.verifyElementVisible('memory-meter')
    })

    it('should show throughput graph', () => {
      UIHelpers.verifyElementVisible('throughput-graph')
    })

    it('should display error count', () => {
      UIHelpers.verifyTextContent('Errors')
      cy.get('[data-testid="error-count"]').should('contain', '0')
    })
  })

  describe('Generation History and Logs', () => {
    beforeEach(() => {
      ConfigurationFactory.setTraceCount(TestData.smallDataset)
      GenerationActions.startGeneration()
      GenerationActions.waitForCompletion()
    })

    it('should display history tab', () => {
      UIHelpers.verifyElementVisible('history-tab')
    })

    it('should show generation history entries', () => {
      UIHelpers.clickElement('history-tab')
      cy.get('[data-testid="history-item"]').should('have.length.at.least', 1)
    })

    it('should display history details', () => {
      UIHelpers.clickElement('history-tab')
      cy.get('[data-testid="history-item"]').first().should('contain', 'traces')
      cy.get('[data-testid="history-item"]').first().should('contain', 'ago')
    })

    it('should allow reusing history configuration', () => {
      UIHelpers.clickElement('history-tab')
      UIHelpers.clickElement('reuse-config')
      cy.get('input[name="traceCount"]').should('have.value')
    })

    it('should show generation logs', () => {
      GenerationActions.startGeneration()
      UIHelpers.clickElement('logs-tab')
      cy.get('[data-testid="log-entry"]').should('have.length.at.least', 1)
    })

    it('should clear history when requested', () => {
      UIHelpers.clickElement('history-tab')
      UIHelpers.clickElement('clear-history')
      cy.contains('Confirm').click()
      UIHelpers.verifyTextContent('History cleared')
    })
  })

  describe('Templates and Preset Management', () => {
    it('should display preset selector', () => {
      UIHelpers.verifyElementVisible('preset-selector')
    })

    it('should show available preset options', () => {
      UIHelpers.clickElement('preset-selector')
      TestData.presets.forEach(preset => {
        UIHelpers.verifyTextContent(preset)
      })
    })

    it('should apply preset configuration correctly', () => {
      cy.get('[data-testid="preset-selector"]').select('E-commerce')
      cy.get('input[name="traceCount"]').should('have.value', '5000')
      cy.get('select[name="workloadPattern"]').should('have.value', 'periodic')
    })

    it('should save custom template', () => {
      ConfigurationFactory.setTraceCount(2500)
      UIHelpers.clickElement('save-template')
      cy.get('input[name="templateName"]').type('My Template')
      UIHelpers.clickElement('save-template-confirm')
      UIHelpers.verifyTextContent('Template saved')
    })

    it('should load custom template', () => {
      UIHelpers.clickElement('template-menu')
      cy.contains('My Template').click()
      cy.get('input[name="traceCount"]').should('have.value', '2500')
    })

    it('should delete template successfully', () => {
      UIHelpers.clickElement('template-menu')
      cy.get('[data-testid="delete-template"]').first().click()
      cy.contains('Confirm').click()
      UIHelpers.verifyTextContent('Template deleted')
    })
  })

  describe('API Integration Information', () => {
    it('should display API endpoint information', () => {
      UIHelpers.clickElement('api-info')
      UIHelpers.verifyTextContent('/api/synthetic-data/generate')
    })

    it('should show API request example', () => {
      UIHelpers.clickElement('api-info')
      UIHelpers.verifyTextContent('POST')
      cy.get('code').should('contain', 'traceCount')
    })

    it('should display API response format', () => {
      UIHelpers.clickElement('api-info')
      UIHelpers.verifyTextContent('Response')
      cy.get('code').should('contain', 'success')
    })

    it('should copy API snippet to clipboard', () => {
      UIHelpers.clickElement('api-info')
      UIHelpers.clickElement('copy-snippet')
      UIHelpers.verifyTextContent('Copied')
    })
  })

  describe('Error Handling During Generation', () => {
    it('should handle generation failures gracefully', () => {
      cy.intercept('POST', '/api/synthetic-data/generate', { statusCode: 500 })
      GenerationActions.startGeneration()
      UIHelpers.verifyTextContent('Generation failed')
    })

    it('should show retry option on failure', () => {
      cy.intercept('POST', '/api/synthetic-data/generate', { statusCode: 500 })
      GenerationActions.startGeneration()
      UIHelpers.verifyTextContent('Retry')
    })

    it('should validate configuration before starting', () => {
      cy.get('input[name="traceCount"]').clear()
      GenerationActions.startGeneration()
      UIHelpers.verifyTextContent('Invalid configuration')
    })

    it('should handle request timeout appropriately', () => {
      cy.intercept('POST', '/api/synthetic-data/generate', (req) => {
        req.reply((res) => {
          res.delay(30000)
        })
      })
      GenerationActions.startGeneration()
      cy.wait(10000)
      UIHelpers.verifyTextContent('Request timed out')
    })
  })

  describe('Mobile Generation Support', () => {
    beforeEach(() => {
      cy.viewport('iphone-x')
    })

    it('should handle mobile generation process', () => {
      GenerationActions.startGeneration()
      UIHelpers.verifyElementVisible('progress-bar')
    })

    it('should announce generation status for accessibility', () => {
      GenerationActions.startGeneration()
      cy.get('[role="status"]').should('contain', 'Generating')
    })
  })
})