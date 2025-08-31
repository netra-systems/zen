/// <reference types="cypress" />
import { SyntheticDataPageObject } from './utils/synthetic-data-page-object'

/**
 * Advanced Features Tests for Synthetic Data Generation Page
 * Tests: Advanced configuration, real-time monitoring, and history management
 * Business Value: Growth segment - validates advanced features for power users
 */

describe('Synthetic Data Generation - Advanced Features', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/synthetic-data-generation')
    cy.wait(1000)
  })

  describe('Advanced Configuration', () => {
    it('should show event types configuration', () => {
      cy.contains('Event Types').should('be.visible')
      cy.get('input[name="event_types"]').should('have.value', 'search,login')
    })

    it('should allow customizing event types', () => {
      cy.get('input[name="event_types"]').clear().type('purchase,view,click')
      cy.get('input[name="event_types"]').should('have.value', 'purchase,view,click')
    })

    it('should show destination table configuration', () => {
      cy.get('input').should('exist')
      // Destination table is auto-generated with timestamp
      cy.get('body').should('contain.text', 'synthetic_data_')
    })

    it('should handle multiple workload patterns', () => {
      cy.get('button[role="combobox"]').click()
      cy.contains('Cost-Sensitive').should('be.visible')
      cy.contains('Latency-Sensitive').should('be.visible')
      cy.contains('High Error Rate').should('be.visible')
    })

    it('should allow defining custom fields', () => {
      SyntheticDataPageObject.openAdvancedOptions()
      SyntheticDataPageObject.addCustomField('region', 'string')
      cy.contains('region').should('be.visible')
    })

    it('should save configuration as template', () => {
      SyntheticDataPageObject.openAdvancedOptions()
      SyntheticDataPageObject.saveTemplate('My Config')
      cy.contains('Template Saved').should('be.visible')
    })

    it('should load saved templates', () => {
      SyntheticDataPageObject.openAdvancedOptions()
      SyntheticDataPageObject.saveTemplate('Test Template')
      cy.contains('Load Template').click()
      cy.contains('Test Template').click()
      cy.contains('Template Loaded').should('be.visible')
    })

    it('should validate advanced field constraints', () => {
      SyntheticDataPageObject.openAdvancedOptions()
      cy.get(SyntheticDataPageObject.selectors.minLatencyInput)
        .type('1000')
      cy.get(SyntheticDataPageObject.selectors.maxLatencyInput)
        .type('100')
      cy.contains('Max must be greater than min').should('be.visible')
    })

    it('should support advanced workload patterns', () => {
      SyntheticDataPageObject.openAdvancedOptions()
      cy.contains('Custom Pattern').click()
      cy.get('textarea[name="patternScript"]').should('be.visible')
      cy.get('textarea[name="patternScript"]')
        .type('function generate() { return Math.random(); }')
      cy.contains('Validate Script').click()
      cy.contains('Script Valid').should('be.visible')
    })
  })

  describe('Real-time Status and Monitoring', () => {
    it('should show generation status in real-time', () => {
      SyntheticDataPageObject.startGeneration()
      cy.contains('Initializing').should('be.visible')
      cy.contains('Generating').should('be.visible')
    })

    it('should display records per second metric', () => {
      SyntheticDataPageObject.startGeneration()
      cy.contains('Records/sec').should('be.visible')
      cy.get(SyntheticDataPageObject.selectors.throughputMetric)
        .should('contain', /\d+/)
    })

    it('should show memory usage indicator', () => {
      SyntheticDataPageObject.startGeneration()
      cy.contains('Memory Usage').should('be.visible')
      cy.get(SyntheticDataPageObject.selectors.memoryBar)
        .should('be.visible')
    })

    it('should track generation phases', () => {
      SyntheticDataPageObject.startGeneration()
      cy.contains('Phase: Initialization').should('be.visible')
      cy.wait(1000)
      cy.contains('Phase: Data Generation').should('be.visible')
    })

    it('should show estimated completion time', () => {
      SyntheticDataPageObject.startGeneration()
      cy.contains('ETA:').should('be.visible')
      cy.contains(/\d+:\d+/).should('be.visible')
    })

    it('should display resource utilization graphs', () => {
      SyntheticDataPageObject.startGeneration()
      cy.get('[data-testid="cpu-chart"]').should('be.visible')
      cy.get('[data-testid="memory-chart"]').should('be.visible')
    })

    it('should alert on performance bottlenecks', () => {
      SyntheticDataPageObject.setTraceCount('100000')
      SyntheticDataPageObject.startGeneration()
      cy.contains('Performance Warning').should('be.visible')
      cy.contains('Consider reducing batch size').should('be.visible')
    })

    it('should provide real-time quality metrics', () => {
      SyntheticDataPageObject.startGeneration()
      cy.contains('Data Quality Score').should('be.visible')
      cy.get('[data-testid="quality-score"]').should('contain', /\d+%/)
    })
  })

  describe('History and Previous Generations', () => {
    it('should display generation history tab', () => {
      cy.contains('History').should('be.visible')
    })

    it('should show previous generations list', () => {
      SyntheticDataPageObject.openHistory()
      cy.get(SyntheticDataPageObject.selectors.historyItem)
        .should('have.length.at.least', 0)
    })

    it('should display generation metadata', () => {
      SyntheticDataPageObject.startGeneration()
      cy.wait(3000)
      SyntheticDataPageObject.openHistory()
      cy.get(SyntheticDataPageObject.selectors.historyItem)
        .first()
        .should('contain', 'traces')
      cy.get(SyntheticDataPageObject.selectors.historyItem)
        .first()
        .should('contain', 'ago')
    })

    it('should allow reusing previous configuration', () => {
      SyntheticDataPageObject.startGeneration()
      cy.wait(3000)
      SyntheticDataPageObject.openHistory()
      SyntheticDataPageObject.reuseFirstConfig()
      cy.get(SyntheticDataPageObject.selectors.tracesInput)
        .should('have.value', '1000')
    })

    it('should allow deleting history items', () => {
      SyntheticDataPageObject.openHistory()
      SyntheticDataPageObject.deleteFirstHistoryItem()
      cy.contains('Deleted').should('be.visible')
    })

    it('should show detailed generation statistics', () => {
      SyntheticDataPageObject.openHistory()
      cy.get(SyntheticDataPageObject.selectors.historyItem)
        .first()
        .click()
      cy.contains('Generation Details').should('be.visible')
      cy.contains('Duration:').should('be.visible')
      cy.contains('Success Rate:').should('be.visible')
    })

    it('should allow comparing multiple generations', () => {
      SyntheticDataPageObject.openHistory()
      cy.get('[data-testid="compare-checkbox"]').first().check()
      cy.get('[data-testid="compare-checkbox"]').eq(1).check()
      cy.contains('Compare Selected').click()
      cy.contains('Comparison Report').should('be.visible')
    })

    it('should export generation history', () => {
      SyntheticDataPageObject.openHistory()
      cy.contains('Export History').click()
      cy.contains('CSV').click()
      cy.readFile('cypress/downloads/generation_history.csv')
        .should('exist')
    })

    it('should filter history by date range', () => {
      SyntheticDataPageObject.openHistory()
      cy.get('input[name="startDate"]').type('2024-01-01')
      cy.get('input[name="endDate"]').type('2024-12-31')
      cy.contains('Apply Filter').click()
      cy.get(SyntheticDataPageObject.selectors.historyItem)
        .should('be.visible')
    })
  })

  describe('Template Management', () => {
    beforeEach(() => {
      SyntheticDataPageObject.openAdvancedOptions()
    })

    it('should create custom configuration templates', () => {
      SyntheticDataPageObject.setLatencyRange('50', '500')
      SyntheticDataPageObject.addServiceName('payment-service')
      SyntheticDataPageObject.saveTemplate('Payment Service Template')
      cy.contains('Template created successfully').should('be.visible')
    })

    it('should list available templates', () => {
      cy.contains('Manage Templates').click()
      cy.get('[data-testid="template-list"]').should('be.visible')
      cy.get('[data-testid="template-item"]')
        .should('have.length.at.least', 0)
    })

    it('should edit existing templates', () => {
      SyntheticDataPageObject.saveTemplate('Edit Test')
      cy.contains('Manage Templates').click()
      cy.get('[data-testid="edit-template"]').first().click()
      cy.get('input[name="templateName"]').clear().type('Updated Name')
      cy.contains('Save Changes').click()
      cy.contains('Template updated').should('be.visible')
    })

    it('should delete templates', () => {
      SyntheticDataPageObject.saveTemplate('Delete Test')
      cy.contains('Manage Templates').click()
      cy.get('[data-testid="delete-template"]').first().click()
      cy.contains('Confirm Delete').click()
      cy.contains('Template deleted').should('be.visible')
    })

    it('should share templates between users', () => {
      SyntheticDataPageObject.saveTemplate('Shared Template')
      cy.contains('Manage Templates').click()
      cy.get('[data-testid="share-template"]').first().click()
      cy.get('input[name="shareEmail"]').type('user@example.com')
      cy.contains('Share').click()
      cy.contains('Template shared').should('be.visible')
    })
  })

  describe('Advanced Analytics', () => {
    beforeEach(() => {
      SyntheticDataPageObject.startGeneration()
      cy.wait(3000) // Wait for generation to complete
    })

    it('should show data distribution analysis', () => {
      cy.contains('Analytics').click()
      cy.contains('Data Distribution').should('be.visible')
      cy.get('[data-testid="distribution-chart"]').should('be.visible')
    })

    it('should display correlation matrices', () => {
      cy.contains('Analytics').click()
      cy.contains('Correlations').click()
      cy.get('[data-testid="correlation-matrix"]').should('be.visible')
    })

    it('should provide anomaly detection insights', () => {
      cy.contains('Analytics').click()
      cy.contains('Anomalies').click()
      cy.get('[data-testid="anomaly-chart"]').should('be.visible')
      cy.contains('anomalies detected').should('be.visible')
    })

    it('should generate quality reports', () => {
      cy.contains('Analytics').click()
      cy.contains('Quality Report').click()
      cy.contains('Data Quality Score:').should('be.visible')
      cy.contains('Completeness:').should('be.visible')
      cy.contains('Consistency:').should('be.visible')
    })

    it('should compare with baseline datasets', () => {
      cy.contains('Analytics').click()
      cy.contains('Baseline Comparison').click()
      cy.get('select[name="baselineDataset"]').select('production_traces')
      cy.contains('Compare').click()
      cy.contains('Similarity Score:').should('be.visible')
    })
  })

  describe('Batch Operations', () => {
    it('should support batch generation jobs', () => {
      cy.contains('Batch Mode').click()
      cy.contains('Add Generation Job').click()
      SyntheticDataPageObject.setTraceCount('1000')
      cy.contains('Add to Queue').click()
      cy.contains('Job queued').should('be.visible')
    })

    it('should schedule recurring generations', () => {
      cy.contains('Schedule').click()
      cy.get('select[name="frequency"]').select('daily')
      cy.get('input[name="time"]').type('09:00')
      cy.contains('Save Schedule').click()
      cy.contains('Schedule created').should('be.visible')
    })

    it('should monitor batch job progress', () => {
      cy.contains('Batch Mode').click()
      cy.contains('Job Queue').should('be.visible')
      cy.get('[data-testid="job-status"]').should('contain', /pending|running|completed/)
    })

    it('should handle batch job failures', () => {
      cy.contains('Batch Mode').click()
      cy.get('[data-testid="failed-job"]').click()
      cy.contains('Error Details').should('be.visible')
      cy.contains('Retry Job').should('be.visible')
    })
  })
})