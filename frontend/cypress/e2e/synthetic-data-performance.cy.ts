/// <reference types="cypress" />
import { SyntheticDataUtils, SyntheticDataSelectors, SyntheticDataExpectations } from './synthetic-data-utils'

/**
 * Performance, validation, responsive design, and error handling tests
 * Ensures system reliability and quality under various conditions
 */

describe('Synthetic Data Performance and Validation', () => {
  beforeEach(() => {
    SyntheticDataUtils.setupEcommerce()
  })

  describe('Real-time Updates and Performance', () => {
    it('should handle rapid generation requests', () => {
      for (let i = 0; i < 3; i++) {
        cy.contains('Generate').click()
        cy.wait(100)
      }
      cy.get(SyntheticDataSelectors.samples).should('exist')
    })

    it('should maintain UI responsiveness during generation', () => {
      cy.contains('Generate').click()
      SyntheticDataUtils.switchToExplorer()
      cy.contains('Interactive Data Explorer').should('be.visible')
    })

    it('should update timestamps correctly', () => {
      cy.get(SyntheticDataSelectors.sampleTimestamp).first().invoke('text').then((initial) => {
        cy.wait(1000)
        SyntheticDataUtils.generateData()
        cy.get(SyntheticDataSelectors.sampleTimestamp).first().invoke('text').should('not.equal', initial)
      })
    })

    it('should handle concurrent user interactions', () => {
      cy.contains('Generate').click()
      SyntheticDataUtils.switchToSchema()
      cy.wait(500)
      SyntheticDataUtils.switchToExplorer()
      cy.contains('Interactive Data Explorer').should('be.visible')
    })

    it('should throttle excessive generation requests', () => {
      SyntheticDataUtils.generateMultiple(10)
      cy.get(SyntheticDataSelectors.samples).should('have.length.lessThan', SyntheticDataExpectations.maxSampleLimit)
    })
  })

  describe('Data Validation and Quality', () => {
    it('should generate valid JSON data', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).invoke('text').then((jsonText) => {
        SyntheticDataUtils.validateJsonFormat(jsonText)
      })
    })

    it('should include all required fields', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'session_id')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'user_id')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'recommendations')
    })

    it('should generate realistic data ranges', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).invoke('text').then((jsonText) => {
        const data = JSON.parse(jsonText)
        if (data.cart_value) {
          SyntheticDataUtils.validateDataRange(
            parseFloat(data.cart_value),
            SyntheticDataExpectations.minCartValue,
            SyntheticDataExpectations.maxCartValue
          )
        }
        if (data.products_viewed) {
          SyntheticDataUtils.validateDataRange(
            data.products_viewed,
            SyntheticDataExpectations.minProductsViewed,
            SyntheticDataExpectations.maxProductsViewed
          )
        }
      })
    })

    it('should maintain data consistency', () => {
      cy.get(SyntheticDataSelectors.samples).each(($sample) => {
        cy.wrap($sample).click()
        cy.get(SyntheticDataSelectors.jsonPreview).invoke('text').then((jsonText) => {
          const data = JSON.parse(jsonText)
          expect(data).to.have.property('session_id')
          expect(data.session_id).to.include('SES-')
        })
      })
    })

    it('should validate data types and formats', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).invoke('text').then((jsonText) => {
        const data = JSON.parse(jsonText)
        expect(data.timestamp).to.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
        expect(data.data_type).to.be.oneOf(['inference', 'training', 'preprocessing', 'evaluation'])
      })
    })

    it('should ensure unique identifiers', () => {
      const sessionIds = new Set()
      cy.get(SyntheticDataSelectors.samples).each(($sample) => {
        cy.wrap($sample).click()
        cy.get(SyntheticDataSelectors.jsonPreview).invoke('text').then((jsonText) => {
          const data = JSON.parse(jsonText)
          expect(sessionIds.has(data.session_id)).to.be.false
          sessionIds.add(data.session_id)
        })
      })
    })
  })

  describe('Responsive Design', () => {
    it('should adapt to mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.contains('Synthetic Data Generation').should('be.visible')
      cy.get(SyntheticDataSelectors.samples).should('be.visible')
    })

    it('should stack statistics cards on mobile', () => {
      cy.viewport('iphone-x')
      cy.get('.grid-cols-2').should('exist')
    })

    it('should maintain functionality on tablet', () => {
      cy.viewport('ipad-2')
      SyntheticDataUtils.generateData()
      cy.get(SyntheticDataSelectors.samples).should('have.length.at.least', 2)
    })

    it('should adjust layout for small screens', () => {
      cy.viewport(768, 1024)
      cy.get('.grid').should('exist')
      cy.contains('Generate').should('be.visible')
    })

    it('should maintain touch interactions on mobile', () => {
      cy.viewport('iphone-x')
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).should('be.visible')
    })
  })

  describe('Error Handling', () => {
    it('should handle generation failures gracefully', () => {
      cy.intercept('POST', '/api/generate-data', { statusCode: 500 })
      cy.contains('Generate').click()
      cy.wait(1000)
      cy.get(SyntheticDataSelectors.samples).should('exist')
    })

    it('should handle export failures', () => {
      cy.window().then((win) => {
        cy.stub(win.URL, 'createObjectURL').throws(new Error('Export failed'))
      })
      cy.get(SyntheticDataSelectors.exportButton).click()
      cy.on('fail', (err) => {
        expect(err.message).to.include('Export')
        return false
      })
    })

    it('should validate data before display', () => {
      cy.get(SyntheticDataSelectors.samples).each(($sample) => {
        cy.wrap($sample).should('contain', 'ID:')
        cy.wrap($sample).should('contain', 'Processing:')
        cy.wrap($sample).should('contain', 'Points:')
      })
    })

    it('should handle network timeouts', () => {
      cy.intercept('POST', '/api/generate-data', { delay: 30000 })
      cy.contains('Generate').click()
      cy.get('.loading-spinner, .animate-spin').should('be.visible')
    })

    it('should recover from JSON parsing errors', () => {
      cy.intercept('GET', '/api/sample-data', { body: 'invalid-json' })
      cy.reload()
      cy.contains('Error loading data').should('be.visible')
    })

    it('should handle missing data gracefully', () => {
      cy.intercept('GET', '/api/sample-data', { body: [] })
      cy.reload()
      cy.contains('No data available').should('be.visible')
    })
  })

  describe('Performance Benchmarks', () => {
    it('should generate data within acceptable time limits', () => {
      const startTime = Date.now()
      SyntheticDataUtils.generateData()
      const endTime = Date.now()
      expect(endTime - startTime).to.be.lessThan(5000)
    })

    it('should handle large datasets efficiently', () => {
      SyntheticDataUtils.generateMultiple(5)
      cy.get(SyntheticDataSelectors.samples).should('have.length.at.least', 5)
      cy.get('body').should('not.have.class', 'loading')
    })

    it('should maintain smooth scrolling with many samples', () => {
      SyntheticDataUtils.generateMultiple(10)
      cy.scrollTo('bottom')
      cy.scrollTo('top')
      cy.get(SyntheticDataSelectors.samples).first().should('be.visible')
    })

    it('should optimize memory usage', () => {
      SyntheticDataUtils.generateMultiple(20)
      cy.get(SyntheticDataSelectors.samples).should('have.length.lessThan', SyntheticDataExpectations.maxSampleLimit)
    })
  })
})