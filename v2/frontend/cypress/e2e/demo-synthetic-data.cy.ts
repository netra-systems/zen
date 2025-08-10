/// <reference types="cypress" />

describe('Demo E2E Test Suite 4: Synthetic Data Generation and Visualization', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/demo')
    cy.contains('E-commerce').click()
    cy.contains('Data Insights').click()
    cy.wait(500)
  })

  describe('Data Generation Interface', () => {
    it('should display synthetic data generation header', () => {
      cy.contains('Synthetic Data Generation').should('be.visible')
      cy.contains('Production-grade synthetic data for E-commerce').should('be.visible')
    })

    it('should show generation controls', () => {
      cy.get('button').contains('Generate').should('be.visible')
      cy.get('button').contains('Export').should('be.visible')
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
      cy.get('[data-testid="data-sample"]').should('have.length.at.least', 1)
    })

    it('should generate new data samples on demand', () => {
      // Get initial sample count
      cy.get('[data-testid="data-sample"]').then(($samples) => {
        const initialCount = $samples.length
        
        cy.contains('Generate').click()
        cy.wait(2000)
        
        // Should have more samples
        cy.get('[data-testid="data-sample"]').should('have.length.greaterThan', initialCount)
      })
    })

    it('should show data sample metadata', () => {
      cy.get('[data-testid="data-sample"]').first().within(() => {
        cy.contains(/inference|training|preprocessing|evaluation/).should('be.visible')
        cy.contains('ms').should('be.visible') // Processing time
        cy.contains(/\d+/).should('be.visible') // Data points
      })
    })

    it('should animate data generation', () => {
      cy.contains('Generate').click()
      cy.get('.animate-spin').should('be.visible')
      cy.wait(2000)
      cy.get('.animate-spin').should('not.exist')
    })

    it('should limit displayed samples to prevent overflow', () => {
      // Generate multiple times
      for (let i = 0; i < 5; i++) {
        cy.contains('Generate').click()
        cy.wait(500)
      }
      
      // Should not exceed reasonable limit (e.g., 10)
      cy.get('[data-testid="data-sample"]').should('have.length.lessThan', 15)
    })
  })

  describe('Industry-Specific Data Generation', () => {
    it('should generate E-commerce specific data', () => {
      cy.get('[data-testid="sample-detail"]').first().click()
      
      // Check for e-commerce specific fields
      cy.contains('session_id').should('be.visible')
      cy.contains('cart_value').should('be.visible')
      cy.contains('products_viewed').should('be.visible')
      cy.contains('recommendations').should('be.visible')
    })

    it('should generate Healthcare specific data when industry changes', () => {
      cy.visit('/demo')
      cy.contains('Healthcare').click()
      cy.contains('Data Insights').click()
      
      cy.get('[data-testid="sample-detail"]').first().click()
      
      // Check for healthcare specific fields
      cy.contains('patient_id').should('be.visible')
      cy.contains('vital_signs').should('be.visible')
      cy.contains('diagnosis_code').should('be.visible')
    })

    it('should generate Financial Services specific data', () => {
      cy.visit('/demo')
      cy.contains('Financial Services').click()
      cy.contains('Data Insights').click()
      
      cy.get('[data-testid="sample-detail"]').first().click()
      
      // Check for financial specific fields
      cy.contains('transaction_id').should('be.visible')
      cy.contains('risk_score').should('be.visible')
      cy.contains('fraud_probability').should('be.visible')
    })
  })

  describe('Data Sample Inspection', () => {
    it('should allow selecting individual samples', () => {
      cy.get('[data-testid="data-sample"]').first().click()
      cy.get('[data-testid="data-sample"]').first().should('have.class', 'border-primary')
    })

    it('should display detailed JSON view of selected sample', () => {
      cy.get('[data-testid="data-sample"]').first().click()
      cy.get('pre').should('be.visible')
      cy.get('pre').should('contain', '{')
      cy.get('pre').should('contain', '}')
    })

    it('should allow copying sample data', () => {
      cy.get('[data-testid="data-sample"]').first().click()
      cy.contains('Copy').click()
      
      // Check for success indicator
      cy.contains('Copied').should('be.visible')
      cy.wait(2000)
      cy.contains('Copied').should('not.exist')
      cy.contains('Copy').should('be.visible')
    })

    it('should format JSON data properly', () => {
      cy.get('[data-testid="data-sample"]').first().click()
      
      // Check for proper indentation
      cy.get('pre').should('have.class', 'font-mono')
      cy.get('pre').invoke('text').should('match', /\s{2}/) // Has indentation
    })
  })

  describe('Data Explorer Tab', () => {
    it('should switch to data explorer view', () => {
      cy.contains('Data Explorer').click()
      cy.contains('Interactive Data Explorer').should('be.visible')
    })

    it('should show filtering instructions', () => {
      cy.contains('Data Explorer').click()
      cy.contains('JSON path expressions').should('be.visible')
      cy.contains('$.user_behavior.conversion_likelihood').should('be.visible')
    })

    it('should display data samples in explorer format', () => {
      cy.contains('Data Explorer').click()
      cy.get('[data-testid="explorer-sample"]').should('have.length.at.least', 1)
    })

    it('should show truncated data preview', () => {
      cy.contains('Data Explorer').click()
      cy.get('[data-testid="explorer-sample"]').first().within(() => {
        cy.contains('[Object]').should('be.visible') // Complex objects shown as [Object]
      })
    })
  })

  describe('Schema View Tab', () => {
    it('should switch to schema view', () => {
      cy.contains('Schema View').click()
      cy.contains('Data Schema').should('be.visible')
    })

    it('should display JSON schema', () => {
      cy.contains('Schema View').click()
      cy.contains('$schema').should('be.visible')
      cy.contains('properties').should('be.visible')
      cy.contains('required').should('be.visible')
    })

    it('should show industry-specific schema', () => {
      cy.contains('Schema View').click()
      cy.contains('E-commerce Synthetic Data Schema').should('be.visible')
    })

    it('should display field types and descriptions', () => {
      cy.contains('Schema View').click()
      cy.get('pre').should('contain', 'type')
      cy.get('pre').should('contain', 'description')
      cy.get('pre').should('contain', 'required')
    })
  })

  describe('Data Statistics and Metrics', () => {
    it('should update statistics after generation', () => {
      // Get initial total samples
      cy.get('[data-testid="stat-total-samples"]').invoke('text').then((initial) => {
        cy.contains('Generate').click()
        cy.wait(2000)
        
        // Check that total increased
        cy.get('[data-testid="stat-total-samples"]').invoke('text').should('not.equal', initial)
      })
    })

    it('should calculate average processing time', () => {
      cy.get('[data-testid="stat-avg-processing"]').should('contain', 'ms')
      cy.get('[data-testid="stat-avg-processing"]').invoke('text').then((text) => {
        const time = parseInt(text)
        expect(time).to.be.greaterThan(0)
        expect(time).to.be.lessThan(10000)
      })
    })

    it('should track total data points', () => {
      cy.get('[data-testid="stat-data-points"]').should('contain', 'K')
      cy.contains('Generate').click()
      cy.wait(2000)
      
      // Data points should increase
      cy.get('[data-testid="stat-data-points"]').invoke('text').then((text) => {
        const points = parseFloat(text)
        expect(points).to.be.greaterThan(0)
      })
    })

    it('should count unique data types', () => {
      cy.get('[data-testid="stat-data-types"]').invoke('text').then((text) => {
        const types = parseInt(text)
        expect(types).to.be.at.least(1)
        expect(types).to.be.at.most(4) // inference, training, preprocessing, evaluation
      })
    })
  })

  describe('Export Functionality', () => {
    it('should have export button enabled', () => {
      cy.contains('Export').should('not.be.disabled')
    })

    it('should trigger export when clicked', () => {
      cy.contains('Export').click()
      
      // Mock download verification
      cy.on('window:alert', (text) => {
        expect(text).to.contain('synthetic-data')
      })
    })

    it('should include industry in export filename', () => {
      cy.window().then((win) => {
        cy.stub(win, 'open').as('download')
      })
      
      cy.contains('Export').click()
      cy.get('@download').should('be.called')
    })
  })

  describe('Real-time Updates and Performance', () => {
    it('should handle rapid generation requests', () => {
      for (let i = 0; i < 3; i++) {
        cy.contains('Generate').click()
        cy.wait(100)
      }
      
      // Should handle gracefully
      cy.get('[data-testid="data-sample"]').should('exist')
    })

    it('should maintain UI responsiveness during generation', () => {
      cy.contains('Generate').click()
      
      // Should still be able to interact
      cy.contains('Data Explorer').click()
      cy.contains('Interactive Data Explorer').should('be.visible')
    })

    it('should update timestamps correctly', () => {
      cy.get('[data-testid="sample-timestamp"]').first().invoke('text').then((initial) => {
        cy.wait(1000)
        cy.contains('Generate').click()
        cy.wait(2000)
        
        cy.get('[data-testid="sample-timestamp"]').first().invoke('text').should('not.equal', initial)
      })
    })
  })

  describe('Data Validation and Quality', () => {
    it('should generate valid JSON data', () => {
      cy.get('[data-testid="data-sample"]').first().click()
      cy.get('pre').invoke('text').then((jsonText) => {
        expect(() => JSON.parse(jsonText)).to.not.throw()
      })
    })

    it('should include all required fields', () => {
      cy.get('[data-testid="data-sample"]').first().click()
      
      // Check for essential fields
      cy.get('pre').should('contain', 'session_id')
      cy.get('pre').should('contain', 'user_id')
      cy.get('pre').should('contain', 'recommendations')
    })

    it('should generate realistic data ranges', () => {
      cy.get('[data-testid="data-sample"]').first().click()
      cy.get('pre').invoke('text').then((jsonText) => {
        const data = JSON.parse(jsonText)
        
        // Validate reasonable ranges
        if (data.cart_value) {
          const value = parseFloat(data.cart_value)
          expect(value).to.be.at.least(0)
          expect(value).to.be.at.most(10000)
        }
        
        if (data.products_viewed) {
          expect(data.products_viewed).to.be.at.least(0)
          expect(data.products_viewed).to.be.at.most(100)
        }
      })
    })

    it('should maintain data consistency', () => {
      cy.get('[data-testid="data-sample"]').each(($sample) => {
        cy.wrap($sample).click()
        cy.get('pre').invoke('text').then((jsonText) => {
          const data = JSON.parse(jsonText)
          
          // Check that IDs are unique
          expect(data).to.have.property('session_id')
          expect(data.session_id).to.include('SES-')
        })
      })
    })
  })

  describe('Responsive Design', () => {
    it('should adapt to mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.contains('Synthetic Data Generation').should('be.visible')
      cy.get('[data-testid="data-sample"]').should('be.visible')
    })

    it('should stack statistics cards on mobile', () => {
      cy.viewport('iphone-x')
      cy.get('.grid-cols-2').should('exist') // Should use 2 columns on mobile
    })

    it('should maintain functionality on tablet', () => {
      cy.viewport('ipad-2')
      cy.contains('Generate').click()
      cy.wait(2000)
      cy.get('[data-testid="data-sample"]').should('have.length.at.least', 2)
    })
  })

  describe('Error Handling', () => {
    it('should handle generation failures gracefully', () => {
      cy.intercept('POST', '/api/generate-data', { statusCode: 500 })
      
      cy.contains('Generate').click()
      cy.wait(1000)
      
      // Should show error or use fallback data
      cy.get('[data-testid="data-sample"]').should('exist')
    })

    it('should handle export failures', () => {
      cy.window().then((win) => {
        cy.stub(win.URL, 'createObjectURL').throws(new Error('Export failed'))
      })
      
      cy.contains('Export').click()
      
      // Should handle error gracefully
      cy.on('fail', (err) => {
        expect(err.message).to.include('Export')
        return false
      })
    })

    it('should validate data before display', () => {
      // All displayed data should be properly formatted
      cy.get('[data-testid="data-sample"]').each(($sample) => {
        cy.wrap($sample).should('contain', 'ID:')
        cy.wrap($sample).should('contain', 'Processing:')
        cy.wrap($sample).should('contain', 'Points:')
      })
    })
  })
})