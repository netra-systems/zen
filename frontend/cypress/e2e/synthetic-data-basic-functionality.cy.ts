/// <reference types="cypress" />
import { 
  SyntheticDataPageObject, 
  WORKLOAD_PATTERNS, 
  TABLE_OPTIONS, 
  VALIDATION_MESSAGES 
} from './utils/synthetic-data-page-object'

/**
 * Basic Functionality Tests for Synthetic Data Generation Page
 * Tests: Page load, configuration, patterns, and table management
 * Business Value: Growth segment - validates core data generation UI functionality
 */

describe('Synthetic Data Generation - Basic Functionality', () => {
  beforeEach(() => {
    SyntheticDataPageObject.visitPage()
  })

  describe('Page Load and Initial State', () => {
    it('should load the synthetic data generation page', () => {
      SyntheticDataPageObject.verifyPageLoad()
    })

    it('should display the main generator component', () => {
      cy.get(SyntheticDataPageObject.selectors.page).should('be.visible')
    })

    it('should show configuration panel', () => {
      cy.contains('Configuration').should('be.visible')
      cy.contains('Parameters').should('be.visible')
    })

    it('should display glassmorphic design elements', () => {
      cy.get('.backdrop-blur').should('exist')
      cy.get('.bg-opacity-20').should('exist')
    })
  })

  describe('Configuration Parameters', () => {
    it('should display all configuration fields', () => {
      cy.contains('Number of Traces').should('be.visible')
      cy.contains('Number of Users').should('be.visible')
      cy.contains('Error Rate').should('be.visible')
      cy.contains('Workload Pattern').should('be.visible')
    })

    it('should have default values set', () => {
      SyntheticDataPageObject.verifyDefaultValues()
    })

    it('should allow updating trace count', () => {
      SyntheticDataPageObject.setTraceCount('5000')
      cy.get(SyntheticDataPageObject.selectors.tracesInput)
        .should('have.value', '5000')
    })

    it('should allow updating user count', () => {
      SyntheticDataPageObject.setUserCount('500')
      cy.get(SyntheticDataPageObject.selectors.usersInput)
        .should('have.value', '500')
    })

    it('should allow updating error rate with slider', () => {
      SyntheticDataPageObject.setErrorRate(15)
      cy.contains('15%').should('be.visible')
    })

    it('should validate input ranges', () => {
      SyntheticDataPageObject.setTraceCount('-100')
      cy.contains(VALIDATION_MESSAGES.mustBePositive).should('be.visible')
    })

    it('should show tooltips for parameters', () => {
      cy.get(SyntheticDataPageObject.selectors.tracesTooltip)
        .trigger('mouseenter')
      cy.contains('Number of synthetic traces to generate')
        .should('be.visible')
    })
  })

  describe('Workload Pattern Selection', () => {
    it('should display workload pattern options', () => {
      WORKLOAD_PATTERNS.forEach(pattern => {
        cy.contains(pattern).should('be.visible')
      })
    })

    it('should allow selecting workload pattern', () => {
      SyntheticDataPageObject.selectWorkloadPattern('Burst')
      SyntheticDataPageObject.verifyPatternSelected('Burst')
    })

    it('should show pattern description on hover', () => {
      cy.contains('Periodic').trigger('mouseenter')
      cy.contains('Regular cycles of high and low activity')
        .should('be.visible')
    })

    it('should update preview based on pattern', () => {
      SyntheticDataPageObject.selectWorkloadPattern('Growth')
      cy.get(SyntheticDataPageObject.selectors.patternPreview)
        .should('contain', 'Growth')
    })

    it('should allow pattern customization', () => {
      SyntheticDataPageObject.selectWorkloadPattern('Burst')
      cy.contains('Customize Pattern').click()
      cy.get(SyntheticDataPageObject.selectors.burstIntensity)
        .should('be.visible')
      cy.get(SyntheticDataPageObject.selectors.burstFrequency)
        .should('be.visible')
    })
  })

  describe('Table Management', () => {
    it('should display table selection dropdown', () => {
      cy.contains('Target Table').should('be.visible')
      cy.get(SyntheticDataPageObject.selectors.targetTableSelect)
        .should('be.visible')
    })

    it('should show available tables', () => {
      cy.get(SyntheticDataPageObject.selectors.targetTableSelect).click()
      TABLE_OPTIONS.forEach(table => {
        cy.contains(table).should('be.visible')
      })
    })

    it('should allow creating new table', () => {
      SyntheticDataPageObject.createNewTable('custom_synthetic_table')
      cy.contains('custom_synthetic_table').should('be.visible')
    })

    it('should show table schema preview', () => {
      SyntheticDataPageObject.selectTable('traces_synthetic')
      cy.contains('Schema Preview').should('be.visible')
      cy.contains('trace_id').should('be.visible')
      cy.contains('timestamp').should('be.visible')
    })

    it('should validate table name format', () => {
      cy.contains('Create New Table').click()
      cy.get(SyntheticDataPageObject.selectors.tableNameInput)
        .type('invalid-table-name!')
      cy.contains(VALIDATION_MESSAGES.invalidTableName)
        .should('be.visible')
    })
  })

  describe('Basic Generation Controls', () => {
    it('should have generate button', () => {
      cy.get(SyntheticDataPageObject.selectors.generateButton)
        .should('be.visible')
    })

    it('should disable generate button without configuration', () => {
      SyntheticDataPageObject.setTraceCount('')
      cy.get(SyntheticDataPageObject.selectors.generateButton)
        .should('be.disabled')
    })

    it('should prevent duplicate submissions', () => {
      SyntheticDataPageObject.startGeneration()
      cy.get(SyntheticDataPageObject.selectors.generateButton)
        .should('be.disabled')
    })

    it('should validate maximum limits', () => {
      SyntheticDataPageObject.setTraceCount('10000000')
      cy.contains(VALIDATION_MESSAGES.exceedsMaxLimit)
        .should('be.visible')
      cy.get(SyntheticDataPageObject.selectors.generateButton)
        .should('be.disabled')
    })
  })

  describe('UI Component Validation', () => {
    it('should display configuration form properly', () => {
      cy.get('form').should('be.visible')
      cy.get('input[type="number"]').should('have.length.at.least', 2)
      cy.get('input[type="range"]').should('be.visible')
    })

    it('should show help text for complex fields', () => {
      cy.contains('Workload Pattern').parent()
        .find('[data-testid*="help"]')
        .should('exist')
    })

    it('should maintain form state on interaction', () => {
      SyntheticDataPageObject.setTraceCount('2000')
      SyntheticDataPageObject.selectWorkloadPattern('Periodic')
      cy.get(SyntheticDataPageObject.selectors.tracesInput)
        .should('have.value', '2000')
      SyntheticDataPageObject.verifyPatternSelected('Periodic')
    })

    it('should handle rapid configuration changes', () => {
      SyntheticDataPageObject.setTraceCount('1000')
      SyntheticDataPageObject.setTraceCount('2000')
      SyntheticDataPageObject.setTraceCount('3000')
      cy.get(SyntheticDataPageObject.selectors.tracesInput)
        .should('have.value', '3000')
    })

    it('should show validation feedback immediately', () => {
      SyntheticDataPageObject.setTraceCount('0')
      cy.contains(VALIDATION_MESSAGES.mustBePositive)
        .should('be.visible')
      SyntheticDataPageObject.setTraceCount('1000')
      cy.contains(VALIDATION_MESSAGES.mustBePositive)
        .should('not.exist')
    })
  })

  describe('Basic Error Handling', () => {
    it('should handle invalid numeric inputs', () => {
      cy.get(SyntheticDataPageObject.selectors.tracesInput)
        .clear()
        .type('abc')
      cy.contains('Invalid number').should('be.visible')
    })

    it('should handle out-of-range inputs gracefully', () => {
      SyntheticDataPageObject.setErrorRate(150)
      cy.contains('Error rate must be between 0-100%')
        .should('be.visible')
    })

    it('should reset invalid configurations', () => {
      SyntheticDataPageObject.setTraceCount('-500')
      cy.contains('Reset to Default').click()
      SyntheticDataPageObject.verifyDefaultValues()
    })

    it('should preserve valid fields when resetting invalid ones', () => {
      SyntheticDataPageObject.setUserCount('200')
      SyntheticDataPageObject.setTraceCount('-100')
      cy.contains('Reset Invalid').click()
      cy.get(SyntheticDataPageObject.selectors.usersInput)
        .should('have.value', '200')
    })
  })

  describe('Configuration Persistence', () => {
    it('should remember configuration between page visits', () => {
      SyntheticDataPageObject.setTraceCount('3000')
      SyntheticDataPageObject.selectWorkloadPattern('Growth')
      cy.reload()
      cy.get(SyntheticDataPageObject.selectors.tracesInput)
        .should('have.value', '3000')
      SyntheticDataPageObject.verifyPatternSelected('Growth')
    })

    it('should handle browser back/forward navigation', () => {
      SyntheticDataPageObject.setTraceCount('4000')
      cy.visit('/dashboard')
      cy.go('back')
      cy.get(SyntheticDataPageObject.selectors.tracesInput)
        .should('have.value', '4000')
    })
  })
})