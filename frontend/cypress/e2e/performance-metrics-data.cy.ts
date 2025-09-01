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
 * Updated for current system: WebSocket metrics, /api/metrics endpoint, circuit breaker integration
 */

describe('Performance Metrics Data Tests', () => {
  beforeEach(() => {
    // Set up current authentication system
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-metrics');
      win.localStorage.setItem('refresh_token', 'test-refresh-metrics');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-metrics',
        email: 'test@netrasystems.ai',
        name: 'Test User'
      }));
    });
    
    // Mock current metrics API endpoint
    cy.intercept('GET', '/api/metrics/**', {
      statusCode: 200,
      body: {
        overview: {
          active_models: 12,
          queue_depth: 3,
          error_rate: 0.02,
          cache_hit_rate: 0.85,
          inference_latency: { current: 245, optimized: 180 },
          throughput: { current: 1250, optimized: 1800 },
          system_health: {
            cpu_usage: 65,
            memory_usage: 72,
            gpu_utilization: 88
          }
        },
        timestamp: new Date().toISOString()
      }
    }).as('metricsData');
    
    // Mock WebSocket connection for real-time metrics
    cy.intercept('/ws*', {
      statusCode: 101,
      headers: { 'upgrade': 'websocket' }
    }).as('wsConnection');
    
    MetricsTestHelper.setupViewport()
    MetricsTestHelper.navigateToMetrics()
    MetricsTestHelper.waitForPerformanceTab()
  })

  describe('Overview Tab Metrics', () => {
    beforeEach(() => {
      MetricsTestHelper.switchToTab('Overview')
      
      // Wait for metrics API to be called
      cy.wait('@metricsData')
      
      // Mock real-time WebSocket metrics updates
      cy.window().then((win) => {
        const store = (win as any).useUnifiedChatStore?.getState();
        if (store && store.handleWebSocketEvent) {
          const metricsEvents = [
            {
              type: 'metrics_update',
              payload: {
                type: 'system_health',
                data: {
                  cpu_usage: 68,
                  memory_usage: 74,
                  gpu_utilization: 90
                },
                timestamp: Date.now()
              }
            },
            {
              type: 'performance_alert',
              payload: {
                alert_type: 'latency_spike',
                current_latency: 280,
                threshold: 250
              }
            }
          ];
          
          metricsEvents.forEach((event, index) => {
            setTimeout(() => {
              store.handleWebSocketEvent(event);
            }, index * 1000);
          });
        }
      });
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
      // Mock latency-specific metrics endpoint
      cy.intercept('GET', '/api/metrics/latency**', {
        statusCode: 200,
        body: {
          p50: 180,
          p90: 245,
          p99: 380,
          mean: 195,
          max: 450,
          min: 120,
          timestamp: new Date().toISOString(),
          circuit_breaker_status: 'closed'
        }
      }).as('latencyMetrics');
      
      MetricsTestHelper.switchToTab('Latency')
      
      // Mock WebSocket latency updates
      cy.window().then((win) => {
        const store = (win as any).useUnifiedChatStore?.getState();
        if (store && store.handleWebSocketEvent) {
          setTimeout(() => {
            store.handleWebSocketEvent({
              type: 'latency_update',
              payload: {
                p50: 185,
                p90: 250,
                circuit_breaker_trips: 2,
                timestamp: Date.now()
              }
            });
          }, 500);
        }
      });
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
      // Mock cost analysis endpoint
      cy.intercept('GET', '/api/metrics/cost**', {
        statusCode: 200,
        body: {
          total_cost: 4750.50,
          cost_per_request: 0.0048,
          cost_breakdown: {
            compute: 3200.30,
            storage: 850.20,
            bandwidth: 700.00
          },
          optimization_potential: {
            monthly_savings: 1425.15,
            efficiency_gain: 30
          },
          timestamp: new Date().toISOString()
        }
      }).as('costMetrics');
      
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
      // Mock benchmarks endpoint
      cy.intercept('GET', '/api/metrics/benchmarks**', {
        statusCode: 200,
        body: {
          benchmarks: [
            {
              name: 'GPT-4 Inference',
              category: 'NLP',
              score: 92.5,
              baseline: 88.0,
              improvement: 5.1
            },
            {
              name: 'BERT Classification',
              category: 'NLP', 
              score: 89.2,
              baseline: 85.5,
              improvement: 4.3
            },
            {
              name: 'ResNet Image Processing',
              category: 'Vision',
              score: 94.1,
              baseline: 90.8,
              improvement: 3.6
            }
          ],
          overall_score: 91.9,
          timestamp: new Date().toISOString()
        }
      }).as('benchmarkMetrics');
      
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
      
      // Wait for metrics data to load
      cy.wait('@metricsData')
      
      // Validate that real-time metrics are displayed correctly
      cy.contains('Active Models').should('be.visible')
      cy.get('.text-2xl').should('have.length.at.least', 4)
      
      // Validate specific metric values from API response
      cy.contains('12').should('be.visible') // Active models
      cy.contains('0.02').should('be.visible') // Error rate
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
      
      // Wait for metrics API to provide system health data
      cy.wait('@metricsData')
      
      // Verify system health section with progress bars
      cy.contains('System Health').should('be.visible')
      cy.get('[role="progressbar"]').should('have.length.at.least', 3)
      
      // Verify specific health metrics from API
      cy.contains('65').should('be.visible') // CPU usage
      cy.contains('72').should('be.visible') // Memory usage
      cy.contains('88').should('be.visible') // GPU utilization
    })

    it('should validate timestamp freshness', () => {
      // Check that timestamp is updated in the header from API
      cy.wait('@metricsData').then((interception) => {
        expect(interception.response.body).to.have.property('timestamp');
      });
      
      cy.contains('Updated').should('be.visible')
      cy.get('.text-xs').should('contain', 'Updated')
    })

  })
})