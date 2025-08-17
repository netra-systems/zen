/// <reference types="cypress" />

import { 
  SyntheticDataTestUtils, 
  ConfigurationFactory, 
  UIHelpers, 
  TestData, 
  Selectors 
} from './synthetic-data-test-utils'

/**
 * Basic component tests for synthetic data generator
 * BVJ: Growth segment - ensures core UI functionality works reliably
 */
describe('SyntheticDataGenerator - Basic Component Tests', () => {
  beforeEach(() => {
    SyntheticDataTestUtils.setupViewport()
    SyntheticDataTestUtils.visitComponent()
  })

  describe('Component Initialization', () => {
    it('should render component with proper structure', () => {
      SyntheticDataTestUtils.getGenerator().should('be.visible')
      UIHelpers.verifyTextContent('Synthetic Data Generator')
      UIHelpers.verifyTextContent('Generate realistic test data')
    })

    it('should display glassmorphic styling', () => {
      cy.get('.backdrop-blur-sm').should('exist')
      cy.get('.bg-white/5').should('exist')
    })

    it('should show all main sections', () => {
      UIHelpers.verifyTextContent('Configuration')
      UIHelpers.verifyTextContent('Output')
      UIHelpers.verifyTextContent('Actions')
    })
  })

  describe('Configuration Panel - Basic Fields', () => {
    it('should display trace count configuration', () => {
      cy.contains('label', 'Number of Traces').should('be.visible')
      cy.get('input[name="traceCount"]').should('be.visible')
      cy.get('input[name="traceCount"]').should('have.value', TestData.defaultTraceCount.toString())
    })

    it('should update trace count input', () => {
      ConfigurationFactory.setTraceCount(5000)
      cy.get('input[name="traceCount"]').should('have.value', '5000')
    })

    it('should display user count configuration', () => {
      cy.contains('label', 'Number of Users').should('be.visible')
      cy.get('input[name="userCount"]').should('be.visible')
    })

    it('should update user count input', () => {
      ConfigurationFactory.setUserCount(250)
      cy.get('input[name="userCount"]').should('have.value', '250')
    })

    it('should display error rate slider', () => {
      cy.contains('label', 'Error Rate (%)').should('be.visible')
      cy.get('input[type="range"][name="errorRate"]').should('be.visible')
    })

    it('should show error rate value updates', () => {
      ConfigurationFactory.setErrorRate(10)
      cy.get('[data-testid="error-rate-value"]').should('contain', '10%')
    })
  })

  describe('Input Validation', () => {
    it('should validate minimum trace count', () => {
      ConfigurationFactory.setTraceCount(0)
      cy.contains('Minimum value is 1').should('be.visible')
    })

    it('should validate maximum trace count', () => {
      ConfigurationFactory.setTraceCount(1000001)
      cy.contains('Maximum value is 1000000').should('be.visible')
    })

    it('should enable generate with valid config', () => {
      ConfigurationFactory.setTraceCount(100)
      SyntheticDataTestUtils.getGenerateButton().should('not.be.disabled')
    })

    it('should disable generate with empty config', () => {
      cy.get('input[name="traceCount"]').clear()
      SyntheticDataTestUtils.getGenerateButton().should('be.disabled')
    })
  })

  describe('Workload Pattern Selection', () => {
    it('should display workload pattern dropdown', () => {
      cy.contains('label', 'Workload Pattern').should('be.visible')
      cy.get('select[name="workloadPattern"]').should('be.visible')
    })

    it('should show all pattern options', () => {
      cy.get('select[name="workloadPattern"]').click()
      TestData.workloadPatterns.forEach(pattern => {
        cy.get('select[name="workloadPattern"]').contains(pattern).should('exist')
      })
    })

    it('should select workload pattern', () => {
      ConfigurationFactory.setWorkloadPattern('Burst')
      cy.get('select[name="workloadPattern"]').should('have.value', 'burst')
    })

    it('should show pattern preview chart', () => {
      ConfigurationFactory.setWorkloadPattern('Periodic')
      UIHelpers.verifyElementVisible('pattern-preview-chart')
    })

    it('should display pattern descriptions', () => {
      ConfigurationFactory.setWorkloadPattern('Growth')
      UIHelpers.verifyTextContent('Gradually increasing load')
    })

    it('should enable custom pattern editor', () => {
      ConfigurationFactory.setWorkloadPattern('Custom')
      UIHelpers.verifyElementVisible('custom-pattern-editor')
    })
  })

  describe('Table Configuration', () => {
    it('should display table selection dropdown', () => {
      cy.contains('label', 'Target Table').should('be.visible')
      cy.get('select[name="targetTable"]').should('be.visible')
    })

    it('should show existing table options', () => {
      cy.get('select[name="targetTable"]').click()
      cy.contains('traces_synthetic').should('exist')
      cy.contains('metrics_synthetic').should('exist')
    })

    it('should allow creating new table', () => {
      UIHelpers.clickElement('create-table-btn')
      UIHelpers.typeInField('table-name-input', 'test_table')
      UIHelpers.clickElement('create-table-confirm')
      UIHelpers.verifyTextContent('test_table')
    })

    it('should validate table names', () => {
      UIHelpers.clickElement('create-table-btn')
      cy.get('[data-testid="table-name-input"]').type('123-invalid!')
      cy.contains('Invalid table name').should('be.visible')
    })

    it('should display table schema preview', () => {
      cy.get('select[name="targetTable"]').select('traces_synthetic')
      UIHelpers.clickElement('schema-preview')
      UIHelpers.verifyTextContent('trace_id')
      UIHelpers.verifyTextContent('timestamp')
      UIHelpers.verifyTextContent('duration')
    })

    it('should manage table retention settings', () => {
      UIHelpers.clickElement('table-settings')
      UIHelpers.verifyTextContent('Retention Period')
      cy.get('select[name="retention"]').select('7 days')
    })
  })

  describe('Generation Estimates', () => {
    it('should show estimated time for generation', () => {
      ConfigurationFactory.setTraceCount(10000)
      UIHelpers.verifyTextContent('Estimated time')
      cy.contains(/\d+ seconds?/).should('be.visible')
    })

    it('should show estimated data size', () => {
      ConfigurationFactory.setTraceCount(10000)
      UIHelpers.verifyTextContent('Estimated size')
      cy.contains(/\d+\.?\d* MB/).should('be.visible')
    })

    it('should warn about large datasets', () => {
      ConfigurationFactory.setTraceCount(TestData.largeDataset)
      UIHelpers.verifyTextContent('Large dataset warning')
    })
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt layout for mobile viewport', () => {
      cy.viewport('iphone-x')
      SyntheticDataTestUtils.getGenerator().should('be.visible')
    })

    it('should stack configuration fields vertically', () => {
      cy.viewport('iphone-x')
      cy.get(Selectors.configSection).should('have.css', 'flex-direction', 'column')
    })

    it('should make range inputs full width', () => {
      cy.viewport('iphone-x')
      cy.get('input[type="range"]').should('have.css', 'width', '100%')
    })
  })

  describe('Accessibility Features', () => {
    it('should have proper ARIA labels', () => {
      cy.get('[aria-label]').should('have.length.at.least', 10)
    })

    it('should support keyboard navigation', () => {
      cy.get('input[name="traceCount"]').focus()
      cy.focused().tab()
      cy.focused().should('have.attr', 'name', 'userCount')
    })

    it('should have proper form labels', () => {
      cy.get('label[for="traceCount"]').should('contain', 'Traces')
      cy.get('label[for="userCount"]').should('contain', 'Users')
    })
  })
})