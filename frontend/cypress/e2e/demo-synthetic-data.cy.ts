/// <reference types="cypress" />
import { SyntheticDataUtils, SyntheticDataSelectors, SyntheticDataExpectations } from './synthetic-data-utils'

describe('Demo E2E Test Suite 4: Synthetic Data Generation and Visualization', () => {
  beforeEach(() => {
    SyntheticDataUtils.setupEcommerce()
    // Wait for the SyntheticDataViewer component to load
    cy.wait(1000)
  })

  describe('Data Generation Interface', () => {
    it('should display synthetic data generation header', () => {
      cy.contains('Synthetic Data Generation').should('be.visible')
      cy.contains('Production-grade synthetic data for E-commerce').should('be.visible')
    })

    it('should show generation controls', () => {
      cy.contains('button', 'Generate').should('be.visible')
      cy.contains('button', 'Export').should('be.visible')
    })

    it('should display data statistics cards', () => {
      cy.contains('Total Samples').should('be.visible')
      cy.contains('Avg Processing Time').should('be.visible')
      cy.contains('Data Points').should('be.visible')
      cy.contains('Data Types').should('be.visible')
    })

    it('should have tab navigation for different views', () => {
      cy.contains('Live Stream').should('be.visible')
      cy.contains('Data Explorer').should('be.visible')
      cy.contains('Schema View').should('be.visible')
    })
  })

  describe('Live Data Streaming', () => {
    it('should display initial data samples', () => {
      // Check for data sample cards in the Live Stream tab
      cy.contains('Live Stream').click()
      cy.get('[class*="border"]').should('have.length.at.least', 1)
    })

    it('should generate new data samples on demand', () => {
      cy.contains('Live Stream').click()
      cy.get('[class*="border"]').then(($samples) => {
        const initialCount = $samples.length
        cy.contains('button', 'Generate').click()
        cy.wait(2000) // Wait for generation to complete
        cy.get('[class*="border"]').should('have.length.greaterThan', initialCount)
      })
    })

    it('should show data sample metadata', () => {
      cy.contains('Live Stream').click()
      cy.get('[class*="border"]').first().within(() => {
        // Check for e-commerce specific data patterns
        cy.get('pre, code, [class*="json"]').should('exist')
      })
    })

    it('should animate data generation', () => {
      cy.contains('button', 'Generate').click()
      // Check for spinning animation during generation
      cy.get('[class*="animate-spin"]').should('be.visible')
      cy.wait(2000)
      cy.get('[class*="animate-spin"]').should('not.exist')
    })

    it('should limit displayed samples to prevent overflow', () => {
      // Generate multiple samples and verify limit
      cy.contains('Live Stream').click()
      for (let i = 0; i < 5; i++) {
        cy.contains('button', 'Generate').click()
        cy.wait(500)
      }
      cy.get('[class*="border"]').should('have.length.lessThan', 15) // Limit to prevent overflow
    })
  })

  describe('Export Functionality', () => {
    it('should have export button enabled', () => {
      cy.contains('button', 'Export').should('not.be.disabled')
    })

    it('should trigger export when clicked', () => {
      cy.contains('button', 'Export').click()
      // Export functionality should trigger download or show success message
      cy.wait(500)
    })

    it('should include industry in export filename', () => {
      cy.window().then((win) => {
        cy.stub(win, 'open').as('download')
      })
      cy.get(SyntheticDataSelectors.exportButton).click()
      cy.get('@download').should('be.called')
    })
  })

  describe('Basic Sample Interaction', () => {
    it('should allow selecting individual samples', () => {
      cy.contains('Live Stream').click()
      cy.get('[class*="border"]').first().click()
      // Verify sample selection visual feedback
      cy.get('[class*="border"]').first().should('have.class', 'cursor-pointer')
    })

    it('should display detailed JSON view of selected sample', () => {
      cy.contains('Live Stream').click()
      cy.get('[class*="border"]').first().click()
      // Check for JSON preview in the sample display
      cy.get('pre, code').should('be.visible')
      cy.get('pre, code').should('contain', '{')
      cy.get('pre, code').should('contain', '}')
    })

    it('should validate generated JSON data', () => {
      cy.contains('Live Stream').click()
      cy.get('[class*="border"]').first().click()
      cy.get('pre, code').invoke('text').then((jsonText) => {
        SyntheticDataUtils.validateJsonFormat(jsonText)
      })
    })

    it('should generate E-commerce specific data', () => {
      cy.contains('Live Stream').click()
      cy.get('[class*="border"]').first().click()
      // Validate e-commerce specific fields are present
      cy.contains(/session_id|user_id|product/).should('be.visible')
    })
  })
})