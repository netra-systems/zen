/// <reference types="cypress" />
import { SyntheticDataUtils, SyntheticDataSelectors, SyntheticDataExpectations } from './synthetic-data-utils'

/**
 * Data inspection, exploration, and schema viewing tests
 * Covers detailed data analysis and visualization features
 */

describe('Synthetic Data Inspection and Analysis', () => {
  beforeEach(() => {
    SyntheticDataUtils.setupEcommerce()
  })

  describe('Data Sample Inspection', () => {
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

    it('should allow copying sample data', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.copyButton).click()
      cy.contains('Copied').should('be.visible')
      cy.wait(2000)
      cy.contains('Copied').should('not.exist')
    })

    it('should format JSON data properly', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).should('have.class', 'font-mono')
      cy.get(SyntheticDataSelectors.jsonPreview).invoke('text').should('match', /\s{2}/)
    })

    it('should highlight selected sample', () => {
      SyntheticDataUtils.selectSampleByIndex(1)
      cy.get(SyntheticDataSelectors.samples).eq(1).should('have.class', 'border-primary')
    })

    it('should display sample metadata', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'timestamp')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'data_type')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'processing_time')
    })
  })

  describe('Data Explorer Tab', () => {
    it('should switch to data explorer view', () => {
      SyntheticDataUtils.switchToExplorer()
      cy.contains('Interactive Data Explorer').should('be.visible')
    })

    it('should show filtering instructions', () => {
      SyntheticDataUtils.switchToExplorer()
      cy.contains('JSON path expressions').should('be.visible')
      cy.contains('$.user_behavior.conversion_likelihood').should('be.visible')
    })

    it('should display data samples in explorer format', () => {
      SyntheticDataUtils.switchToExplorer()
      cy.get(SyntheticDataSelectors.explorerSample).should('have.length.at.least', 1)
    })

    it('should show truncated data preview', () => {
      SyntheticDataUtils.switchToExplorer()
      cy.get(SyntheticDataSelectors.explorerSample).first().within(() => {
        cy.contains('[Object]').should('be.visible')
      })
    })

    it('should allow filtering by data type', () => {
      SyntheticDataUtils.switchToExplorer()
      cy.get('input[placeholder*="filter"]').type('inference')
      cy.get(SyntheticDataSelectors.explorerSample).should('contain', 'inference')
    })

    it('should display sample count in explorer', () => {
      SyntheticDataUtils.switchToExplorer()
      cy.contains('samples found').should('be.visible')
      cy.contains(/\d+ samples found/).should('be.visible')
    })
  })

  describe('Schema View Tab', () => {
    it('should switch to schema view', () => {
      SyntheticDataUtils.switchToSchema()
      cy.contains('Data Schema').should('be.visible')
    })

    it('should display JSON schema', () => {
      SyntheticDataUtils.switchToSchema()
      cy.contains('$schema').should('be.visible')
      cy.contains('properties').should('be.visible')
      cy.contains('required').should('be.visible')
    })

    it('should show industry-specific schema', () => {
      SyntheticDataUtils.switchToSchema()
      cy.contains('E-commerce Synthetic Data Schema').should('be.visible')
    })

    it('should display field types and descriptions', () => {
      SyntheticDataUtils.switchToSchema()
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'type')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'description')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'required')
    })

    it('should show schema validation rules', () => {
      SyntheticDataUtils.switchToSchema()
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'minimum')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'maximum')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'pattern')
    })

    it('should display nested object schemas', () => {
      SyntheticDataUtils.switchToSchema()
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'user_behavior')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'recommendations')
    })
  })

  describe('Data Statistics and Metrics', () => {
    it('should update statistics after generation', () => {
      cy.contains('Total Samples').parent().invoke('text').then((initial) => {
        SyntheticDataUtils.generateData()
        cy.contains('Total Samples').parent().invoke('text').should('not.equal', initial)
      })
    })

    it('should calculate average processing time', () => {
      cy.get(SyntheticDataSelectors.statAvgProcessing).should('contain', 'ms')
      cy.get(SyntheticDataSelectors.statAvgProcessing).invoke('text').then((text) => {
        const time = parseInt(text)
        SyntheticDataUtils.validateDataRange(
          time, 
          SyntheticDataExpectations.minProcessingTime,
          SyntheticDataExpectations.maxProcessingTime
        )
      })
    })

    it('should track total data points', () => {
      cy.get(SyntheticDataSelectors.statDataPoints).should('contain', 'K')
      SyntheticDataUtils.generateData()
      cy.get(SyntheticDataSelectors.statDataPoints).invoke('text').then((text) => {
        const points = parseFloat(text)
        expect(points).to.be.greaterThan(0)
      })
    })

    it('should count unique data types', () => {
      cy.get(SyntheticDataSelectors.statDataTypes).invoke('text').then((text) => {
        const types = parseInt(text)
        SyntheticDataUtils.validateDataRange(
          types,
          SyntheticDataExpectations.minDataTypes,
          SyntheticDataExpectations.maxDataTypes
        )
      })
    })

    it('should display processing efficiency metrics', () => {
      cy.contains('Avg Processing').should('be.visible')
      cy.contains('Data Points').should('be.visible')
      cy.contains('Generation Rate').should('be.visible')
    })

    it('should show real-time statistics updates', () => {
      cy.get(SyntheticDataSelectors.statTotalSamples).invoke('text').then((initial) => {
        SyntheticDataUtils.generateData()
        cy.get(SyntheticDataSelectors.statTotalSamples).invoke('text').should('not.equal', initial)
      })
    })
  })

  describe('Advanced Data Analysis', () => {
    it('should provide data quality metrics', () => {
      SyntheticDataUtils.switchToExplorer()
      cy.contains('Data Quality').should('be.visible')
      cy.contains('Completeness').should('be.visible')
      cy.contains('Validity').should('be.visible')
    })

    it('should show data distribution charts', () => {
      SyntheticDataUtils.switchToExplorer()
      cy.get('canvas, svg').should('exist') // Chart elements
    })

    it('should allow data export from explorer', () => {
      SyntheticDataUtils.switchToExplorer()
      cy.contains('Export Filtered').should('be.visible')
      cy.contains('Export Filtered').click()
    })

    it('should display field statistics', () => {
      SyntheticDataUtils.switchToExplorer()
      cy.contains('Field Analysis').should('be.visible')
      cy.contains('Unique Values').should('be.visible')
      cy.contains('Null Count').should('be.visible')
    })
  })
})