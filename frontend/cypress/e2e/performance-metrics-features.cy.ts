/// <reference types="cypress" />
import { 
  MetricsTestHelper, 
  TEST_SELECTORS, 
  TIME_RANGES,
  EXPORT_FORMATS,
  CHART_TYPES,
  PERFORMANCE_THRESHOLDS
} from '../support/metrics-test-utils'

/**
 * Performance Metrics Advanced Features Tests  
 * BVJ: Enterprise segment - validates platform performance, supports SLA compliance
 * Tests: Real-time updates, visualization, filtering, drill-down, export
 */

describe('Performance Metrics Advanced Features', () => {
  beforeEach(() => {
    MetricsTestHelper.setupViewport()
    MetricsTestHelper.navigateToMetrics()
    MetricsTestHelper.waitForPerformanceTab()
  })

  describe('Real-time Updates', () => {
    it('should auto-refresh metrics data', () => {
      cy.get(TEST_SELECTORS.METRIC_VALUE).then($initial => {
        const initialValue = $initial.text()
        MetricsTestHelper.waitForDataUpdate()
        cy.get(TEST_SELECTORS.METRIC_VALUE).should($updated => {
          expect($updated.text()).to.not.equal(initialValue)
        })
      })
    })

    it('should update timestamp continuously', () => {
      cy.contains('Last updated').parent().then($initial => {
        const initialTime = $initial.text()
        MetricsTestHelper.waitForDataUpdate()
        cy.contains('Last updated').parent().should($updated => {
          expect($updated.text()).to.not.equal(initialTime)
        })
      })
    })

    it('should show refresh animation during updates', () => {
      cy.wait(4500)
      MetricsTestHelper.verifyRefreshAnimation()
    })

    it('should handle manual refresh trigger', () => {
      MetricsTestHelper.triggerRefresh()
      MetricsTestHelper.verifyRefreshAnimation()
    })

    it('should pause and resume auto-refresh', () => {
      MetricsTestHelper.pauseAutoRefresh()
      cy.get('[data-testid="resume-refresh"]').click()
      cy.get(TEST_SELECTORS.AUTO_REFRESH).should('not.contain', 'Paused')
    })

    it('should show connection status indicator', () => {
      cy.get('[data-testid="connection-status"]').should('be.visible')
      cy.get('[data-testid="connection-status"]').should('have.class', 'connected')
    })

    it('should handle websocket reconnection', () => {
      cy.window().then(win => {
        win.dispatchEvent(new Event('offline'))
      })
      cy.contains('Reconnecting').should('be.visible')
    })

    it('should queue updates during connection loss', () => {
      cy.get('[data-testid="update-queue"]').should('be.visible')
    })
  })

  describe('Data Visualization', () => {
    it('should display line charts with data points', () => {
      cy.get(CHART_TYPES.LINE).should('have.length.at.least', 1)
      cy.get('path[stroke]').should('exist')
    })

    it('should show bar charts with proper scaling', () => {
      cy.get(CHART_TYPES.BAR).should('have.length.at.least', 1)
      cy.get('rect').should('exist')
    })

    it('should display gauge charts for metrics', () => {
      cy.get(CHART_TYPES.GAUGE).should('have.length.at.least', 2)
      cy.get('circle').should('exist')
    })

    it('should show sparklines for trends', () => {
      cy.get('[data-testid="sparkline"]').should('have.length.at.least', 3)
    })

    it('should have interactive tooltips on charts', () => {
      MetricsTestHelper.verifyTooltipInteraction()
    })

    it('should support chart zoom functionality', () => {
      MetricsTestHelper.verifyZoomFunctionality()
    })

    it('should display chart legends appropriately', () => {
      cy.get('[data-testid="chart-legend"]').should('be.visible')
    })

    it('should handle chart data loading states', () => {
      cy.get('[data-testid="chart-loading"]').should('be.visible')
    })
  })

  describe('Filtering and Time Range', () => {
    it('should display time range selector', () => {
      cy.get('[data-testid="time-range"]').should('be.visible')
    })

    it('should show all available time ranges', () => {
      TIME_RANGES.forEach(range => {
        cy.contains(range).should('be.visible')
      })
    })

    it('should update metrics based on time range', () => {
      MetricsTestHelper.setTimeRange('24h')
      cy.contains('Last 24 hours').should('be.visible')
    })

    it('should show service filter dropdown', () => {
      cy.get('[data-testid="service-filter"]').should('be.visible')
    })

    it('should filter metrics by selected service', () => {
      MetricsTestHelper.filterByService('API Gateway')
      cy.contains('API Gateway').should('be.visible')
    })

    it('should support multi-select filtering', () => {
      cy.get('[data-testid="multi-filter"]').click()
      cy.get('input[value="service1"]').check()
      cy.get('input[value="service2"]').check()
      cy.contains('Apply').click()
    })

    it('should display active filter indicators', () => {
      MetricsTestHelper.setTimeRange('7d')
      cy.get('[data-testid="active-filters"]').should('contain', '7d')
    })

    it('should allow clearing all filters', () => {
      cy.get('[data-testid="clear-filters"]').click()
      cy.get('[data-testid="active-filters"]').should('not.exist')
    })
  })

  describe('Alerts and Thresholds', () => {
    it('should display alert indicators when present', () => {
      MetricsTestHelper.verifyAlertVisible()
    })

    it('should show threshold violations clearly', () => {
      cy.contains('Threshold Alerts').should('be.visible')
      cy.get('[data-testid="threshold-violation"]').should('have.class', 'text-red-500')
    })

    it('should display alert history panel', () => {
      cy.contains('Alert History').click()
      cy.get('[data-testid="alert-item"]').should('have.length.at.least', 0)
    })

    it('should allow configuring custom thresholds', () => {
      MetricsTestHelper.configureThreshold('latency', '500')
      cy.contains('Threshold updated').should('be.visible')
    })

    it('should show alert notifications with count', () => {
      cy.get('[data-testid="notification-bell"]').should('be.visible')
      cy.get('[data-testid="notification-count"]').should('contain', /\d+/)
    })

    it('should support threshold acknowledgment', () => {
      cy.get('[data-testid="acknowledge-alert"]').first().click()
      cy.contains('Alert acknowledged').should('be.visible')
    })

    it('should display escalation rules', () => {
      cy.contains('Escalation Rules').click()
      cy.get('[data-testid="escalation-rule"]').should('be.visible')
    })

    it('should show alert severity levels', () => {
      cy.get('[data-testid="alert-severity"]').should('be.visible')
    })
  })

  describe('Export and Reporting', () => {
    it('should display export menu options', () => {
      cy.get('[data-testid="export-menu"]').click()
      EXPORT_FORMATS.forEach(format => {
        cy.contains(`Export as ${format}`).should('be.visible')
      })
    })

    it('should export metrics as PDF', () => {
      MetricsTestHelper.exportMetrics('PDF')
      MetricsTestHelper.verifyExportFile('performance-metrics.pdf')
    })

    it('should export data as CSV', () => {
      MetricsTestHelper.exportMetrics('CSV')
      MetricsTestHelper.verifyExportFile('metrics-data.csv')
    })

    it('should allow scheduling automated reports', () => {
      MetricsTestHelper.scheduleReport()
      cy.get('select[name="frequency"]').should('be.visible')
    })

    it('should generate performance snapshots', () => {
      MetricsTestHelper.createSnapshot()
    })

    it('should support custom report templates', () => {
      cy.contains('Custom Template').click()
      cy.get('[data-testid="template-editor"]').should('be.visible')
    })

    it('should show export progress indicator', () => {
      MetricsTestHelper.exportMetrics('PDF')
      cy.get('[data-testid="export-progress"]').should('be.visible')
    })

    it('should handle export failures gracefully', () => {
      MetricsTestHelper.simulateApiFailure('/api/export')
      MetricsTestHelper.exportMetrics('PDF')
      cy.contains('Export failed').should('be.visible')
    })
  })

  describe('Drill-down Features', () => {
    it('should allow drilling into metric details', () => {
      MetricsTestHelper.drillIntoMetric()
    })

    it('should show detailed metric breakdown', () => {
      MetricsTestHelper.drillIntoMetric()
      cy.contains('Detailed Breakdown').should('be.visible')
      cy.get('[data-testid="breakdown-item"]').should('have.length.at.least', 3)
    })

    it('should display historical data in drill-down', () => {
      MetricsTestHelper.drillIntoMetric()
      cy.contains('Historical Data').should('be.visible')
      MetricsTestHelper.verifyChartVisible('[data-testid="history-chart"]')
    })

    it('should show related metrics panel', () => {
      MetricsTestHelper.drillIntoMetric()
      cy.contains('Related Metrics').should('be.visible')
      cy.get('[data-testid="related-metric"]').should('have.length.at.least', 2)
    })

    it('should support metric correlation analysis', () => {
      MetricsTestHelper.drillIntoMetric()
      cy.contains('Correlation Analysis').should('be.visible')
    })

    it('should allow metric comparison mode', () => {
      cy.get('[data-testid="compare-mode"]').click()
      cy.get('[data-testid="comparison-panel"]').should('be.visible')
    })

    it('should show drill-down breadcrumbs', () => {
      MetricsTestHelper.drillIntoMetric()
      cy.get('[data-testid="drill-breadcrumb"]').should('be.visible')
    })

    it('should support closing drill-down panels', () => {
      MetricsTestHelper.drillIntoMetric()
      cy.get('[data-testid="close-drill-down"]').click()
      cy.get('[data-testid="metric-details"]').should('not.exist')
    })
  })

})