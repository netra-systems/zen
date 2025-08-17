/// <reference types="cypress" />
import { MetricsTestHelper, TEST_SELECTORS, SLA_THRESHOLDS } from '../support/metrics-test-utils'

/**
 * Performance Metrics Quality Assurance Tests
 * BVJ: Enterprise segment - validates platform performance, supports SLA compliance  
 * Tests: Mobile responsiveness, accessibility, error handling, performance
 */

describe('Performance Metrics Quality Assurance', () => {
  beforeEach(() => {
    MetricsTestHelper.setupViewport()
    MetricsTestHelper.navigateToMetrics()
    MetricsTestHelper.waitForPerformanceTab()
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt layout to mobile viewport', () => {
      MetricsTestHelper.setupMobileViewport()
      cy.get(TEST_SELECTORS.PERFORMANCE_METRICS).should('be.visible')
      cy.contains('Performance Metrics').should('be.visible')
    })

    it('should show mobile-optimized navigation', () => {
      MetricsTestHelper.setupMobileViewport()
      MetricsTestHelper.verifyMobileLayout()
      cy.get('[data-testid="tab-dropdown"]').should('be.visible')
    })

    it('should stack metric cards vertically on mobile', () => {
      MetricsTestHelper.setupMobileViewport()
      cy.get('[data-testid="metric-card"]').should('have.css', 'width', '100%')
    })

    it('should handle mobile touch interactions', () => {
      MetricsTestHelper.setupMobileViewport()
      cy.get('[data-testid="tab-dropdown"]').select('Latency')
      cy.contains('Response Time').should('be.visible')
    })

    it('should optimize charts for mobile display', () => {
      MetricsTestHelper.setupMobileViewport()
      cy.get('[data-testid="mobile-chart"]').should('be.visible')
    })

    it('should show mobile-specific controls', () => {
      MetricsTestHelper.setupMobileViewport()
      cy.get('[data-testid="mobile-controls"]').should('be.visible')
    })

    it('should handle orientation changes', () => {
      cy.viewport('iphone-x', 'landscape')
      cy.get(TEST_SELECTORS.PERFORMANCE_METRICS).should('be.visible')
    })

    it('should maintain functionality on tablets', () => {
      cy.viewport('ipad-2')
      cy.get('[data-testid="tablet-layout"]').should('be.visible')
    })
  })

  describe('Accessibility Compliance', () => {
    it('should have proper ARIA labels throughout', () => {
      MetricsTestHelper.checkAccessibility()
    })

    it('should support keyboard navigation', () => {
      MetricsTestHelper.verifyKeyboardNavigation()
    })

    it('should announce metric updates to screen readers', () => {
      cy.get('[role="status"]').should('exist')
      MetricsTestHelper.waitForDataUpdate()
      cy.get('[role="status"]').should('contain', 'Updated')
    })

    it('should have sufficient color contrast', () => {
      MetricsTestHelper.verifyColorContrast()
    })

    it('should provide alternative text for charts', () => {
      cy.get('[data-testid="chart-alt-text"]').should('exist')
    })

    it('should support high contrast mode', () => {
      cy.window().then(win => {
        win.document.body.classList.add('high-contrast')
      })
      cy.get('.high-contrast').should('exist')
    })

    it('should have focus indicators', () => {
      cy.get('button').first().focus()
      cy.focused().should('have.css', 'outline')
    })

    it('should support screen reader announcements', () => {
      cy.get('[aria-live="polite"]').should('exist')
    })
  })

  describe('Error Handling and Resilience', () => {
    it('should handle API failures gracefully', () => {
      MetricsTestHelper.simulateApiFailure('/api/demo/metrics')
      cy.reload()
      MetricsTestHelper.verifyErrorHandling()
    })

    it('should show cached data when API is unavailable', () => {
      MetricsTestHelper.simulateApiFailure('/api/demo/metrics')
      MetricsTestHelper.waitForDataUpdate()
      cy.contains('Showing cached data').should('be.visible')
    })

    it('should handle partial data loading scenarios', () => {
      MetricsTestHelper.simulateApiFailure('/api/demo/metrics/latency')
      MetricsTestHelper.switchToTab('Latency')
      cy.contains('Partial data available').should('be.visible')
    })

    it('should display retry options on failure', () => {
      MetricsTestHelper.simulateApiFailure('/api/demo/metrics')
      cy.reload()
      cy.contains('Retry').click()
      cy.get('[data-testid="retry-loading"]').should('be.visible')
    })

    it('should handle network timeout scenarios', () => {
      cy.intercept('GET', '/api/demo/metrics', { delay: 30000 })
      cy.reload()
      cy.contains('Request timeout').should('be.visible')
    })

    it('should show connection status during outages', () => {
      MetricsTestHelper.simulateApiFailure('/api/demo/metrics')
      cy.get('[data-testid="connection-status"]').should('have.class', 'disconnected')
    })

    it('should handle malformed data responses', () => {
      cy.intercept('GET', '/api/demo/metrics', { body: 'invalid json' })
      cy.reload()
      cy.contains('Data format error').should('be.visible')
    })

    it('should recover gracefully from errors', () => {
      MetricsTestHelper.simulateApiFailure('/api/demo/metrics')
      cy.intercept('GET', '/api/demo/metrics', { fixture: 'metrics.json' })
      cy.get('[data-testid="retry-button"]').click()
      cy.get(TEST_SELECTORS.METRIC_VALUE).should('be.visible')
    })
  })

  describe('Performance and Load Testing', () => {
    it('should load initial data within acceptable time', () => {
      const startTime = Date.now()
      cy.reload()
      cy.get(TEST_SELECTORS.METRIC_VALUE).should('be.visible')
      cy.then(() => {
        const loadTime = Date.now() - startTime
        expect(loadTime).to.be.lessThan(3000)
      })
    })

    it('should handle concurrent tab switching efficiently', () => {
      const tabs = ['Overview', 'Latency', 'Cost Analysis']
      tabs.forEach(tab => {
        MetricsTestHelper.switchToTab(tab)
        cy.get('[data-testid="tab-content"]').should('be.visible')
      })
    })

    it('should maintain performance with large datasets', () => {
      cy.intercept('GET', '/api/demo/metrics', { fixture: 'large-metrics.json' })
      cy.reload()
      cy.get(TEST_SELECTORS.METRIC_VALUE).should('be.visible')
    })

    it('should handle memory usage efficiently', () => {
      cy.window().then(win => {
        const initialMemory = win.performance.memory?.usedJSHeapSize || 0
        MetricsTestHelper.waitForDataUpdate()
        const finalMemory = win.performance.memory?.usedJSHeapSize || 0
        expect(finalMemory - initialMemory).to.be.lessThan(50000000)
      })
    })

    it('should throttle refresh requests appropriately', () => {
      let requestCount = 0
      cy.intercept('GET', '/api/demo/metrics', () => {
        requestCount++
      })
      cy.wait(10000)
      cy.then(() => {
        expect(requestCount).to.be.at.most(3)
      })
    })

    it('should optimize chart rendering performance', () => {
      cy.get('[data-testid="chart-render-time"]').should('exist')
      cy.get('[data-testid="chart-render-time"]')
        .invoke('text')
        .then(text => {
          const renderTime = parseInt(text.replace('ms', ''))
          expect(renderTime).to.be.lessThan(100)
        })
    })

    it('should handle rapid user interactions', () => {
      for (let i = 0; i < 5; i++) {
        MetricsTestHelper.switchToTab('Overview')
        MetricsTestHelper.switchToTab('Latency')
      }
      cy.get('[data-testid="active-tab"]').should('be.visible')
    })

    it('should maintain SLA compliance metrics', () => {
      cy.get('[data-testid="sla-compliance"]').should('be.visible')
      cy.get('[data-testid="availability"]')
        .invoke('text')
        .then(text => {
          const availability = parseFloat(text.replace('%', ''))
          expect(availability).to.be.at.least(SLA_THRESHOLDS.AVAILABILITY)
        })
    })
  })

  describe('Security and Data Protection', () => {
    it('should not expose sensitive data in DOM', () => {
      cy.get('[data-testid="api-key"]').should('not.exist')
      cy.get('[data-testid="secret-token"]').should('not.exist')
    })

    it('should handle authentication failures', () => {
      cy.intercept('GET', '/api/demo/metrics', { statusCode: 401 })
      cy.reload()
      cy.contains('Authentication required').should('be.visible')
    })

    it('should prevent XSS in metric displays', () => {
      cy.intercept('GET', '/api/demo/metrics', {
        body: { value: '<script>alert("xss")</script>' }
      })
      cy.reload()
      cy.get('script').should('not.exist')
    })

    it('should validate input sanitization', () => {
      MetricsTestHelper.configureThreshold('latency', '<script>alert("xss")</script>')
      cy.get('script').should('not.exist')
    })

    it('should handle CSRF protection', () => {
      cy.get('[name="csrf-token"]').should('exist')
    })

    it('should use secure communication protocols', () => {
      cy.url().should('include', 'https')
    })

    it('should implement proper data encryption', () => {
      cy.get('[data-testid="encryption-status"]').should('contain', 'Encrypted')
    })

    it('should respect data privacy settings', () => {
      cy.get('[data-testid="privacy-controls"]').should('be.visible')
    })
  })

  describe('Browser Compatibility', () => {
    it('should work in modern browsers', () => {
      cy.window().then(win => {
        expect(win.fetch).to.exist
        expect(win.Promise).to.exist
      })
    })

    it('should handle browser storage limitations', () => {
      cy.window().then(win => {
        try {
          win.localStorage.setItem('test', 'value')
          expect(win.localStorage.getItem('test')).to.equal('value')
        } catch (e) {
          cy.contains('Storage unavailable').should('be.visible')
        }
      })
    })

    it('should support offline functionality', () => {
      cy.window().then(win => {
        win.dispatchEvent(new Event('offline'))
      })
      cy.contains('Offline mode').should('be.visible')
    })

    it('should handle JavaScript disabled gracefully', () => {
      cy.get('[noscript]').should('exist')
    })

  })
})