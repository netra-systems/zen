/// <reference types="cypress" />

import { EnterpriseDemoUtils, ENTERPRISE_DEMO_CONSTANTS, ENTERPRISE_SELECTORS } from './utils/enterprise-demo-utils'

/**
 * Enterprise Demo Sales Enablement Tests
 * 
 * BVJ: Enterprise segment - Sales enablement and conversion validation
 * Business Goal: Validate sales process elements for enterprise prospects
 * Value Impact: Ensures sales team can effectively demonstrate ROI and conversion paths
 * Revenue Impact: Directly supports enterprise sales pipeline and conversion rates
 */

describe('Enterprise Demo - Sales Enablement', () => {
  beforeEach(() => {
    EnterpriseDemoUtils.setupDemoPage()
  })

  describe('Customer Success Stories', () => {
    it('should display testimonial carousel', () => {
      cy.contains('Customer Success').should('be.visible')
      cy.get(ENTERPRISE_SELECTORS.testimonialCard).should('have.length.at.least', 3)
    })

    it('should show Fortune 500 logos', () => {
      cy.get('[data-testid="customer-logo"]').should('have.length.at.least', 5)
    })

    it('should display case study metrics', () => {
      ENTERPRISE_DEMO_CONSTANTS.CASE_STUDY_METRICS.forEach(metric => {
        cy.contains(metric).should('be.visible')
      })
    })

    it('should navigate testimonial carousel', () => {
      EnterpriseDemoUtils.navigateTestimonials()
    })

    it('should link to detailed case studies', () => {
      cy.contains('Read Case Study').should('have.attr', 'href')
    })
  })

  describe('Implementation Timeline', () => {
    it('should display implementation phases', () => {
      cy.contains('Implementation Timeline').should('be.visible')
      cy.get(ENTERPRISE_SELECTORS.timelinePhase).should('have.length', 4)
    })

    it('should show phase details', () => {
      ENTERPRISE_DEMO_CONSTANTS.PHASES.forEach(phase => {
        cy.contains(phase).should('be.visible')
      })
    })

    it('should display timeline duration', () => {
      cy.contains('Week 1-2').should('be.visible')
      cy.contains('Week 3-4').should('be.visible')
      cy.contains('Week 5-8').should('be.visible')
    })

    it('should highlight current phase', () => {
      cy.get('[data-testid="current-phase"]').should('have.class', 'ring-2')
    })

    it('should show phase deliverables on click', () => {
      cy.contains('Discovery').click()
      cy.contains('Requirements Analysis').should('be.visible')
      cy.contains('Architecture Review').should('be.visible')
    })
  })

  describe('Pricing and Packages', () => {
    it('should display enterprise pricing tiers', () => {
      cy.contains('Enterprise Pricing').should('be.visible')
      cy.get(ENTERPRISE_SELECTORS.pricingTier).should('have.length', 3)
    })

    it('should show tier features', () => {
      ENTERPRISE_DEMO_CONSTANTS.PRICING_TIERS.forEach(tier => {
        cy.contains(tier).should('be.visible')
      })
    })

    it('should display custom pricing option', () => {
      cy.contains('Custom Pricing').should('be.visible')
      cy.contains('Contact Sales').should('be.visible')
    })

    it('should highlight recommended tier', () => {
      cy.get('[data-testid="recommended-tier"]').should('have.class', 'scale-105')
    })

    it('should open pricing calculator', () => {
      cy.contains('Calculate Pricing').click()
      cy.get('[data-testid="pricing-calculator"]').should('be.visible')
    })
  })

  describe('Call-to-Action Sections', () => {
    it('should display primary CTA buttons', () => {
      cy.contains('button', 'Schedule Demo').should('be.visible')
      cy.contains('button', 'Request Trial').should('be.visible')
      cy.contains('button', 'Contact Sales').should('be.visible')
    })

    it('should show demo scheduling form', () => {
      EnterpriseDemoUtils.openDemoForm()
      cy.get('input[name="company"]').should('be.visible')
      cy.get('input[name="email"]').should('be.visible')
    })

    it('should validate form inputs', () => {
      EnterpriseDemoUtils.openDemoForm()
      cy.get('button[type="submit"]').click()
      cy.contains('Required').should('be.visible')
    })

    it('should submit demo request', () => {
      EnterpriseDemoUtils.openDemoForm()
      EnterpriseDemoUtils.fillDemoForm()
      EnterpriseDemoUtils.submitDemoForm()
    })

    it('should open contact sales modal', () => {
      cy.contains('Contact Sales').click()
      cy.get(ENTERPRISE_SELECTORS.salesModal).should('be.visible')
      cy.contains('Enterprise Sales Team').should('be.visible')
    })
  })

  describe('Sales Conversion Flow', () => {
    it('should guide from success stories to pricing', () => {
      cy.contains('Customer Success').scrollIntoView()
      EnterpriseDemoUtils.navigateTestimonials()
      cy.contains('Enterprise Pricing').scrollIntoView()
      cy.get(ENTERPRISE_SELECTORS.pricingTier).should('be.visible')
    })

    it('should connect timeline to demo scheduling', () => {
      cy.contains('Implementation Timeline').scrollIntoView()
      cy.contains('Discovery').should('be.visible')
      EnterpriseDemoUtils.openDemoForm()
    })

    it('should link success metrics to ROI calculation', () => {
      ENTERPRISE_DEMO_CONSTANTS.CASE_STUDY_METRICS.forEach(metric => {
        cy.contains(metric).should('be.visible')
      })
      cy.contains('Calculate Pricing').click()
      cy.get('[data-testid="pricing-calculator"]').should('be.visible')
    })

    it('should support sales team demo workflow', () => {
      cy.contains('Customer Success').should('be.visible')
      cy.contains('Implementation Timeline').should('be.visible')
      cy.contains('Enterprise Pricing').should('be.visible')
      cy.contains('Schedule Demo').should('be.visible')
    })

    it('should validate enterprise lead capture', () => {
      EnterpriseDemoUtils.openDemoForm()
      EnterpriseDemoUtils.fillDemoForm()
      cy.get('button[type="submit"]').should('be.enabled')
    })

    it('should demonstrate complete sales journey', () => {
      // Customer proof points
      cy.contains('Customer Success').scrollIntoView()
      cy.get(ENTERPRISE_SELECTORS.testimonialCard).should('be.visible')
      
      // Implementation clarity
      cy.contains('Implementation Timeline').scrollIntoView()
      cy.get(ENTERPRISE_SELECTORS.timelinePhase).should('be.visible')
      
      // Pricing transparency
      cy.contains('Enterprise Pricing').scrollIntoView()
      cy.get(ENTERPRISE_SELECTORS.pricingTier).should('be.visible')
      
      // Call to action
      EnterpriseDemoUtils.openDemoForm()
    })
  })

  describe('Enterprise Sales Analytics', () => {
    it('should track pricing calculator usage', () => {
      EnterpriseDemoUtils.trackAnalyticsEvent('pricing_calculator_open')
      cy.contains('Calculate Pricing').click()
      EnterpriseDemoUtils.verifyAnalyticsTracking()
    })

    it('should track demo form submissions', () => {
      EnterpriseDemoUtils.trackAnalyticsEvent('demo_form_submit')
      EnterpriseDemoUtils.openDemoForm()
      EnterpriseDemoUtils.fillDemoForm()
      EnterpriseDemoUtils.submitDemoForm()
    })

    it('should track sales contact interactions', () => {
      EnterpriseDemoUtils.trackAnalyticsEvent('sales_contact')
      cy.contains('Contact Sales').click()
      cy.get(ENTERPRISE_SELECTORS.salesModal).should('be.visible')
    })
  })
})