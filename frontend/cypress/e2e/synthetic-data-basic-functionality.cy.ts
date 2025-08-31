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
      cy.contains('Generate Synthetic Data').should('be.visible')
      cy.get('.mx-auto').should('be.visible')
    })

    it('should show configuration form elements', () => {
      cy.contains('Number of Traces').should('be.visible')
      cy.contains('Number of Users').should('be.visible')
      cy.contains('Error Rate').should('be.visible')
      cy.contains('Workload Pattern').should('be.visible')
    })

    it('should display card layout', () => {
      cy.get('.max-w-2xl').should('exist')
      cy.get('.mx-auto').should('exist')
    })
  })

  describe('Configuration Parameters', () => {
    it('should display all configuration fields', () => {
      cy.contains('Number of Traces').should('be.visible')
      cy.contains('Number of Users').should('be.visible')
      cy.contains('Error Rate').should('be.visible')
      cy.contains('Workload Pattern').should('be.visible')
      cy.contains('Event Types').should('be.visible')
      cy.contains('Source Table').should('be.visible')
    })

    it('should have default values set', () => {
      cy.get('#num_traces').should('have.value', '100')
      cy.get('#num_users').should('have.value', '10')
      cy.get('#error_rate').should('have.value', '0.1')
      cy.get('#event_types').should('have.value', 'search,login')
    })

    it('should allow updating trace count', () => {
      cy.get('#num_traces').clear().type('5000')
      cy.get('#num_traces').should('have.value', '5000')
    })

    it('should allow updating user count', () => {
      cy.get('#num_users').clear().type('500')
      cy.get('#num_users').should('have.value', '500')
    })

    it('should allow updating error rate', () => {
      cy.get('#error_rate').clear().type('0.15')
      cy.get('#error_rate').should('have.value', '0.15')
    })

    it('should allow updating event types', () => {
      cy.get('#event_types').clear().type('purchase,checkout')
      cy.get('#event_types').should('have.value', 'purchase,checkout')
    })
  })

  describe('Workload Pattern Selection', () => {
    it('should display workload pattern dropdown', () => {
      cy.get('[data-testid="select-trigger"]').should('be.visible')
      cy.contains('Select a pattern').should('be.visible')
    })

    it('should show available workload patterns', () => {
      cy.get('[data-testid="select-trigger"]').click()
      cy.contains('Default Workload').should('be.visible')
      cy.contains('Cost-Sensitive').should('be.visible')
      cy.contains('Latency-Sensitive').should('be.visible')
      cy.contains('High Error Rate').should('be.visible')
    })

    it('should allow selecting workload pattern', () => {
      cy.get('[data-testid="select-trigger"]').click()
      cy.contains('Cost-Sensitive').click()
      // Close dropdown if it stays open
      cy.get('body').click(0, 0)
    })

    it('should maintain default pattern selection', () => {
      cy.get('[data-testid="select-trigger"]')
        .should('contain', 'Default Workload')
    })
  })

  describe('Source Table Management', () => {
    it('should display source table selection', () => {
      cy.contains('Source Table').should('be.visible')
      cy.get('#source_table').should('be.visible')
    })

    it('should load available source tables', () => {
      // The component fetches tables on load, so we just verify the dropdown exists
      cy.get('#source_table').should('be.visible')
    })

    it('should have default destination table name', () => {
      // Destination table is auto-generated with timestamp
      cy.contains('synthetic_data_').should('exist')
    })
  })

  describe('Basic Generation Controls', () => {
    it('should have generate button', () => {
      cy.contains('Generate Data').should('be.visible')
      cy.get('button').contains('Generate Data').should('not.be.disabled')
    })

    it('should show loading state during generation', () => {
      // Mock a slow response to test loading state
      cy.intercept('POST', '**/api/generation/synthetic_data', { delay: 2000, body: { success: true } })
      cy.contains('Generate Data').click()
      cy.contains('Generating...').should('be.visible')
    })

    it('should be full width button', () => {
      cy.get('button').contains('Generate Data').should('have.class', 'w-full')
    })
  })

  describe('UI Component Validation', () => {
    it('should display configuration form properly', () => {
      cy.get('.space-y-4').should('be.visible')
      cy.get('input[type="number"]').should('have.length', 3) // num_traces, num_users, error_rate
      cy.get('input[type="text"]').should('have.length', 1) // event_types
    })

    it('should use proper grid layout', () => {
      cy.get('.grid-cols-2').should('be.visible')
      cy.get('.gap-4').should('be.visible')
    })

    it('should maintain form state on interaction', () => {
      cy.get('#num_traces').clear().type('2000')
      cy.get('#num_users').clear().type('25')
      cy.get('#num_traces').should('have.value', '2000')
      cy.get('#num_users').should('have.value', '25')
    })

    it('should handle rapid configuration changes', () => {
      cy.get('#num_traces').clear().type('1000')
      cy.get('#num_traces').clear().type('2000')
      cy.get('#num_traces').clear().type('3000')
      cy.get('#num_traces').should('have.value', '3000')
    })

    it('should show proper labels for all inputs', () => {
      cy.get('label[for="num_traces"]').should('contain', 'Number of Traces')
      cy.get('label[for="num_users"]').should('contain', 'Number of Users')
      cy.get('label[for="error_rate"]').should('contain', 'Error Rate')
      cy.get('label[for="event_types"]').should('contain', 'Event Types')
    })
  })

  describe('Basic Error Handling', () => {
    it('should handle API errors gracefully', () => {
      // Mock an API error
      cy.intercept('POST', '**/api/generation/synthetic_data', { statusCode: 500, body: { error: 'Internal Server Error' } })
      cy.contains('Generate Data').click()
      cy.contains('Failed to generate synthetic data').should('be.visible')
    })

    it('should show error alert when generation fails', () => {
      // Mock an API error
      cy.intercept('POST', '**/api/generation/synthetic_data', { statusCode: 400, body: { error: 'Bad Request' } })
      cy.contains('Generate Data').click()
      cy.get('[role="alert"]').should('be.visible')
      cy.contains('Error').should('be.visible')
    })

    it('should handle table fetch errors', () => {
      // Mock table fetch error
      cy.intercept('GET', '**/api/generation/clickhouse_tables', { statusCode: 500 })
      cy.reload()
      cy.contains('Failed to fetch tables').should('be.visible')
    })
  })

  describe('Configuration Validation', () => {
    it('should accept valid numeric inputs', () => {
      cy.get('#num_traces').clear().type('1000')
      cy.get('#num_users').clear().type('50')
      cy.get('#error_rate').clear().type('0.05')
      
      cy.get('#num_traces').should('have.value', '1000')
      cy.get('#num_users').should('have.value', '50')
      cy.get('#error_rate').should('have.value', '0.05')
    })

    it('should handle step validation for error rate', () => {
      cy.get('#error_rate').should('have.attr', 'step', '0.01')
    })

    it('should maintain form values during interaction', () => {
      cy.get('#num_traces').clear().type('500')
      cy.get('#event_types').clear().type('custom,events')
      
      // Click somewhere else and verify values persist
      cy.contains('Generate Data').click()
      cy.get('#num_traces').should('have.value', '500')
      cy.get('#event_types').should('have.value', 'custom,events')
    })
  })
})