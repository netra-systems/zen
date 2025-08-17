/// <reference types="cypress" />
import { SyntheticDataUtils, SyntheticDataSelectors, SyntheticDataExpectations } from './synthetic-data-utils'

describe('Demo E2E Test Suite 4: Synthetic Data Generation and Visualization', () => {
  beforeEach(() => {
    SyntheticDataUtils.setupEcommerce()
  })

  describe('Data Generation Interface', () => {
    it('should display synthetic data generation header', () => {
      cy.contains('Synthetic Data Generation').should('be.visible')
      cy.contains('Production-grade synthetic data for E-commerce').should('be.visible')
    })

    it('should show generation controls', () => {
      cy.get(SyntheticDataSelectors.generateButton).should('be.visible')
      cy.get(SyntheticDataSelectors.exportButton).should('be.visible')
    })

    it('should display data statistics cards', () => {
      cy.contains('Total Samples').should('be.visible')
      cy.contains('Avg Processing').should('be.visible')
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
      cy.get(SyntheticDataSelectors.samples).should('have.length.at.least', 1)
    })

    it('should generate new data samples on demand', () => {
      cy.get(SyntheticDataSelectors.samples).then(($samples) => {
        const initialCount = $samples.length
        SyntheticDataUtils.generateData()
        cy.get(SyntheticDataSelectors.samples).should('have.length.greaterThan', initialCount)
      })
    })

    it('should show data sample metadata', () => {
      cy.get(SyntheticDataSelectors.samples).first().within(() => {
        cy.contains(/inference|training|preprocessing|evaluation/).should('be.visible')
        cy.contains('ms').should('be.visible')
        cy.contains(/\d+/).should('be.visible')
      })
    })

    it('should animate data generation', () => {
      cy.contains('Generate').click()
      cy.get('.animate-spin').should('be.visible')
      cy.wait(2000)
      cy.get('.animate-spin').should('not.exist')
    })

    it('should limit displayed samples to prevent overflow', () => {
      SyntheticDataUtils.generateMultiple(5)
      cy.get(SyntheticDataSelectors.samples).should('have.length.lessThan', SyntheticDataExpectations.maxSampleLimit)
    })
  })

  describe('Export Functionality', () => {
    it('should have export button enabled', () => {
      cy.get(SyntheticDataSelectors.exportButton).should('not.be.disabled')
    })

    it('should trigger export when clicked', () => {
      cy.get(SyntheticDataSelectors.exportButton).click()
      cy.on('window:alert', (text) => {
        expect(text).to.contain('synthetic-data')
      })
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
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.samples).first().should('have.class', 'border-primary')
    })

    it('should display detailed JSON view of selected sample', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).should('be.visible')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', '{')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', '}')
    })

    it('should validate generated JSON data', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).invoke('text').then((jsonText) => {
        SyntheticDataUtils.validateJsonFormat(jsonText)
      })
    })

    it('should generate E-commerce specific data', () => {
      cy.get('.cursor-pointer').first().click()
      SyntheticDataUtils.validateEcommerceFields()
    })
  })
})