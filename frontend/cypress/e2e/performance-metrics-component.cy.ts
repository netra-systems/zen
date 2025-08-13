/// <reference types="cypress" />

describe('PerformanceMetrics Component E2E Tests', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/demo')
    cy.contains('Technology').click()
    cy.contains('Performance').click()
    cy.wait(500)
  })

  describe('Component Initialization', () => {
    it('should render PerformanceMetrics component', () => {
      cy.get('[data-testid="performance-metrics"]').should('be.visible')
    })

    it('should display component heading', () => {
      cy.contains('h2', 'Real-Time Performance Metrics').should('be.visible')
    })

    it('should show auto-refresh indicator', () => {
      cy.get('[data-testid="auto-refresh"]').should('be.visible')
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
  })

  describe('Tab Navigation', () => {
    it('should display all metric tabs', () => {
      const tabs = ['Overview', 'Latency', 'Cost Analysis', 'Benchmarks']
      tabs.forEach(tab => {
        cy.contains(tab).should('be.visible')
      })
    })

    it('should switch to Overview tab', () => {
      cy.contains('Overview').click()
      cy.contains('System Health').should('be.visible')
      cy.contains('Active Optimizations').should('be.visible')
    })

    it('should switch to Latency tab', () => {
      cy.contains('Latency').click()
      cy.contains('Response Time Distribution').should('be.visible')
      cy.contains('P50').should('be.visible')
      cy.contains('P95').should('be.visible')
      cy.contains('P99').should('be.visible')
    })

    it('should switch to Cost Analysis tab', () => {
      cy.contains('Cost Analysis').click()
      cy.contains('Cost Breakdown').should('be.visible')
      cy.contains('Savings Trend').should('be.visible')
    })

    it('should switch to Benchmarks tab', () => {
      cy.contains('Benchmarks').click()
      cy.contains('Industry Comparison').should('be.visible')
      cy.contains('Performance Index').should('be.visible')
    })

    it('should maintain tab state on refresh', () => {
      cy.contains('Latency').click()
      cy.reload()
      cy.get('[data-testid="active-tab"]').should('contain', 'Latency')
    })
  })

  describe('Overview Tab Metrics', () => {
    beforeEach(() => {
      cy.contains('Overview').click()
    })

    it('should display system health score', () => {
      cy.contains('System Health').should('be.visible')
      cy.get('[data-testid="health-score"]').should('contain', '%')
    })

    it('should show health status indicator', () => {
      cy.get('[data-testid="health-indicator"]').should('be.visible')
      cy.get('[data-testid="health-indicator"]').should('have.class', 'bg-green-500')
    })

    it('should display active optimizations count', () => {
      cy.contains('Active Optimizations').should('be.visible')
      cy.get('[data-testid="optimization-count"]').should('contain', /\d+/)
    })

    it('should show uptime percentage', () => {
      cy.contains('Uptime').should('be.visible')
      cy.contains('99.9%').should('be.visible')
    })

    it('should display request throughput', () => {
      cy.contains('Throughput').should('be.visible')
      cy.contains('req/s').should('be.visible')
    })

    it('should show error rate', () => {
      cy.contains('Error Rate').should('be.visible')
      cy.contains(/\d+\.?\d*%/).should('be.visible')
    })

    it('should display resource utilization', () => {
      cy.contains('CPU Usage').should('be.visible')
      cy.contains('Memory Usage').should('be.visible')
      cy.get('[data-testid="cpu-gauge"]').should('be.visible')
      cy.get('[data-testid="memory-gauge"]').should('be.visible')
    })
  })

  describe('Latency Tab Metrics', () => {
    beforeEach(() => {
      cy.contains('Latency').click()
    })

    it('should display latency distribution chart', () => {
      cy.get('[data-testid="latency-chart"]').should('be.visible')
      cy.get('svg').should('exist')
    })

    it('should show percentile values', () => {
      cy.contains('P50').parent().contains(/\d+ms/).should('be.visible')
      cy.contains('P75').parent().contains(/\d+ms/).should('be.visible')
      cy.contains('P95').parent().contains(/\d+ms/).should('be.visible')
      cy.contains('P99').parent().contains(/\d+ms/).should('be.visible')
    })

    it('should display average latency', () => {
      cy.contains('Average').should('be.visible')
      cy.get('[data-testid="avg-latency"]').should('contain', 'ms')
    })

    it('should show latency trend', () => {
      cy.contains('Trend').should('be.visible')
      cy.get('[data-testid="latency-trend"]').should('be.visible')
      cy.contains(/↑|↓|→/).should('be.visible')
    })

    it('should display service-level latencies', () => {
      cy.contains('Service Breakdown').should('be.visible')
      cy.get('[data-testid="service-latency"]').should('have.length.at.least', 3)
    })

    it('should show latency heatmap', () => {
      cy.get('[data-testid="latency-heatmap"]').should('be.visible')
      cy.get('[data-testid="heatmap-cell"]').should('have.length.at.least', 24)
    })

    it('should display optimization suggestions', () => {
      cy.contains('Optimization Opportunities').should('be.visible')
      cy.get('[data-testid="latency-suggestion"]').should('have.length.at.least', 2)
    })
  })

  describe('Cost Analysis Tab', () => {
    beforeEach(() => {
      cy.contains('Cost Analysis').click()
    })

    it('should display total monthly cost', () => {
      cy.contains('Total Monthly Cost').should('be.visible')
      cy.contains(/\$[\d,]+/).should('be.visible')
    })

    it('should show cost breakdown pie chart', () => {
      cy.get('[data-testid="cost-pie-chart"]').should('be.visible')
      cy.get('svg').should('exist')
    })

    it('should display cost categories', () => {
      const categories = ['Compute', 'Storage', 'Network', 'API Calls']
      categories.forEach(category => {
        cy.contains(category).should('be.visible')
      })
    })

    it('should show cost trend graph', () => {
      cy.get('[data-testid="cost-trend-graph"]').should('be.visible')
      cy.contains('Last 30 Days').should('be.visible')
    })

    it('should display savings achieved', () => {
      cy.contains('Savings This Month').should('be.visible')
      cy.contains(/\$[\d,]+/).should('be.visible')
      cy.contains(/\d+%/).should('be.visible')
    })

    it('should show cost per request', () => {
      cy.contains('Cost per 1K Requests').should('be.visible')
      cy.contains(/\$\d+\.\d+/).should('be.visible')
    })

    it('should display projected costs', () => {
      cy.contains('Projected Next Month').should('be.visible')
      cy.contains(/\$[\d,]+/).should('be.visible')
    })

    it('should show cost optimization recommendations', () => {
      cy.contains('Cost Optimization').should('be.visible')
      cy.get('[data-testid="cost-recommendation"]').should('have.length.at.least', 3)
    })
  })

  describe('Benchmarks Tab', () => {
    beforeEach(() => {
      cy.contains('Benchmarks').click()
    })

    it('should display performance index', () => {
      cy.contains('Performance Index').should('be.visible')
      cy.get('[data-testid="performance-index"]').should('contain', /\d+/)
    })

    it('should show industry comparison', () => {
      cy.contains('Industry Average').should('be.visible')
      cy.contains('Your Performance').should('be.visible')
    })

    it('should display comparison chart', () => {
      cy.get('[data-testid="benchmark-chart"]').should('be.visible')
      cy.get('[data-testid="benchmark-bar"]').should('have.length.at.least', 5)
    })

    it('should show percentile ranking', () => {
      cy.contains('Percentile Ranking').should('be.visible')
      cy.contains('Top').should('be.visible')
      cy.contains('%').should('be.visible')
    })

    it('should display metric comparisons', () => {
      const metrics = ['Latency', 'Throughput', 'Cost Efficiency', 'Reliability']
      metrics.forEach(metric => {
        cy.contains(metric).should('be.visible')
      })
    })

    it('should show improvement areas', () => {
      cy.contains('Areas for Improvement').should('be.visible')
      cy.get('[data-testid="improvement-area"]').should('have.length.at.least', 2)
    })

    it('should display competitor analysis', () => {
      cy.contains('vs Competition').should('be.visible')
      cy.get('[data-testid="competitor-metric"]').should('have.length.at.least', 3)
    })
  })

  describe('Real-time Updates', () => {
    it('should auto-refresh metrics', () => {
      cy.get('[data-testid="metric-value"]').then($initial => {
        const initialValue = $initial.text()
        cy.wait(5000)
        cy.get('[data-testid="metric-value"]').should($updated => {
          expect($updated.text()).to.not.equal(initialValue)
        })
      })
    })

    it('should update timestamp', () => {
      cy.contains('Last updated').parent().then($initial => {
        const initialTime = $initial.text()
        cy.wait(5000)
        cy.contains('Last updated').parent().should($updated => {
          expect($updated.text()).to.not.equal(initialTime)
        })
      })
    })

    it('should show refresh animation', () => {
      cy.wait(4500)
      cy.get('[data-testid="refresh-indicator"]').should('have.class', 'animate-spin')
    })

    it('should allow manual refresh', () => {
      cy.get('[data-testid="refresh-button"]').click()
      cy.get('[data-testid="refresh-indicator"]').should('have.class', 'animate-spin')
    })

    it('should pause auto-refresh', () => {
      cy.get('[data-testid="pause-refresh"]').click()
      cy.get('[data-testid="auto-refresh"]').should('contain', 'Paused')
    })
  })

  describe('Data Visualization', () => {
    it('should display line charts', () => {
      cy.get('[data-testid="line-chart"]').should('have.length.at.least', 1)
      cy.get('path[stroke]').should('exist')
    })

    it('should show bar charts', () => {
      cy.get('[data-testid="bar-chart"]').should('have.length.at.least', 1)
      cy.get('rect').should('exist')
    })

    it('should display gauge charts', () => {
      cy.get('[data-testid="gauge-chart"]').should('have.length.at.least', 2)
      cy.get('circle').should('exist')
    })

    it('should show sparklines', () => {
      cy.get('[data-testid="sparkline"]').should('have.length.at.least', 3)
    })

    it('should have interactive tooltips', () => {
      cy.get('[data-testid="chart-point"]').first().trigger('mouseenter')
      cy.get('[data-testid="tooltip"]').should('be.visible')
    })

    it('should allow zooming on charts', () => {
      cy.get('[data-testid="zoomable-chart"]').first().trigger('wheel', { deltaY: -100 })
      cy.get('[data-testid="zoom-level"]').should('contain', '110%')
    })
  })

  describe('Filtering and Time Range', () => {
    it('should display time range selector', () => {
      cy.get('[data-testid="time-range"]').should('be.visible')
    })

    it('should allow selecting different time ranges', () => {
      const ranges = ['1h', '6h', '24h', '7d', '30d']
      ranges.forEach(range => {
        cy.contains(range).should('be.visible')
      })
    })

    it('should update metrics based on time range', () => {
      cy.contains('24h').click()
      cy.wait(1000)
      cy.contains('Last 24 hours').should('be.visible')
    })

    it('should show service filter', () => {
      cy.get('[data-testid="service-filter"]').should('be.visible')
    })

    it('should filter metrics by service', () => {
      cy.get('[data-testid="service-filter"]').select('API Gateway')
      cy.wait(1000)
      cy.contains('API Gateway').should('be.visible')
    })

    it('should allow multi-select filtering', () => {
      cy.get('[data-testid="multi-filter"]').click()
      cy.get('input[value="service1"]').check()
      cy.get('input[value="service2"]').check()
      cy.contains('Apply').click()
    })
  })

  describe('Alerts and Thresholds', () => {
    it('should display alert indicators', () => {
      cy.get('[data-testid="alert-indicator"]').should('be.visible')
    })

    it('should show threshold violations', () => {
      cy.contains('Threshold Alerts').should('be.visible')
      cy.get('[data-testid="threshold-violation"]').should('have.class', 'text-red-500')
    })

    it('should display alert history', () => {
      cy.contains('Alert History').click()
      cy.get('[data-testid="alert-item"]').should('have.length.at.least', 0)
    })

    it('should allow setting custom thresholds', () => {
      cy.contains('Configure Thresholds').click()
      cy.get('input[name="latency-threshold"]').clear().type('500')
      cy.contains('Save').click()
      cy.contains('Threshold updated').should('be.visible')
    })

    it('should show alert notifications', () => {
      cy.get('[data-testid="notification-bell"]').should('be.visible')
      cy.get('[data-testid="notification-count"]').should('contain', /\d+/)
    })
  })

  describe('Export and Reporting', () => {
    it('should display export options', () => {
      cy.get('[data-testid="export-menu"]').click()
      cy.contains('Export as PDF').should('be.visible')
      cy.contains('Export as CSV').should('be.visible')
    })

    it('should export metrics as PDF', () => {
      cy.get('[data-testid="export-menu"]').click()
      cy.contains('Export as PDF').click()
      cy.readFile('cypress/downloads/performance-metrics.pdf').should('exist')
    })

    it('should export data as CSV', () => {
      cy.get('[data-testid="export-menu"]').click()
      cy.contains('Export as CSV').click()
      cy.readFile('cypress/downloads/metrics-data.csv').should('exist')
    })

    it('should allow scheduling reports', () => {
      cy.contains('Schedule Report').click()
      cy.get('[data-testid="schedule-modal"]').should('be.visible')
      cy.get('select[name="frequency"]').should('be.visible')
    })

    it('should generate snapshot', () => {
      cy.contains('Snapshot').click()
      cy.contains('Snapshot created').should('be.visible')
    })
  })

  describe('Drill-down Features', () => {
    it('should allow drilling into metrics', () => {
      cy.get('[data-testid="metric-card"]').first().click()
      cy.get('[data-testid="metric-details"]').should('be.visible')
    })

    it('should show detailed breakdown', () => {
      cy.get('[data-testid="metric-card"]').first().click()
      cy.contains('Detailed Breakdown').should('be.visible')
      cy.get('[data-testid="breakdown-item"]').should('have.length.at.least', 3)
    })

    it('should display historical data', () => {
      cy.get('[data-testid="metric-card"]').first().click()
      cy.contains('Historical Data').should('be.visible')
      cy.get('[data-testid="history-chart"]').should('be.visible')
    })

    it('should show related metrics', () => {
      cy.get('[data-testid="metric-card"]').first().click()
      cy.contains('Related Metrics').should('be.visible')
      cy.get('[data-testid="related-metric"]').should('have.length.at.least', 2)
    })
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt to mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="performance-metrics"]').should('be.visible')
      cy.contains('Performance Metrics').should('be.visible')
    })

    it('should show mobile-optimized tabs', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="mobile-tabs"]').should('be.visible')
      cy.get('[data-testid="tab-dropdown"]').should('be.visible')
    })

    it('should stack metric cards on mobile', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="metric-card"]').should('have.css', 'width', '100%')
    })

    it('should handle mobile interactions', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="tab-dropdown"]').select('Latency')
      cy.contains('Response Time').should('be.visible')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      cy.get('[aria-label]').should('have.length.at.least', 10)
    })

    it('should support keyboard navigation', () => {
      cy.get('body').tab()
      cy.focused().should('have.attr', 'role', 'tab')
    })

    it('should announce metric updates', () => {
      cy.get('[role="status"]').should('exist')
      cy.wait(5000)
      cy.get('[role="status"]').should('contain', 'Updated')
    })

    it('should have sufficient color contrast', () => {
      cy.get('[data-testid="metric-value"]').should('have.css', 'color')
        .and('not.equal', 'rgb(200, 200, 200)')
    })
  })

  describe('Error Handling', () => {
    it('should handle API failures gracefully', () => {
      cy.intercept('GET', '/api/demo/metrics', { statusCode: 500 })
      cy.reload()
      cy.contains('Unable to load metrics').should('be.visible')
      cy.contains('Retry').should('be.visible')
    })

    it('should show cached data on error', () => {
      cy.intercept('GET', '/api/demo/metrics', { statusCode: 500 })
      cy.wait(5000)
      cy.contains('Showing cached data').should('be.visible')
    })

    it('should handle partial data loading', () => {
      cy.intercept('GET', '/api/demo/metrics/latency', { statusCode: 500 })
      cy.contains('Latency').click()
      cy.contains('Partial data available').should('be.visible')
    })
  })
})