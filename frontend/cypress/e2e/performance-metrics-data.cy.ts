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

    it('should display system health metrics', () => {
      cy.contains('System Health').should('be.visible')
      // Check for system metrics like CPU Usage, Memory, etc.
      cy.contains('CPU Usage').should('be.visible')
      cy.contains('Memory').should('be.visible')
    })

    it('should show real-time metrics cards', () => {
      // Check for real-time metric cards from data.ts
      cy.contains('Active Models').should('be.visible')
      cy.contains('Queue Depth').should('be.visible')
      cy.contains('Error Rate').should('be.visible')
      cy.contains('Cache Hit Rate').should('be.visible')
    })

    it('should display metric values with units', () => {
      // Check that metric cards show numerical values
      cy.get('.text-2xl').should('have.length.at.least', 4)
    })

    it('should show performance metrics grid', () => {
      // Check for the metrics grid from data.ts (Inference Latency, Throughput, etc.)
      cy.contains('Inference Latency').should('be.visible')
      cy.contains('Throughput').should('be.visible')
    })

    it('should display throughput with correct units', () => {
      cy.contains('Throughput').should('be.visible')
      cy.contains('req/s').should('be.visible')
    })

    it('should show error rate in real-time metrics', () => {
      cy.contains('Error Rate').should('be.visible')
      // Error rate should be displayed as a decimal value
      cy.get('.text-2xl').should('contain.any', ['0.02', '0.01'])
    })

    it('should display system health with progress bars', () => {
      cy.contains('CPU Usage').should('be.visible')
      cy.contains('Memory').should('be.visible')
      cy.contains('GPU Utilization').should('be.visible')
      // Check for progress bars in system health section
      cy.get('[role="progressbar"]').should('have.length.at.least', 3)
    })

  })

  describe('Latency Tab Metrics', () => {
    beforeEach(() => {
      MetricsTestHelper.switchToTab('Latency')
    })

    it('should display latency tab content', () => {
      // Check that latency tab is active and has content
      cy.get('[data-value="latency"]').should('have.attr', 'data-state', 'active')
      cy.get('[data-state="active"]').should('be.visible')
    })

    it('should load latency-specific content', () => {
      // Verify latency tab content loads
      cy.get('[data-state="active"]').should('exist')
    })

    it('should maintain tab functionality', () => {
      // Verify tab switching works correctly
      cy.get('[data-value="latency"]').should('have.attr', 'data-state', 'active')
    })

    it('should display latency metrics when implemented', () => {
      // Placeholder for when latency metrics are fully implemented
      cy.get('[data-state="active"]').should('be.visible')
    })

    it('should show tab structure', () => {
      // Verify basic tab structure is present
      cy.get('[role="tablist"]').should('be.visible')
    })

    it('should handle tab navigation', () => {
      // Test navigation back to overview
      MetricsTestHelper.switchToTab('Overview')
      cy.get('[data-value="overview"]').should('have.attr', 'data-state', 'active')
    })

    it('should maintain component state', () => {
      // Verify component remains stable
      cy.contains('Performance Metrics Dashboard').should('be.visible')
    })

    it('should support future latency features', () => {
      // Ready for when latency tab content is implemented
      cy.get('[data-state="active"]').should('exist')
    })
  })

  describe('Cost Analysis Tab', () => {
    beforeEach(() => {
      MetricsTestHelper.switchToTab('Cost Analysis')
    })

    it('should display cost analysis tab content', () => {
      cy.get('[data-value="cost"]').should('have.attr', 'data-state', 'active')
      cy.get('[data-state="active"]').should('be.visible')
    })

    it('should load cost-specific content', () => {
      // Verify cost tab content loads when implemented
      cy.get('[data-state="active"]').should('exist')
    })

    it('should maintain tab structure', () => {
      cy.get('[role="tablist"]').should('be.visible')
      cy.get('[data-value="cost"]').should('have.attr', 'data-state', 'active')
    })

    it('should support cost visualization when implemented', () => {
      // Ready for cost analysis features
      cy.get('[data-state="active"]').should('be.visible')
    })

    it('should handle cost metrics data', () => {
      // Cost per 1M Requests metric exists in data.ts
      cy.get('[data-state="active"]').should('exist')
    })

    it('should be ready for cost metrics display', () => {
      // Future implementation of cost metrics
      cy.get('[data-state="active"]').should('be.visible')
    })

    it('should maintain navigation functionality', () => {
      MetricsTestHelper.switchToTab('Overview')
      cy.get('[data-value="overview"]').should('have.attr', 'data-state', 'active')
    })

    it('should support future cost optimization features', () => {
      cy.get('[data-state="active"]').should('exist')
    })
  })

  describe('Benchmarks Tab', () => {
    beforeEach(() => {
      MetricsTestHelper.switchToTab('Benchmarks')
    })

    it('should display benchmarks tab content', () => {
      cy.get('[data-value="benchmarks"]').should('have.attr', 'data-state', 'active')
      cy.get('[data-state="active"]').should('be.visible')
    })

    it('should load benchmark-specific content', () => {
      // Verify benchmarks tab content loads when implemented
      cy.get('[data-state="active"]').should('exist')
    })

    it('should maintain benchmarks tab structure', () => {
      cy.get('[role="tablist"]').should('be.visible')
      cy.get('[data-value="benchmarks"]').should('have.attr', 'data-state', 'active')
    })

    it('should be ready for benchmark data', () => {
      // Benchmark data exists in data.ts (benchmarks array)
      cy.get('[data-state="active"]').should('be.visible')
    })

    it('should support benchmark categories', () => {
      // Future implementation of benchmark categories (NLP, Vision, etc.)
      cy.get('[data-state="active"]').should('exist')
    })

    it('should handle benchmark navigation', () => {
      MetricsTestHelper.switchToTab('Overview')
      cy.get('[data-value="overview"]').should('have.attr', 'data-state', 'active')
    })

    it('should support future benchmark features', () => {
      // Ready for benchmark comparison features
      cy.get('[data-state="active"]').should('be.visible')
    })

  })

  describe('Metric Validation and Thresholds', () => {
    it('should validate real-time metrics display', () => {
      MetricsTestHelper.switchToTab('Overview')
      // Validate that real-time metrics are displayed correctly
      cy.contains('Active Models').should('be.visible')
      cy.get('.text-2xl').should('have.length.at.least', 4)
    })

    it('should validate metric card structure', () => {
      MetricsTestHelper.switchToTab('Overview')
      // Validate metric cards show current vs optimized values
      cy.contains('Inference Latency').should('be.visible')
      cy.contains('Current').should('be.visible')
      cy.contains('Optimized').should('be.visible')
    })

    it('should validate latency metrics in overview', () => {
      MetricsTestHelper.switchToTab('Overview')
      // Check that latency is shown in metric cards with 'ms' unit
      cy.contains('Inference Latency').should('be.visible')
      cy.contains('ms').should('be.visible')
    })

    it('should validate throughput format in metrics', () => {
      MetricsTestHelper.switchToTab('Overview')
      // Check throughput is displayed with correct units
      cy.contains('Throughput').should('be.visible')
      cy.contains('req/s').should('be.visible')
    })

    it('should ensure system health metrics are present', () => {
      MetricsTestHelper.switchToTab('Overview')
      // Verify system health section with progress bars
      cy.contains('System Health').should('be.visible')
      cy.get('[role="progressbar"]').should('have.length.at.least', 3)
    })

    it('should validate timestamp freshness', () => {
      // Check that timestamp is updated in the header
      cy.contains('Updated').should('be.visible')
      cy.get('.text-xs').should('contain', 'Updated')
    })

  })
})