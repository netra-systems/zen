/// <reference types="cypress" />

/**
 * Enterprise Demo Test Utilities
 * 
 * BVJ: Enterprise segment - Shared testing utilities for enterprise demo page
 * Supports sales process validation and enterprise feature testing
 * 
 * Business Value:
 * - Reduces test maintenance overhead
 * - Ensures consistent enterprise demo testing
 * - Supports sales team demo validation
 */

export class EnterpriseDemoUtils {
  /**
   * Setup enterprise demo page with optimal viewport
   */
  static setupDemoPage(): void {
    cy.viewport(1920, 1080)
    cy.visit('/enterprise-demo')
  }

  /**
   * Verify page load basics
   */
  static verifyPageLoad(): void {
    cy.url().should('include', '/enterprise-demo')
    cy.contains('Enterprise AI Optimization Platform').should('be.visible')
  }

  /**
   * Check enterprise security badges
   */
  static verifySecurityBadges(): void {
    cy.contains('SOC 2').should('be.visible')
    cy.contains('ISO 27001').should('be.visible')
    cy.contains('HIPAA').should('be.visible')
  }

  /**
   * Verify executive messaging present
   */
  static verifyExecutiveMessaging(): void {
    cy.contains('Transform Your AI Infrastructure').should('be.visible')
    cy.contains('Enterprise-Grade').should('be.visible')
    cy.contains('ROI').should('be.visible')
  }

  /**
   * Open and verify demo scheduling form
   */
  static openDemoForm(): void {
    cy.contains('Schedule Demo').click()
    cy.get('[data-testid="demo-form"]').should('be.visible')
  }

  /**
   * Fill demo form with test data
   */
  static fillDemoForm(): void {
    cy.get('input[name="company"]').type('Test Corp')
    cy.get('input[name="email"]').type('test@example.com')
    cy.get('input[name="name"]').type('John Doe')
  }

  /**
   * Submit demo form and verify success
   */
  static submitDemoForm(): void {
    cy.get('button[type="submit"]').click()
    cy.contains('Thank you').should('be.visible')
  }

  /**
   * Verify metric cards are displayed
   */
  static verifyMetricCards(minCount: number = 4): void {
    cy.get('[data-testid="metric-card"]').should('have.length.at.least', minCount)
  }

  /**
   * Check for interactive dashboard elements
   */
  static verifyDashboardInteractivity(): void {
    cy.get('[data-testid="date-range-selector"]').should('be.visible')
    cy.get('[data-testid="metric-filter"]').should('be.visible')
  }

  /**
   * Verify enterprise feature tiles
   */
  static verifyFeatureTiles(minCount: number = 6): void {
    cy.get('[data-testid="feature-tile"]').should('have.length.at.least', minCount)
  }

  /**
   * Navigate testimonial carousel
   */
  static navigateTestimonials(): void {
    cy.get('[aria-label="Next testimonial"]').click()
    cy.wait(500)
    cy.get('[aria-label="Previous testimonial"]').click()
  }

  /**
   * Verify compliance badges
   */
  static verifyComplianceBadges(minCount: number = 6): void {
    cy.get('[data-testid="compliance-badge"]').should('have.length.at.least', minCount)
  }

  /**
   * Test mobile responsiveness setup
   */
  static setupMobileView(): void {
    cy.viewport('iphone-x')
  }

  /**
   * Track analytics event
   */
  static trackAnalyticsEvent(eventName: string): void {
    cy.window().then(win => {
      const initialLength = win.dataLayer?.length || 0
      return initialLength
    }).as('initialAnalytics')
  }

  /**
   * Verify analytics tracking
   */
  static verifyAnalyticsTracking(): void {
    cy.window().then(win => {
      expect(win.dataLayer).to.exist
    })
  }

  /**
   * Check performance timing
   */
  static verifyPerformanceTiming(): void {
    cy.visit('/enterprise-demo', {
      onBeforeLoad: (win) => {
        win.performance.mark('start')
      },
      onLoad: (win) => {
        win.performance.mark('end')
        win.performance.measure('load', 'start', 'end')
        const measure = win.performance.getEntriesByType('measure')[0]
        expect(measure.duration).to.be.lessThan(4000)
      }
    })
  }

  /**
   * Test keyboard navigation
   */
  static testKeyboardNavigation(): void {
    cy.get('body').tab()
    cy.focused().should('have.attr', 'href').or('have.attr', 'type', 'button')
  }

  /**
   * Verify ARIA accessibility
   */
  static verifyARIALabels(minCount: number = 5): void {
    cy.get('button[aria-label]').should('have.length.at.least', minCount)
  }
}

/**
 * Enterprise Demo Constants
 */
export const ENTERPRISE_DEMO_CONSTANTS = {
  PHASES: ['Discovery', 'Pilot', 'Rollout', 'Optimization'],
  PLATFORMS: ['AWS', 'Azure', 'GCP'],
  DEPLOYMENT_OPTIONS: ['Cloud', 'On-premises', 'Hybrid'],
  DATA_RESIDENCY: ['US', 'EU', 'APAC'],
  PRICING_TIERS: ['Professional', 'Enterprise', 'Enterprise Plus'],
  CASE_STUDY_METRICS: [
    '75% Cost Reduction',
    '10x Performance', 
    '2 Week Implementation'
  ]
}

/**
 * Enterprise Demo Selectors
 */
export const ENTERPRISE_SELECTORS = {
  metricCard: '[data-testid="metric-card"]',
  featureTile: '[data-testid="feature-tile"]',
  testimonialCard: '[data-testid="testimonial-card"]',
  complianceBadge: '[data-testid="compliance-badge"]',
  demoForm: '[data-testid="demo-form"]',
  dashboardPreview: '[data-testid="dashboard-preview"]',
  pricingTier: '[data-testid="pricing-tier"]',
  timelinePhase: '[data-testid="timeline-phase"]',
  mobileMenu: '[data-testid="mobile-menu"]',
  salesModal: '[data-testid="sales-modal"]'
}