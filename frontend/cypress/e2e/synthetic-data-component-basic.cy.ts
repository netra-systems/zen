/// <reference types="cypress" />

// Updated imports to match current implementation

/**
 * Basic component tests for synthetic data generator
 * BVJ: Growth segment - ensures core UI functionality works reliably
 */
describe('SyntheticDataGenerator - Basic Component Tests', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/synthetic-data-generation')
    cy.wait(500)
  })

  describe('Component Initialization', () => {
    it('should render component with proper structure', () => {
      cy.contains('Generate Synthetic Data').should('be.visible')
      cy.get('.max-w-2xl').should('be.visible')
      cy.get('.mx-auto').should('be.visible')
    })

    it('should display card layout styling', () => {
      cy.get('.max-w-2xl').should('exist')
      cy.get('.space-y-4').should('exist')
      cy.get('[class*="card"]').should('exist')
      cy.get('[class*="grid"]').should('exist')
    })

    it('should show all main form elements', () => {
      cy.contains('Number of Traces').should('be.visible')
      cy.contains('Number of Users').should('be.visible')
      cy.contains('Error Rate').should('be.visible')
      cy.contains('Workload Pattern').should('be.visible')
      cy.contains('Generate Data').should('be.visible')
    })
  })

  describe('Configuration Panel - Basic Fields', () => {
    it('should display trace count configuration', () => {
      cy.get('label[for="num_traces"]').should('be.visible')
      cy.get('#num_traces, input[name="num_traces"]').should('be.visible')
      cy.get('#num_traces, input[name="num_traces"]').should('have.value', '100')
    })

    it('should update trace count input', () => {
      cy.get('#num_traces, input[name="num_traces"]').clear().type('5000')
      cy.get('#num_traces, input[name="num_traces"]').should('have.value', '5000')
    })

    it('should display user count configuration', () => {
      cy.get('label[for="num_users"]').should('be.visible')
      cy.get('#num_users').should('be.visible')
    })

    it('should update user count input', () => {
      cy.get('#num_users').clear().type('250')
      cy.get('#num_users').should('have.value', '250')
    })

    it('should display error rate field', () => {
      cy.get('label[for="error_rate"]').should('be.visible')
      cy.get('#error_rate').should('be.visible')
    })

    it('should show error rate default value', () => {
      cy.get('#error_rate').should('have.value', '0.1')
    })
  })

  describe('Input Validation', () => {
    it('should accept numeric inputs', () => {
      cy.get('#num_traces').clear().type('500')
      cy.get('#num_users').clear().type('50')
      cy.get('#error_rate').clear().type('0.05')
      
      cy.get('#num_traces').should('have.value', '500')
      cy.get('#num_users').should('have.value', '50')
      cy.get('#error_rate').should('have.value', '0.05')
    })

    it('should handle step validation for error rate', () => {
      cy.get('#error_rate').should('have.attr', 'step', '0.01')
    })

    it('should enable generate with valid config', () => {
      cy.get('#num_traces').clear().type('100')
      cy.contains('Generate Data').should('not.be.disabled')
    })

    it('should show proper input types', () => {
      cy.get('#num_traces').should('have.attr', 'type', 'number')
      cy.get('#num_users').should('have.attr', 'type', 'number')
      cy.get('#error_rate').should('have.attr', 'type', 'number')
    })
  })

  describe('Workload Pattern Selection', () => {
    it('should display workload pattern dropdown', () => {
      cy.get('label[for="workload_pattern"]').should('be.visible')
      cy.get('#workload_pattern').should('be.visible')
    })

    it('should show available pattern options', () => {
      cy.get('[data-testid="select-trigger"]').click()
      cy.contains('Default Workload').should('be.visible')
      cy.contains('Cost-Sensitive').should('be.visible')
      cy.contains('Latency-Sensitive').should('be.visible')
      cy.contains('High Error Rate').should('be.visible')
    })

    it('should allow pattern selection', () => {
      cy.get('[data-testid="select-trigger"]').click()
      cy.contains('Cost-Sensitive').click()
      // Close dropdown
      cy.get('body').click(0, 0)
    })

    it('should have default pattern selected', () => {
      cy.get('[data-testid="select-trigger"]')
        .should('contain', 'Default Workload')
    })
  })

  describe('Source Table Configuration', () => {
    it('should display source table selection dropdown', () => {
      cy.get('label[for="source_table"]').should('be.visible')
      cy.get('#source_table').should('be.visible')
    })

    it('should load available source tables on component mount', () => {
      // Component should fetch tables automatically
      cy.get('#source_table').should('be.visible')
    })

    it('should display event types configuration', () => {
      cy.get('label[for="event_types"]').should('be.visible')
      cy.get('#event_types').should('be.visible')
      cy.get('#event_types').should('have.value', 'search,login')
    })

    it('should allow updating event types', () => {
      cy.get('#event_types').clear().type('purchase,checkout,view')
      cy.get('#event_types').should('have.value', 'purchase,checkout,view')
    })
  })

  describe('Generation Process', () => {
    it('should show loading state when generating', () => {
      // Mock a slow API response
      cy.intercept('POST', '**/api/generation/synthetic_data', { delay: 2000, body: { success: true } })
      cy.contains('Generate Data').click()
      cy.contains('Generating...').should('be.visible')
    })

    it('should disable button during generation', () => {
      // Mock a slow API response
      cy.intercept('POST', '**/api/generation/synthetic_data', { delay: 2000, body: { success: true } })
      cy.contains('Generate Data').click()
      cy.get('button').contains('Generating...').should('be.disabled')
    })

    it('should handle successful generation', () => {
      cy.intercept('POST', '**/api/generation/synthetic_data', { body: { success: true } })
      cy.contains('Generate Data').click()
      // Button should be enabled again after completion
      cy.contains('Generate Data').should('not.be.disabled')
    })
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt layout for mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.get('.max-w-2xl').should('be.visible')
      cy.contains('Generate Synthetic Data').should('be.visible')
    })

    it('should maintain grid layout on mobile', () => {
      cy.viewport('iphone-x')
      cy.get('.grid-cols-2').should('be.visible')
    })

    it('should keep full width button on mobile', () => {
      cy.viewport('iphone-x')
      cy.get('button').contains('Generate Data').should('have.class', 'w-full')
    })
  })

  describe('Accessibility Features', () => {
    it('should have proper form labels', () => {
      cy.get('label[for="num_traces"]').should('contain', 'Number of Traces')
      cy.get('label[for="num_users"]').should('contain', 'Number of Users')
      cy.get('label[for="error_rate"]').should('contain', 'Error Rate')
      cy.get('label[for="workload_pattern"]').should('contain', 'Workload Pattern')
    })

    it('should support keyboard navigation between inputs', () => {
      cy.get('#num_traces').focus()
      cy.focused().should('have.id', 'num_traces')
      cy.focused().tab()
      cy.focused().should('have.id', 'num_users')
    })

    it('should have proper input associations', () => {
      cy.get('#num_traces').should('have.attr', 'name', 'num_traces')
      cy.get('#num_users').should('have.attr', 'name', 'num_users')
      cy.get('#error_rate').should('have.attr', 'name', 'error_rate')
    })
  })
})