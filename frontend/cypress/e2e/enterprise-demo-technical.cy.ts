/// <reference types="cypress" />

import { EnterpriseDemoUtils, ENTERPRISE_DEMO_CONSTANTS, ENTERPRISE_SELECTORS } from './utils/enterprise-demo-utils'

/**
 * Enterprise Demo Technical Validation Tests
 * 
 * BVJ: Enterprise segment - Technical validation for enterprise decision makers
 * Business Goal: Validate technical capabilities for CTO/Engineering leadership
 * Value Impact: Ensures technical stakeholders can validate platform capabilities
 * Revenue Impact: Reduces technical objections in enterprise sales process
 */

describe('Enterprise Demo - Technical Validation', () => {
  beforeEach(() => {
    EnterpriseDemoUtils.setupDemoPage()
  })

  describe('Technical Specifications', () => {
    it('should display technical specs section', () => {
      cy.contains('Technical Specifications').should('be.visible')
      cy.get('[data-testid="spec-category"]').should('have.length.at.least', 4)
    })

    it('should show infrastructure requirements', () => {
      cy.contains('Infrastructure').should('be.visible')
      ENTERPRISE_DEMO_CONSTANTS.DEPLOYMENT_OPTIONS.forEach(option => {
        cy.contains(option).should('be.visible')
      })
    })

    it('should display supported platforms', () => {
      cy.contains('Supported Platforms').should('be.visible')
      ENTERPRISE_DEMO_CONSTANTS.PLATFORMS.forEach(platform => {
        cy.contains(platform).should('be.visible')
      })
    })

    it('should show API documentation link', () => {
      cy.contains('API Documentation').should('have.attr', 'href', '/docs/api')
    })
  })

  describe('Compliance and Certifications', () => {
    it('should display compliance badges', () => {
      cy.contains('Compliance').should('be.visible')
      EnterpriseDemoUtils.verifyComplianceBadges()
    })

    it('should show certification details on click', () => {
      cy.contains('SOC 2').click()
      cy.get('[data-testid="cert-modal"]').should('be.visible')
      cy.contains('Type II').should('be.visible')
    })

    it('should link to compliance documentation', () => {
      cy.contains('Compliance Documentation').should('have.attr', 'href')
    })

    it('should display data residency options', () => {
      cy.contains('Data Residency').should('be.visible')
      ENTERPRISE_DEMO_CONSTANTS.DATA_RESIDENCY.forEach(region => {
        cy.contains(region).should('be.visible')
      })
    })
  })

  describe('Resource Center', () => {
    it('should display resource links', () => {
      cy.contains('Resources').should('be.visible')
      cy.contains('Whitepapers').should('be.visible')
      cy.contains('Webinars').should('be.visible')
      cy.contains('Documentation').should('be.visible')
    })

    it('should show downloadable resources', () => {
      cy.contains('Download Whitepaper').should('be.visible')
      cy.contains('ROI Guide').should('be.visible')
      cy.contains('Implementation Guide').should('be.visible')
    })

    it('should require form for downloads', () => {
      cy.contains('Download Whitepaper').click()
      cy.get('[data-testid="download-form"]').should('be.visible')
    })

    it('should link to video demos', () => {
      cy.contains('Watch Demo').should('have.attr', 'href')
    })
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt to mobile viewport', () => {
      EnterpriseDemoUtils.setupMobileView()
      cy.contains('Enterprise AI Optimization').should('be.visible')
      cy.get(ENTERPRISE_SELECTORS.mobileMenu).should('be.visible')
    })

    it('should stack features on mobile', () => {
      EnterpriseDemoUtils.setupMobileView()
      cy.get('[data-testid="feature-tile"]').should('have.css', 'width', '100%')
    })

    it('should show mobile-optimized CTAs', () => {
      EnterpriseDemoUtils.setupMobileView()
      cy.contains('Schedule Demo').should('be.visible')
      cy.get('button').should('have.css', 'width', '100%')
    })

    it('should handle mobile navigation', () => {
      EnterpriseDemoUtils.setupMobileView()
      cy.get(ENTERPRISE_SELECTORS.mobileMenu).click()
      cy.contains('Features').should('be.visible')
      cy.contains('Pricing').should('be.visible')
    })
  })

  describe('Performance and Analytics', () => {
    it('should track page view analytics', () => {
      EnterpriseDemoUtils.verifyAnalyticsTracking()
    })

    it('should track CTA clicks', () => {
      cy.window().then(win => {
        const initialLength = win.dataLayer?.length || 0
        cy.contains('Schedule Demo').click()
        expect(win.dataLayer?.length).to.be.greaterThan(initialLength)
      })
    })

    it('should load within performance budget', () => {
      EnterpriseDemoUtils.verifyPerformanceTiming()
    })

    it('should lazy load heavy components', () => {
      cy.get(ENTERPRISE_SELECTORS.dashboardPreview).scrollIntoView()
      cy.get('[data-testid="dashboard-chart"]').should('be.visible')
    })
  })

  describe('Accessibility', () => {
    it('should have proper heading hierarchy', () => {
      cy.get('h1').should('have.length', 1)
      cy.get('h2').should('have.length.at.least', 5)
    })

    it('should have ARIA labels for interactive elements', () => {
      EnterpriseDemoUtils.verifyARIALabels()
    })

    it('should support keyboard navigation', () => {
      EnterpriseDemoUtils.testKeyboardNavigation()
    })

    it('should have sufficient color contrast', () => {
      cy.get('.text-white').should('have.css', 'background-color')
        .and('not.equal', 'rgb(255, 255, 255)')
    })
  })

  describe('Technical Integration Validation', () => {
    it('should validate API documentation accessibility', () => {
      cy.contains('API Documentation').click()
      cy.url().should('include', '/docs/api')
    })

    it('should verify platform integration examples', () => {
      cy.contains('Supported Platforms').should('be.visible')
      ENTERPRISE_DEMO_CONSTANTS.PLATFORMS.forEach(platform => {
        cy.contains(platform).should('be.visible')
      })
    })

    it('should demonstrate security compliance flow', () => {
      EnterpriseDemoUtils.verifySecurityBadges()
      cy.contains('SOC 2').click()
      cy.get('[data-testid="cert-modal"]').should('be.visible')
    })

    it('should validate resource download workflow', () => {
      cy.contains('Download Whitepaper').click()
      cy.get('[data-testid="download-form"]').should('be.visible')
      cy.get('input[name="email"]').type('tech@example.com')
      cy.get('input[name="company"]').type('Tech Corp')
    })

    it('should ensure cross-device technical consistency', () => {
      // Desktop validation
      cy.contains('Technical Specifications').should('be.visible')
      
      // Mobile validation
      EnterpriseDemoUtils.setupMobileView()
      cy.contains('Technical Specifications').should('be.visible')
      
      // Feature consistency
      cy.get(ENTERPRISE_SELECTORS.mobileMenu).click()
      cy.contains('Resources').should('be.visible')
    })

    it('should validate performance across features', () => {
      // Check initial load
      cy.contains('Technical Specifications').should('be.visible')
      
      // Test lazy loading
      cy.get(ENTERPRISE_SELECTORS.dashboardPreview).scrollIntoView()
      cy.get('[data-testid="dashboard-chart"]').should('be.visible')
      
      // Verify analytics tracking
      EnterpriseDemoUtils.verifyAnalyticsTracking()
    })
  })

  describe('Enterprise Technical Requirements', () => {
    it('should address enterprise deployment options', () => {
      ENTERPRISE_DEMO_CONSTANTS.DEPLOYMENT_OPTIONS.forEach(option => {
        cy.contains(option).should('be.visible')
      })
    })

    it('should provide technical documentation access', () => {
      cy.contains('API Documentation').should('be.visible')
      cy.contains('Implementation Guide').should('be.visible')
    })

    it('should demonstrate compliance readiness', () => {
      EnterpriseDemoUtils.verifyComplianceBadges()
      ENTERPRISE_DEMO_CONSTANTS.DATA_RESIDENCY.forEach(region => {
        cy.contains(region).should('be.visible')
      })
    })
  })
})