/// <reference types="cypress" />
import { SyntheticDataPageObject } from './utils/synthetic-data-page-object'

/**
 * Quality Assurance Tests for Synthetic Data Generation Page
 * Tests: Mobile responsiveness, performance, accessibility, and error handling
 * Business Value: Growth segment - ensures quality user experience across all devices and scenarios
 */

describe('Synthetic Data Generation - Quality Assurance', () => {
  beforeEach(() => {
    SyntheticDataPageObject.visitPage()
  })

  describe('Mobile Responsiveness', () => {
    beforeEach(() => {
      SyntheticDataPageObject.setMobileViewport()
    })

    it('should adapt to mobile viewport', () => {
      cy.contains('Synthetic Data Generation').should('be.visible')
      cy.get(SyntheticDataPageObject.selectors.page).should('be.visible')
    })

    it('should stack configuration fields on mobile', () => {
      SyntheticDataPageObject.verifyMobileLayout()
    })

    it('should show mobile-optimized controls', () => {
      cy.get('input[type="range"]').should('be.visible')
      cy.get(SyntheticDataPageObject.selectors.generateButton)
        .should('have.css', 'width', '100%')
    })

    it('should handle mobile pattern selection', () => {
      SyntheticDataPageObject.selectWorkloadPattern('Burst')
      SyntheticDataPageObject.verifyPatternSelected('Burst')
    })

    it('should maintain functionality on tablet viewport', () => {
      cy.viewport('ipad-2')
      SyntheticDataPageObject.setTraceCount('2000')
      SyntheticDataPageObject.startGeneration()
      cy.contains('Generating').should('be.visible')
    })

    it('should handle touch interactions', () => {
      cy.get(SyntheticDataPageObject.selectors.errorRateSlider)
        .trigger('touchstart', { which: 1 })
        .trigger('touchmove', { clientX: 200, clientY: 200 })
        .trigger('touchend')
      cy.contains('%').should('be.visible')
    })

    it('should optimize mobile navigation', () => {
      cy.get('[data-testid="mobile-menu"]').should('be.visible')
      cy.get('[data-testid="mobile-menu"]').click()
      cy.contains('Advanced Options').should('be.visible')
    })

    it('should handle mobile text input', () => {
      SyntheticDataPageObject.setTraceCount('3000')
      cy.get(SyntheticDataPageObject.selectors.tracesInput)
        .should('have.value', '3000')
    })
  })

  describe('Performance and Error Handling', () => {
    it('should handle network errors gracefully', () => {
      SyntheticDataPageObject.simulateNetworkError()
      SyntheticDataPageObject.startGeneration()
      cy.contains('Generation failed').should('be.visible')
      cy.contains('Retry').should('be.visible')
    })

    it('should timeout long-running generations', () => {
      SyntheticDataPageObject.simulateTimeout()
      SyntheticDataPageObject.startGeneration()
      cy.wait(10000)
      cy.contains('Generation timed out').should('be.visible')
    })

    it('should handle invalid server responses', () => {
      SyntheticDataPageObject.simulateInvalidResponse()
      SyntheticDataPageObject.startGeneration()
      cy.contains('Invalid response').should('be.visible')
    })

    it('should prevent duplicate submissions', () => {
      SyntheticDataPageObject.startGeneration()
      cy.get(SyntheticDataPageObject.selectors.generateButton)
        .should('be.disabled')
    })

    it('should handle browser memory limitations', () => {
      SyntheticDataPageObject.setTraceCount('1000000')
      SyntheticDataPageObject.startGeneration()
      cy.contains('Memory limit exceeded').should('be.visible')
      cy.contains('Reduce dataset size').should('be.visible')
    })

    it('should recover from connection interruptions', () => {
      SyntheticDataPageObject.startGeneration()
      cy.wait(1000)
      cy.window().its('navigator').invoke('serviceWorker.ready')
      cy.window().then((win) => {
        win.dispatchEvent(new Event('offline'))
      })
      cy.contains('Connection lost').should('be.visible')
      cy.window().then((win) => {
        win.dispatchEvent(new Event('online'))
      })
      cy.contains('Connection restored').should('be.visible')
    })

    it('should handle concurrent user sessions', () => {
      cy.window().then((win) => {
        win.open('/synthetic-data-generation', '_blank')
      })
      SyntheticDataPageObject.startGeneration()
      cy.contains('Multiple sessions detected').should('be.visible')
    })

    it('should validate input sanitization', () => {
      SyntheticDataPageObject.setTraceCount('<script>alert("xss")</script>')
      cy.get(SyntheticDataPageObject.selectors.tracesInput)
        .should('not.contain', '<script>')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      SyntheticDataPageObject.verifyAccessibility()
    })

    it('should support keyboard navigation', () => {
      cy.get('body').tab()
      cy.focused().should('have.attr', 'name', 'traces')
      cy.focused().tab()
      cy.focused().should('have.attr', 'name', 'users')
    })

    it('should announce status changes to screen readers', () => {
      cy.get('[role="status"]').should('exist')
      SyntheticDataPageObject.startGeneration()
      cy.get('[role="status"]').should('contain', 'Generating')
    })

    it('should have proper form labels', () => {
      cy.get('label[for="traces"]').should('contain', 'Number of Traces')
      cy.get('label[for="users"]').should('contain', 'Number of Users')
    })

    it('should provide keyboard shortcuts', () => {
      cy.get('body').type('{ctrl+g}')
      cy.contains('Generating').should('be.visible')
    })

    it('should support high contrast mode', () => {
      cy.get('body').invoke('addClass', 'high-contrast')
      cy.get(SyntheticDataPageObject.selectors.generateButton)
        .should('have.css', 'border-width', '2px')
    })

    it('should handle screen reader announcements', () => {
      cy.get('[aria-live="polite"]').should('exist')
      SyntheticDataPageObject.startGeneration()
      cy.get('[aria-live="polite"]')
        .should('contain', 'Data generation started')
    })

    it('should provide focus indicators', () => {
      cy.get(SyntheticDataPageObject.selectors.tracesInput).focus()
      cy.focused().should('have.css', 'outline-width', '2px')
    })
  })

  describe('Cross-Browser Compatibility', () => {
    it('should handle browser-specific APIs gracefully', () => {
      cy.window().then((win) => {
        if (!win.navigator.clipboard) {
          cy.contains('Copy to Clipboard').click()
          cy.contains('Clipboard not supported').should('be.visible')
        }
      })
    })

    it('should support older browser versions', () => {
      cy.window().then((win) => {
        // Simulate older browser without modern features
        delete win.fetch
        SyntheticDataPageObject.startGeneration()
        cy.contains('Generating').should('be.visible')
      })
    })

    it('should handle different time zones', () => {
      cy.clock(new Date('2024-01-01T12:00:00.000Z'))
      SyntheticDataPageObject.startGeneration()
      cy.wait(3000)
      cy.contains('12:00').should('be.visible')
    })

    it('should support different language settings', () => {
      cy.window().then((win) => {
        Object.defineProperty(win.navigator, 'language', {
          value: 'es-ES',
          configurable: true
        })
      })
      cy.reload()
      cy.contains('Generar Datos').should('be.visible')
    })
  })

  describe('Security and Privacy', () => {
    it('should sanitize user inputs', () => {
      cy.get('input[name="serviceName"]').type('<img src=x onerror=alert(1)>')
      cy.get('input[name="serviceName"]')
        .should('not.contain', '<img')
        .should('not.contain', 'onerror')
    })

    it('should handle sensitive data appropriately', () => {
      SyntheticDataPageObject.openAdvancedOptions()
      cy.get('input[name="apiKey"]').type('secret-key-123')
      cy.get('input[name="apiKey"]').should('have.attr', 'type', 'password')
    })

    it('should prevent CSRF attacks', () => {
      cy.get('meta[name="csrf-token"]').should('exist')
      cy.request({
        method: 'POST',
        url: '/api/synthetic-data/generate',
        failOnStatusCode: false,
        headers: {
          'Content-Type': 'application/json'
        },
        body: { traces: 1000 }
      }).then((response) => {
        expect(response.status).to.eq(403)
      })
    })

    it('should implement content security policy', () => {
      cy.document().then((doc) => {
        const cspMeta = doc.querySelector('meta[http-equiv="Content-Security-Policy"]')
        expect(cspMeta).to.exist
      })
    })
  })

  describe('Offline Support', () => {
    it('should cache critical resources', () => {
      cy.window().its('navigator.serviceWorker.ready').then(() => {
        cy.window().then((win) => {
          win.dispatchEvent(new Event('offline'))
        })
        cy.reload()
        cy.contains('Synthetic Data Generation').should('be.visible')
      })
    })

    it('should queue actions when offline', () => {
      SyntheticDataPageObject.setTraceCount('2000')
      cy.window().then((win) => {
        win.dispatchEvent(new Event('offline'))
      })
      SyntheticDataPageObject.startGeneration()
      cy.contains('Action queued for when online').should('be.visible')
    })

    it('should sync when connection is restored', () => {
      cy.window().then((win) => {
        win.dispatchEvent(new Event('offline'))
      })
      SyntheticDataPageObject.setTraceCount('3000')
      cy.window().then((win) => {
        win.dispatchEvent(new Event('online'))
      })
      cy.contains('Syncing changes').should('be.visible')
    })
  })

  describe('Performance Optimization', () => {
    it('should load page within performance budget', () => {
      cy.window().its('performance').then((perf) => {
        const navigationEntry = perf.getEntriesByType('navigation')[0]
        expect(navigationEntry.loadEventEnd - navigationEntry.fetchStart)
          .to.be.lessThan(3000)
      })
    })

    it('should lazy load non-critical components', () => {
      cy.get('[data-testid="advanced-analytics"]').should('not.exist')
      cy.contains('Analytics').click()
      cy.get('[data-testid="advanced-analytics"]').should('be.visible')
    })

    it('should optimize large dataset rendering', () => {
      SyntheticDataPageObject.setTraceCount('10000')
      SyntheticDataPageObject.startGeneration()
      cy.wait(3000)
      cy.get('[data-testid="virtual-scroll"]').should('be.visible')
      cy.get(SyntheticDataPageObject.selectors.previewRow)
        .should('have.length.at.most', 50)
    })

    it('should debounce user inputs', () => {
      const start = Date.now()
      for (let i = 0; i < 10; i++) {
        SyntheticDataPageObject.setTraceCount(`${1000 + i}`)
      }
      cy.wait(500)
      const end = Date.now()
      expect(end - start).to.be.lessThan(1000)
    })
  })
})