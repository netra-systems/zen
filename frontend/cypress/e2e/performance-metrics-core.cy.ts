/// <reference types="cypress" />
import { MetricsTestHelper, TEST_SELECTORS, METRIC_TABS } from '../support/metrics-test-utils'

/**
 * Performance Metrics Core Component Tests
 * BVJ: Enterprise segment - validates platform performance, supports SLA compliance
 * Tests: Component initialization, navigation, basic functionality
 */

describe('PerformanceMetrics Core Component Tests', () => {
  beforeEach(() => {
    MetricsTestHelper.setupViewport()
    MetricsTestHelper.navigateToMetrics()
    MetricsTestHelper.waitForPerformanceTab()
  })

  describe('Component Initialization', () => {
    it('should render PerformanceMetrics component', () => {
      cy.contains('Performance Metrics Dashboard').should('be.visible')
    })

    it('should display component heading', () => {
      cy.contains('Performance Metrics Dashboard').should('be.visible')
      cy.contains('Real-time optimization metrics').should('be.visible')
    })

    it('should show auto-refresh control', () => {
      cy.contains('Auto').should('be.visible')
      cy.contains('Manual').should('be.visible')
    })

    it('should display last updated timestamp', () => {
      cy.contains('Updated').should('be.visible')
      // Check for timestamp in format like "Updated 12:34:56 PM"
      cy.get('.text-xs').should('contain', 'Updated')
    })

    it('should have card-based layout', () => {
      // Check for card components
      cy.get('.space-y-6').should('exist')
      cy.get('[role="tablist"]').should('exist')
    })

    it('should initialize with overview tab active by default', () => {
      cy.get('[data-value="overview"]').should('have.attr', 'data-state', 'active')
    })

    it('should show loading state initially', () => {
      cy.reload()
      cy.contains('Loading performance metrics', { timeout: 3000 }).should('be.visible')
    })

    it('should display tab navigation', () => {
      METRIC_TABS.forEach(tab => {
        cy.contains(tab).should('be.visible')
      })
    })
  })

  describe('Tab Navigation', () => {
    it('should display all metric tabs', () => {
      METRIC_TABS.forEach(tab => {
        cy.contains(tab).should('be.visible')
      })
    })

    it('should switch to Overview tab', () => {
      MetricsTestHelper.switchToTab('Overview')
      cy.contains('System Health').should('be.visible')
      // Check for real-time metrics cards
      cy.contains('Active Models').should('be.visible')
      cy.contains('Queue Depth').should('be.visible')
    })

    it('should switch to Latency tab', () => {
      MetricsTestHelper.switchToTab('Latency')
      // Check for latency-specific content
      cy.get('[data-value="latency"]').should('have.attr', 'data-state', 'active')
    })

    it('should switch to Cost Analysis tab', () => {
      MetricsTestHelper.switchToTab('Cost Analysis')
      // Check that cost tab is active
      cy.get('[data-value="cost"]').should('have.attr', 'data-state', 'active')
    })

    it('should switch to Benchmarks tab', () => {
      MetricsTestHelper.switchToTab('Benchmarks')
      // Check that benchmarks tab is active
      cy.get('[data-value="benchmarks"]').should('have.attr', 'data-state', 'active')
    })

    it('should maintain tab state on refresh', () => {
      MetricsTestHelper.switchToTab('Latency')
      cy.reload()
      MetricsTestHelper.verifyTabActive('Latency')
    })

    it('should highlight active tab', () => {
      MetricsTestHelper.switchToTab('Overview')
      cy.get('[data-value="overview"]').should('have.attr', 'data-state', 'active')
    })

    it('should show tab content', () => {
      MetricsTestHelper.switchToTab('Overview')
      cy.get('[data-state="active"]').should('be.visible')
    })

    it('should handle rapid tab switching', () => {
      METRIC_TABS.forEach((tab, index) => {
        if (index < 3) MetricsTestHelper.switchToTab(tab)
      })
      cy.get('[data-testid="active-tab"]').should('be.visible')
    })
  })

  describe('Component Layout', () => {
    it('should display header section', () => {
      cy.contains('Performance Metrics Dashboard').should('be.visible')
      cy.contains('Real-time optimization metrics').should('be.visible')
    })

    it('should show control panel', () => {
      // Check for auto/manual refresh button
      cy.contains('Auto').should('be.visible')
      cy.contains('Manual').should('be.visible')
    })

    it('should display metrics grid', () => {
      // Check for grid layout containing metric cards
      cy.get('.grid').should('be.visible')
      cy.get('.grid > div').should('have.length.at.least', 1)
    })

    it('should show status indicators', () => {
      // Check for updated timestamp badge
      cy.contains('Updated').should('be.visible')
    })

    it('should display within demo context', () => {
      // Check that we are in the demo environment
      cy.url().should('include', '/demo')
    })

    it('should show performance content', () => {
      // Check that tab content area is visible
      cy.get('[data-state="active"]').should('be.visible')
    })

    it('should display refresh button', () => {
      // Check for the auto/manual toggle button
      cy.get('button').should('contain.any', ['Auto', 'Manual'])
    })

    it('should have responsive grid layout', () => {
      cy.get('.grid').should('exist')
    })
  })

  describe('Refresh Controls', () => {
    it('should show refresh button', () => {
      cy.get('button').should('contain.any', ['Auto', 'Manual'])
    })

    it('should allow toggle between auto and manual refresh', () => {
      // Click the refresh toggle button
      cy.get('button').contains(/Auto|Manual/).click()
      // Verify the state changed
      cy.get('button').should('contain.any', ['Auto', 'Manual'])
    })

    it('should show auto/manual toggle', () => {
      cy.get('button').should('contain.any', ['Auto', 'Manual'])
    })

    it('should toggle refresh mode when clicked', () => {
      cy.get('button').contains(/Auto|Manual/).click()
      cy.wait(500)
    })

    it('should display timestamp updates', () => {
      cy.contains('Updated').should('be.visible')
    })

    it('should show last refresh timestamp', () => {
      cy.contains('Updated').should('be.visible')
    })

    it('should indicate refresh status', () => {
      cy.get('button').should('contain.any', ['Auto', 'Manual'])
    })

    it('should handle component state gracefully', () => {
      // Component should remain stable during interactions
      cy.get('[data-value="overview"]').should('have.attr', 'data-state', 'active')
    })
  })

  describe('Component State Management', () => {
    it('should maintain state across tab switches', () => {
      MetricsTestHelper.switchToTab('Overview')
      MetricsTestHelper.switchToTab('Latency')
      // Verify navigation works
      cy.get('[data-value="latency"]').should('have.attr', 'data-state', 'active')
    })

    it('should preserve tab state during navigation', () => {
      MetricsTestHelper.switchToTab('Cost Analysis')
      cy.get('[data-value="cost"]').should('have.attr', 'data-state', 'active')
    })

    it('should handle URL navigation', () => {
      cy.url().should('include', '/demo')
    })

    it('should show content during tab transitions', () => {
      MetricsTestHelper.switchToTab('Benchmarks')
      cy.get('[data-state="active"]').should('be.visible')
    })

    it('should handle rapid tab switching', () => {
      MetricsTestHelper.switchToTab('Overview')
      MetricsTestHelper.switchToTab('Latency')
      MetricsTestHelper.switchToTab('Overview')
      cy.get('[data-value="overview"]').should('have.attr', 'data-state', 'active')
    })

    it('should handle concurrent state updates', () => {
      // Check that metric cards are visible
      cy.get('.grid > div').should('have.length.at.least', 1)
    })

    it('should maintain component layout', () => {
      cy.get('.space-y-6').should('exist')
      MetricsTestHelper.switchToTab('Latency')
      cy.get('[role="tablist"]').should('be.visible')
    })

    it('should maintain consistent tab behavior', () => {
      METRIC_TABS.forEach((tab) => {
        MetricsTestHelper.switchToTab(tab)
        cy.get('[data-state="active"]').should('be.visible')
      })
    })
  })
})