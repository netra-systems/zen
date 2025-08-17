/// <reference types="cypress" />
import { 
  MetricsTestHelper, 
  TEST_SELECTORS, 
  COST_CATEGORIES, 
  BENCHMARK_METRICS,
  LATENCY_PERCENTILES,
  PERFORMANCE_THRESHOLDS,
  validateMetricFormat 
} from '../support/metrics-test-utils'

/**
 * Performance Metrics Data Tests
 * BVJ: Enterprise segment - validates platform performance, supports SLA compliance
 * Tests: Metric data accuracy, thresholds, business KPIs
 */

describe('Performance Metrics Data Tests', () => {
  beforeEach(() => {
    MetricsTestHelper.setupViewport()
    MetricsTestHelper.navigateToMetrics()
    MetricsTestHelper.waitForPerformanceTab()
  })

  describe('Overview Tab Metrics', () => {
    beforeEach(() => {
      MetricsTestHelper.switchToTab('Overview')
    })

    it('should display system health score within threshold', () => {
      cy.contains('System Health').should('be.visible')
      cy.get('[data-testid="health-score"]')
        .should('contain', '%')
        .invoke('text')
        .then(text => {
          const score = parseInt(text.replace('%', ''))
          expect(score).to.be.at.least(PERFORMANCE_THRESHOLDS.HEALTH_SCORE_MIN)
        })
    })

    it('should show health status indicator with correct color', () => {
      cy.get('[data-testid="health-indicator"]').should('be.visible')
      cy.get('[data-testid="health-indicator"]').should('have.class', 'bg-green-500')
    })

    it('should display active optimizations count', () => {
      cy.contains('Active Optimizations').should('be.visible')
      cy.get('[data-testid="optimization-count"]').should('contain', /\d+/)
    })

    it('should show uptime percentage meeting SLA', () => {
      cy.contains('Uptime').should('be.visible')
      cy.contains('99.9%').should('be.visible')
    })

    it('should display request throughput metrics', () => {
      cy.contains('Throughput').should('be.visible')
      cy.contains('req/s').should('be.visible')
    })

    it('should show error rate within acceptable limits', () => {
      cy.contains('Error Rate').should('be.visible')
      cy.get('[data-testid="error-rate"]')
        .invoke('text')
        .should('match', /\d+\.?\d*%/)
    })

    it('should display resource utilization gauges', () => {
      cy.contains('CPU Usage').should('be.visible')
      cy.contains('Memory Usage').should('be.visible')
      cy.get('[data-testid="cpu-gauge"]').should('be.visible')
      cy.get('[data-testid="memory-gauge"]').should('be.visible')
    })

  })

  describe('Latency Tab Metrics', () => {
    beforeEach(() => {
      MetricsTestHelper.switchToTab('Latency')
    })

    it('should display latency distribution chart', () => {
      MetricsTestHelper.verifyChartVisible('[data-testid="latency-chart"]')
    })

    it('should show all percentile values', () => {
      LATENCY_PERCENTILES.forEach(percentile => {
        cy.contains(percentile).parent().contains(/\d+ms/).should('be.visible')
      })
    })

    it('should validate P99 latency meets SLA threshold', () => {
      cy.contains('P99').parent()
        .invoke('text')
        .then(text => {
          const latency = parseInt(text.match(/\d+/)?.[0] || '0')
          expect(latency).to.be.at.most(PERFORMANCE_THRESHOLDS.LATENCY_P99_MAX)
        })
    })

    it('should display average latency', () => {
      cy.contains('Average').should('be.visible')
      cy.get('[data-testid="avg-latency"]').should('contain', 'ms')
    })

    it('should show latency trend with direction indicator', () => {
      cy.contains('Trend').should('be.visible')
      cy.get('[data-testid="latency-trend"]').should('be.visible')
      cy.contains(/↑|↓|→/).should('be.visible')
    })

    it('should display service-level latency breakdown', () => {
      cy.contains('Service Breakdown').should('be.visible')
      cy.get('[data-testid="service-latency"]').should('have.length.at.least', 3)
    })

    it('should show latency heatmap with time buckets', () => {
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
      MetricsTestHelper.switchToTab('Cost Analysis')
    })

    it('should display total monthly cost', () => {
      cy.contains('Total Monthly Cost').should('be.visible')
      cy.get('[data-testid="total-cost"]')
        .invoke('text')
        .should('match', /\$[\d,]+/)
    })

    it('should show cost breakdown pie chart', () => {
      MetricsTestHelper.verifyChartVisible('[data-testid="cost-pie-chart"]')
    })

    it('should display all cost categories', () => {
      COST_CATEGORIES.forEach(category => {
        cy.contains(category).should('be.visible')
      })
    })

    it('should show cost trend graph over time', () => {
      MetricsTestHelper.verifyChartVisible('[data-testid="cost-trend-graph"]')
      cy.contains('Last 30 Days').should('be.visible')
    })

    it('should display savings achieved this month', () => {
      cy.contains('Savings This Month').should('be.visible')
      cy.get('[data-testid="savings-amount"]')
        .invoke('text')
        .should('match', /\$[\d,]+/)
      cy.get('[data-testid="savings-percentage"]')
        .invoke('text')
        .should('match', /\d+%/)
    })

    it('should show cost per request metric', () => {
      cy.contains('Cost per 1K Requests').should('be.visible')
      cy.get('[data-testid="cost-per-request"]')
        .invoke('text')
        .should('match', /\$\d+\.\d+/)
    })

    it('should display projected costs', () => {
      cy.contains('Projected Next Month').should('be.visible')
      cy.get('[data-testid="projected-cost"]')
        .invoke('text')
        .should('match', /\$[\d,]+/)
    })

    it('should show cost optimization recommendations', () => {
      cy.contains('Cost Optimization').should('be.visible')
      cy.get('[data-testid="cost-recommendation"]').should('have.length.at.least', 3)
    })
  })

  describe('Benchmarks Tab', () => {
    beforeEach(() => {
      MetricsTestHelper.switchToTab('Benchmarks')
    })

    it('should display performance index score', () => {
      cy.contains('Performance Index').should('be.visible')
      cy.get('[data-testid="performance-index"]')
        .should('contain', /\d+/)
        .invoke('text')
        .then(text => {
          const score = parseInt(text)
          expect(score).to.be.within(0, 100)
        })
    })

    it('should show industry comparison metrics', () => {
      cy.contains('Industry Average').should('be.visible')
      cy.contains('Your Performance').should('be.visible')
    })

    it('should display benchmark comparison chart', () => {
      MetricsTestHelper.verifyChartVisible('[data-testid="benchmark-chart"]')
      cy.get('[data-testid="benchmark-bar"]').should('have.length.at.least', 5)
    })

    it('should show percentile ranking', () => {
      cy.contains('Percentile Ranking').should('be.visible')
      cy.contains('Top').should('be.visible')
      cy.get('[data-testid="percentile-rank"]').should('contain', '%')
    })

    it('should display all benchmark metrics', () => {
      BENCHMARK_METRICS.forEach(metric => {
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

  describe('Metric Validation and Thresholds', () => {
    it('should validate percentage format compliance', () => {
      MetricsTestHelper.switchToTab('Overview')
      cy.get('[data-testid="health-score"]')
        .invoke('text')
        .then(text => {
          expect(validateMetricFormat.percentage(text)).to.be.true
        })
    })

    it('should validate currency format compliance', () => {
      MetricsTestHelper.switchToTab('Cost Analysis')
      cy.get('[data-testid="total-cost"]')
        .invoke('text')
        .then(text => {
          expect(validateMetricFormat.currency(text)).to.be.true
        })
    })

    it('should validate latency format compliance', () => {
      MetricsTestHelper.switchToTab('Latency')
      cy.get('[data-testid="avg-latency"]')
        .invoke('text')
        .then(text => {
          expect(validateMetricFormat.latency(text)).to.be.true
        })
    })

    it('should validate throughput format compliance', () => {
      MetricsTestHelper.switchToTab('Overview')
      cy.get('[data-testid="throughput-value"]')
        .invoke('text')
        .then(text => {
          expect(validateMetricFormat.throughput(text)).to.be.true
        })
    })

    it('should ensure metrics are within business thresholds', () => {
      MetricsTestHelper.switchToTab('Overview')
      cy.get('[data-testid="error-rate"]')
        .invoke('text')
        .then(text => {
          const rate = parseFloat(text.replace('%', ''))
          expect(rate).to.be.at.most(PERFORMANCE_THRESHOLDS.ERROR_RATE_MAX)
        })
    })

    it('should validate data freshness indicators', () => {
      cy.get('[data-testid="data-timestamp"]').should('be.visible')
      cy.contains(/\d+ seconds? ago/).should('be.visible')
    })

  })
})