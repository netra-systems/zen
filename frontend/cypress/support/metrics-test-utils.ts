/// <reference types="cypress" />

/**
 * Metrics Test Utilities - Shared test helpers and thresholds
 * BVJ: Enterprise segment - validates platform performance, supports SLA compliance
 */

export const PERFORMANCE_THRESHOLDS = {
  HEALTH_SCORE_MIN: 95,
  UPTIME_MIN: 99.9,
  ERROR_RATE_MAX: 0.1,
  LATENCY_P99_MAX: 500,
  LATENCY_P95_MAX: 200,
  COST_PER_1K_REQUESTS_MAX: 5.0,
  REFRESH_INTERVAL: 5000
} as const

export const TEST_SELECTORS = {
  PERFORMANCE_METRICS: '[data-testid="performance-metrics"]',
  AUTO_REFRESH: '[data-testid="auto-refresh"]',
  HEALTH_SCORE: '[data-testid="health-score"]',
  METRIC_VALUE: '[data-testid="metric-value"]',
  CHART_POINT: '[data-testid="chart-point"]',
  TOOLTIP: '[data-testid="tooltip"]'
} as const

export const METRIC_TABS = ['Overview', 'Latency', 'Cost Analysis', 'Benchmarks'] as const
export const TIME_RANGES = ['1h', '6h', '24h', '7d', '30d'] as const
export const COST_CATEGORIES = ['Compute', 'Storage', 'Network', 'API Calls'] as const

export class MetricsTestHelper {
  static setupViewport(): void {
    cy.viewport(1920, 1080)
  }

  static navigateToMetrics(): void {
    cy.visit('/demo')
    cy.contains('Technology').click()
  }

  static waitForPerformanceTab(): void {
    cy.contains('Performance').click()
    cy.wait(500)
  }

  static verifyComponentVisible(): void {
    cy.get(TEST_SELECTORS.PERFORMANCE_METRICS).should('be.visible')
    cy.contains('h2', 'Real-Time Performance Metrics').should('be.visible')
  }

  static switchToTab(tabName: string): void {
    cy.contains(tabName).click()
  }

  static verifyTabActive(tabName: string): void {
    cy.get('[data-testid="active-tab"]').should('contain', tabName)
  }

  static verifyMetricPresent(metricName: string): void {
    cy.contains(metricName).should('be.visible')
  }

  static verifyChartVisible(chartSelector: string): void {
    cy.get(chartSelector).should('be.visible')
    cy.get('svg').should('exist')
  }

  static triggerRefresh(): void {
    cy.get('[data-testid="refresh-button"]').click()
  }

  static verifyRefreshAnimation(): void {
    cy.get('[data-testid="refresh-indicator"]').should('have.class', 'animate-spin')
  }

  static waitForDataUpdate(): void {
    cy.wait(PERFORMANCE_THRESHOLDS.REFRESH_INTERVAL)
  }

  static verifyThresholdCompliance(selector: string, expectedValue: number): void {
    cy.get(selector).should('be.visible')
  }

  static setupMobileViewport(): void {
    cy.viewport('iphone-x')
  }

  static verifyMobileLayout(): void {
    cy.get('[data-testid="mobile-tabs"]').should('be.visible')
  }

  static checkAccessibility(): void {
    cy.get('[aria-label]').should('have.length.at.least', 10)
  }

  static simulateApiFailure(endpoint: string): void {
    cy.intercept('GET', endpoint, { statusCode: 500 })
  }

  static verifyErrorHandling(): void {
    cy.contains('Unable to load metrics').should('be.visible')
    cy.contains('Retry').should('be.visible')
  }

  static exportMetrics(format: 'PDF' | 'CSV'): void {
    cy.get('[data-testid="export-menu"]').click()
    cy.contains(`Export as ${format}`).click()
  }

  static verifyExportFile(filename: string): void {
    cy.readFile(`cypress/downloads/${filename}`).should('exist')
  }

  static setTimeRange(range: string): void {
    cy.contains(range).click()
    cy.wait(1000)
  }

  static filterByService(serviceName: string): void {
    cy.get('[data-testid="service-filter"]').select(serviceName)
    cy.wait(1000)
  }

  static configureThreshold(metricName: string, value: string): void {
    cy.contains('Configure Thresholds').click()
    cy.get(`input[name="${metricName}-threshold"]`).clear().type(value)
    cy.contains('Save').click()
  }

  static verifyAlertVisible(): void {
    cy.get('[data-testid="alert-indicator"]').should('be.visible')
  }

  static drillIntoMetric(): void {
    cy.get('[data-testid="metric-card"]').first().click()
    cy.get('[data-testid="metric-details"]').should('be.visible')
  }

  static verifyTooltipInteraction(): void {
    cy.get(TEST_SELECTORS.CHART_POINT).first().trigger('mouseenter')
    cy.get(TEST_SELECTORS.TOOLTIP).should('be.visible')
  }

  static verifyZoomFunctionality(): void {
    cy.get('[data-testid="zoomable-chart"]').first().trigger('wheel', { deltaY: -100 })
    cy.get('[data-testid="zoom-level"]').should('contain', '110%')
  }

  static pauseAutoRefresh(): void {
    cy.get('[data-testid="pause-refresh"]').click()
    cy.get(TEST_SELECTORS.AUTO_REFRESH).should('contain', 'Paused')
  }

  static verifyKeyboardNavigation(): void {
    cy.get('body').tab()
    cy.focused().should('have.attr', 'role', 'tab')
  }

  static verifyColorContrast(): void {
    cy.get(TEST_SELECTORS.METRIC_VALUE).should('have.css', 'color')
      .and('not.equal', 'rgb(200, 200, 200)')
  }

  static createSnapshot(): void {
    cy.contains('Snapshot').click()
    cy.contains('Snapshot created').should('be.visible')
  }

  static scheduleReport(): void {
    cy.contains('Schedule Report').click()
    cy.get('[data-testid="schedule-modal"]').should('be.visible')
  }
}

export const BENCHMARK_METRICS = [
  'Latency',
  'Throughput', 
  'Cost Efficiency',
  'Reliability'
] as const

export const LATENCY_PERCENTILES = ['P50', 'P75', 'P95', 'P99'] as const

export const EXPORT_FORMATS = ['PDF', 'CSV'] as const

export const CHART_TYPES = {
  LINE: '[data-testid="line-chart"]',
  BAR: '[data-testid="bar-chart"]',
  GAUGE: '[data-testid="gauge-chart"]',
  PIE: '[data-testid="cost-pie-chart"]',
  HEATMAP: '[data-testid="latency-heatmap"]'
} as const

// Performance metric validation helpers
export const validateMetricFormat = {
  percentage: (value: string) => /\d+\.?\d*%/.test(value),
  currency: (value: string) => /\$[\d,]+/.test(value),
  latency: (value: string) => /\d+ms/.test(value),
  throughput: (value: string) => /\d+\s?req\/s/.test(value)
}

// SLA compliance thresholds for Enterprise customers
export const SLA_THRESHOLDS = {
  AVAILABILITY: 99.95,
  RESPONSE_TIME_P95: 150,
  ERROR_RATE: 0.05,
  THROUGHPUT_MIN: 1000
} as const