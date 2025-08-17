/// <reference types="cypress" />
import { SyntheticDataUtils, SyntheticDataSelectors } from './synthetic-data-utils'

/**
 * Industry-specific synthetic data generation tests
 * Tests data generation across different industry verticals
 */

describe('Synthetic Data Industry-Specific Generation', () => {
  beforeEach(() => {
    SyntheticDataUtils.setupViewport()
  })

  describe('E-commerce Industry Data', () => {
    beforeEach(() => {
      SyntheticDataUtils.navigateToDemo()
      SyntheticDataUtils.selectIndustry('E-commerce')
    })

    it('should generate E-commerce specific data fields', () => {
      cy.get('.cursor-pointer').first().click()
      SyntheticDataUtils.validateEcommerceFields()
    })

    it('should include commerce-specific metadata', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'cart_value')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'product_category')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'user_segment')
    })

    it('should generate realistic e-commerce data ranges', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).invoke('text').then((jsonText) => {
        const data = JSON.parse(jsonText)
        if (data.cart_value) {
          SyntheticDataUtils.validateDataRange(
            parseFloat(data.cart_value), 
            0, 
            10000
          )
        }
      })
    })

    it('should maintain session consistency', () => {
      cy.get(SyntheticDataSelectors.samples).each(($sample) => {
        cy.wrap($sample).click()
        cy.get(SyntheticDataSelectors.jsonPreview).invoke('text').then((jsonText) => {
          const data = JSON.parse(jsonText)
          expect(data).to.have.property('session_id')
          expect(data.session_id).to.include('SES-')
        })
      })
    })
  })

  describe('Healthcare Industry Data', () => {
    beforeEach(() => {
      SyntheticDataUtils.navigateToDemo()
      SyntheticDataUtils.selectIndustry('Healthcare')
    })

    it('should generate Healthcare specific data fields', () => {
      cy.get('.cursor-pointer').first().click()
      SyntheticDataUtils.validateHealthcareFields()
    })

    it('should include medical-specific metadata', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'patient_id')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'medical_record')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'treatment_plan')
    })

    it('should generate compliant patient identifiers', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).invoke('text').then((jsonText) => {
        const data = JSON.parse(jsonText)
        expect(data).to.have.property('patient_id')
        expect(data.patient_id).to.include('PAT-')
      })
    })

    it('should include vital signs data', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'vital_signs')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'blood_pressure')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'heart_rate')
    })
  })

  describe('Financial Services Industry Data', () => {
    beforeEach(() => {
      SyntheticDataUtils.navigateToDemo()
      SyntheticDataUtils.selectIndustry('Financial Services')
    })

    it('should generate Financial Services specific data fields', () => {
      cy.get('.cursor-pointer').first().click()
      SyntheticDataUtils.validateFinancialFields()
    })

    it('should include financial-specific metadata', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'transaction_id')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'account_type')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'compliance_status')
    })

    it('should generate valid transaction identifiers', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).invoke('text').then((jsonText) => {
        const data = JSON.parse(jsonText)
        expect(data).to.have.property('transaction_id')
        expect(data.transaction_id).to.include('TXN-')
      })
    })

    it('should include risk assessment data', () => {
      SyntheticDataUtils.selectFirstSample()
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'risk_score')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'fraud_probability')
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'credit_rating')
    })
  })

  describe('Cross-Industry Data Quality', () => {
    const industries = ['E-commerce', 'Healthcare', 'Financial Services']

    industries.forEach((industry) => {
      it(`should generate consistent data structure for ${industry}`, () => {
        SyntheticDataUtils.navigateToDemo()
        SyntheticDataUtils.selectIndustry(industry)
        
        SyntheticDataUtils.selectFirstSample()
        cy.get(SyntheticDataSelectors.jsonPreview).invoke('text').then((jsonText) => {
          SyntheticDataUtils.validateJsonFormat(jsonText)
          const data = JSON.parse(jsonText)
          expect(data).to.have.property('timestamp')
          expect(data).to.have.property('data_type')
        })
      })
    })

    it('should maintain industry context across generations', () => {
      SyntheticDataUtils.navigateToDemo()
      SyntheticDataUtils.selectIndustry('Healthcare')
      
      SyntheticDataUtils.generateData()
      cy.get(SyntheticDataSelectors.samples).first().click()
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'patient_id')
      
      SyntheticDataUtils.generateData()
      cy.get(SyntheticDataSelectors.samples).first().click()
      cy.get(SyntheticDataSelectors.jsonPreview).should('contain', 'patient_id')
    })
  })

  describe('Industry Schema Validation', () => {
    it('should display industry-specific schema in Schema View', () => {
      SyntheticDataUtils.setupEcommerce()
      SyntheticDataUtils.switchToSchema()
      cy.contains('E-commerce Synthetic Data Schema').should('be.visible')
    })

    it('should show healthcare schema when switched', () => {
      SyntheticDataUtils.navigateToDemo()
      SyntheticDataUtils.selectIndustry('Healthcare')
      SyntheticDataUtils.switchToSchema()
      cy.contains('Healthcare Synthetic Data Schema').should('be.visible')
    })

    it('should display financial schema appropriately', () => {
      SyntheticDataUtils.navigateToDemo()
      SyntheticDataUtils.selectIndustry('Financial Services')
      SyntheticDataUtils.switchToSchema()
      cy.contains('Financial Services Synthetic Data Schema').should('be.visible')
    })
  })
})