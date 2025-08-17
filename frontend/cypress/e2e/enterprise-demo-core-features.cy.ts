/// <reference types="cypress" />

import { EnterpriseDemoUtils, ENTERPRISE_SELECTORS } from './utils/enterprise-demo-utils'

/**
 * Enterprise Demo Core Features Tests
 * 
 * BVJ: Enterprise segment - Core platform capability validation
 * Business Goal: Validate core enterprise features for sales demos
 * Value Impact: Ensures enterprise prospects see working platform capabilities
 * Revenue Impact: Supports enterprise conversion pipeline
 */

describe('Enterprise Demo - Core Features', () => {
  beforeEach(() => {
    EnterpriseDemoUtils.setupDemoPage()
  })

  describe('Page Load and Authentication', () => {
    it('should load the enterprise demo page', () => {
      EnterpriseDemoUtils.verifyPageLoad()
    })

    it('should display executive-level messaging', () => {
      EnterpriseDemoUtils.verifyExecutiveMessaging()
    })

    it('should show authentication gate for protected features', () => {
      cy.contains('Schedule Executive Briefing').click()
      cy.contains('Authentication Required').should('be.visible')
    })

    it('should display enterprise security badges', () => {
      EnterpriseDemoUtils.verifySecurityBadges()
    })
  })

  describe('Live Performance Metrics Dashboard', () => {
    it('should display real-time metrics', () => {
      cy.contains('Live Performance').should('be.visible')
      EnterpriseDemoUtils.verifyMetricCards()
    })

    it('should show cost savings metrics', () => {
      cy.contains('Cost Reduction').should('be.visible')
      cy.contains('$').should('be.visible')
      cy.contains('%').should('be.visible')
    })

    it('should display latency improvements', () => {
      cy.contains('Latency').should('be.visible')
      cy.contains('ms').should('be.visible')
      cy.contains('reduction').should('be.visible')
    })

    it('should show throughput metrics', () => {
      cy.contains('Throughput').should('be.visible')
      cy.contains('requests/sec').should('be.visible')
    })

    it('should auto-refresh metrics', () => {
      cy.get('[data-testid="metric-value"]').then($initial => {
        const initialValue = $initial.text()
        cy.wait(5000)
        cy.get('[data-testid="metric-value"]').should($updated => {
          expect($updated.text()).to.not.equal(initialValue)
        })
      })
    })

    it('should display metric trends with charts', () => {
      cy.get('[data-testid="trend-chart"]').should('be.visible')
      cy.get('svg').should('exist')
    })
  })

  describe('Feature Showcase', () => {
    it('should display enterprise features grid', () => {
      cy.contains('Enterprise Features').should('be.visible')
      EnterpriseDemoUtils.verifyFeatureTiles()
    })

    it('should highlight multi-agent orchestration', () => {
      cy.contains('Multi-Agent Orchestration').should('be.visible')
      cy.contains('Coordinate multiple AI agents').should('be.visible')
    })

    it('should showcase security features', () => {
      cy.contains('Enterprise Security').should('be.visible')
      cy.contains('End-to-end encryption').should('be.visible')
      cy.contains('Role-based access').should('be.visible')
    })

    it('should display integration capabilities', () => {
      cy.contains('Seamless Integration').should('be.visible')
      cy.contains('API').should('be.visible')
      cy.contains('SDK').should('be.visible')
    })

    it('should show feature details on hover', () => {
      cy.contains('Multi-Agent Orchestration').trigger('mouseenter')
      cy.contains('Learn More').should('be.visible')
    })

    it('should open feature modal on click', () => {
      cy.contains('Enterprise Security').click()
      cy.get('[data-testid="feature-modal"]').should('be.visible')
      cy.contains('Advanced Security Features').should('be.visible')
    })
  })

  describe('Executive Dashboard Preview', () => {
    it('should display dashboard preview section', () => {
      cy.contains('Executive Dashboard').should('be.visible')
      cy.get(ENTERPRISE_SELECTORS.dashboardPreview).should('be.visible')
    })

    it('should show KPI widgets', () => {
      cy.contains('Key Performance Indicators').should('be.visible')
      cy.get('[data-testid="kpi-widget"]').should('have.length.at.least', 4)
    })

    it('should display cost analysis chart', () => {
      cy.contains('Cost Analysis').should('be.visible')
      cy.get('[data-testid="cost-chart"]').should('be.visible')
    })

    it('should show ROI projections', () => {
      cy.contains('ROI Projection').should('be.visible')
      cy.contains('3-Year').should('be.visible')
      cy.contains('5-Year').should('be.visible')
    })

    it('should have interactive dashboard elements', () => {
      EnterpriseDemoUtils.verifyDashboardInteractivity()
    })
  })

  describe('Core Feature Integration', () => {
    it('should validate feature flow from metrics to dashboard', () => {
      EnterpriseDemoUtils.verifyMetricCards()
      cy.get(ENTERPRISE_SELECTORS.dashboardPreview).scrollIntoView()
      EnterpriseDemoUtils.verifyDashboardInteractivity()
    })

    it('should support enterprise authentication workflow', () => {
      cy.contains('Enterprise Security').click()
      cy.get('[data-testid="feature-modal"]').should('be.visible')
      cy.contains('Schedule Demo').should('be.visible')
    })

    it('should demonstrate real-time data flow', () => {
      cy.contains('Live Performance').should('be.visible')
      cy.get('[data-testid="trend-chart"]').should('be.visible')
      cy.contains('Executive Dashboard').should('be.visible')
    })

    it('should validate enterprise security messaging consistency', () => {
      EnterpriseDemoUtils.verifySecurityBadges()
      cy.contains('Enterprise Security').should('be.visible')
      cy.contains('End-to-end encryption').should('be.visible')
    })

    it('should ensure smooth feature navigation', () => {
      cy.contains('Enterprise Features').scrollIntoView()
      EnterpriseDemoUtils.verifyFeatureTiles()
      cy.contains('Executive Dashboard').scrollIntoView()
      cy.get(ENTERPRISE_SELECTORS.dashboardPreview).should('be.visible')
    })
  })
})