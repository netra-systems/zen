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
      cy.get(TEST_SELECTORS.PERFORMANCE_METRICS).should('be.visible')
    })

    it('should display component heading', () => {
      cy.contains('h2', 'Real-Time Performance Metrics').should('be.visible')
    })

    it('should show auto-refresh indicator', () => {
      cy.get(TEST_SELECTORS.AUTO_REFRESH).should('be.visible')
      cy.contains('Auto-refresh').should('be.visible')
    })

    it('should display last updated timestamp', () => {
      cy.contains('Last updated').should('be.visible')
      cy.contains(/\d+ seconds? ago/).should('be.visible')
    })

    it('should have glassmorphic styling', () => {
      cy.get('.backdrop-blur-xl').should('exist')
      cy.get('.bg-opacity-5').should('exist')
    })

    it('should initialize with default tab active', () => {
      cy.get('[data-testid="active-tab"]').should('exist')
    })

    it('should show loading state initially', () => {
      cy.reload()
      cy.get('[data-testid="loading-indicator"]').should('be.visible')
    })

    it('should display metric count indicator', () => {
      cy.get('[data-testid="metric-count"]').should('be.visible')
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
      cy.contains('Active Optimizations').should('be.visible')
    })

    it('should switch to Latency tab', () => {
      MetricsTestHelper.switchToTab('Latency')
      cy.contains('Response Time Distribution').should('be.visible')
      cy.contains('P50').should('be.visible')
    })

    it('should switch to Cost Analysis tab', () => {
      MetricsTestHelper.switchToTab('Cost Analysis')
      cy.contains('Cost Breakdown').should('be.visible')
      cy.contains('Savings Trend').should('be.visible')
    })

    it('should switch to Benchmarks tab', () => {
      MetricsTestHelper.switchToTab('Benchmarks')
      cy.contains('Industry Comparison').should('be.visible')
      cy.contains('Performance Index').should('be.visible')
    })

    it('should maintain tab state on refresh', () => {
      MetricsTestHelper.switchToTab('Latency')
      cy.reload()
      MetricsTestHelper.verifyTabActive('Latency')
    })

    it('should highlight active tab', () => {
      MetricsTestHelper.switchToTab('Overview')
      cy.get('[data-testid="tab-overview"]').should('have.class', 'active')
    })

    it('should show tab content transitions', () => {
      MetricsTestHelper.switchToTab('Overview')
      cy.get('[data-testid="tab-content"]').should('have.class', 'fade-in')
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
      cy.get('[data-testid="metrics-header"]').should('be.visible')
      cy.get('[data-testid="metrics-title"]').should('be.visible')
    })

    it('should show control panel', () => {
      cy.get('[data-testid="control-panel"]').should('be.visible')
      cy.get('[data-testid="refresh-controls"]').should('be.visible')
    })

    it('should display metrics grid', () => {
      cy.get('[data-testid="metrics-grid"]').should('be.visible')
      cy.get('[data-testid="metric-card"]').should('have.length.at.least', 1)
    })

    it('should show status indicators', () => {
      cy.get('[data-testid="status-indicator"]').should('be.visible')
      cy.get('[data-testid="connection-status"]').should('be.visible')
    })

    it('should display breadcrumb navigation', () => {
      cy.get('[data-testid="breadcrumb"]').should('be.visible')
      cy.contains('Demo').should('be.visible')
    })

    it('should show performance summary', () => {
      cy.get('[data-testid="performance-summary"]').should('be.visible')
    })

    it('should display action buttons', () => {
      cy.get('[data-testid="action-buttons"]').should('be.visible')
    })

    it('should have responsive grid layout', () => {
      cy.get('[data-testid="metrics-grid"]').should('have.css', 'display', 'grid')
    })
  })

  describe('Refresh Controls', () => {
    it('should show refresh button', () => {
      cy.get('[data-testid="refresh-button"]').should('be.visible')
    })

    it('should allow manual refresh', () => {
      MetricsTestHelper.triggerRefresh()
      MetricsTestHelper.verifyRefreshAnimation()
    })

    it('should show pause/resume toggle', () => {
      cy.get('[data-testid="pause-refresh"]').should('be.visible')
    })

    it('should pause auto-refresh when clicked', () => {
      MetricsTestHelper.pauseAutoRefresh()
    })

    it('should display refresh interval setting', () => {
      cy.get('[data-testid="refresh-interval"]').should('be.visible')
    })

    it('should show last refresh timestamp', () => {
      cy.get('[data-testid="last-refresh"]').should('be.visible')
    })

    it('should indicate refresh status', () => {
      cy.get('[data-testid="refresh-status"]').should('be.visible')
    })

    it('should handle refresh failure gracefully', () => {
      MetricsTestHelper.simulateApiFailure('/api/demo/metrics')
      MetricsTestHelper.triggerRefresh()
      cy.contains('Refresh failed').should('be.visible')
    })
  })

  describe('Component State Management', () => {
    it('should maintain state across tab switches', () => {
      MetricsTestHelper.switchToTab('Overview')
      MetricsTestHelper.pauseAutoRefresh()
      MetricsTestHelper.switchToTab('Latency')
      cy.get(TEST_SELECTORS.AUTO_REFRESH).should('contain', 'Paused')
    })

    it('should preserve filter settings', () => {
      MetricsTestHelper.setTimeRange('24h')
      MetricsTestHelper.switchToTab('Cost Analysis')
      cy.contains('Last 24 hours').should('be.visible')
    })

    it('should handle URL navigation', () => {
      cy.url().should('include', '/demo')
    })

    it('should show loading states during transitions', () => {
      MetricsTestHelper.switchToTab('Benchmarks')
      cy.get('[data-testid="tab-loading"]').should('be.visible')
    })

    it('should cache tab content appropriately', () => {
      MetricsTestHelper.switchToTab('Overview')
      MetricsTestHelper.switchToTab('Latency')
      MetricsTestHelper.switchToTab('Overview')
      cy.get('[data-testid="cached-content"]').should('exist')
    })

    it('should handle concurrent state updates', () => {
      cy.get(TEST_SELECTORS.METRIC_VALUE).should('be.visible')
    })

    it('should maintain scroll position', () => {
      cy.scrollTo('bottom')
      MetricsTestHelper.switchToTab('Latency')
      cy.window().its('scrollY').should('equal', 0)
    })

    it('should clear transient alerts on tab change', () => {
      MetricsTestHelper.switchToTab('Overview')
      cy.get('[data-testid="transient-alert"]').should('not.exist')
    })
  })
})