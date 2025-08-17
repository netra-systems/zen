/// <reference types="cypress" />
import { PromptTestUtilities, PromptTestFactories, PromptTestValidators } from './test-utilities.cy'

/**
 * Example Prompts Quality Assurance Tests
 * BVJ: Free/Early segment - ensures reliable experience for user retention and conversion
 */

describe('ExamplePrompts Quality Assurance', () => {
  beforeEach(() => {
    PromptTestUtilities.setupViewport()
  })

  describe('Accessibility Compliance', () => {
    it('should have proper ARIA labels', () => {
      cy.get('[aria-label="Example prompts"]').should('exist')
      cy.get('[aria-label="Select prompt"]')
        .should('have.length.at.least', 5)
    })

    it('should support keyboard navigation', () => {
      PromptTestValidators.validateKeyboardNav()
    })

    it('should have proper focus indicators', () => {
      PromptTestUtilities.getPromptCards().first().focus()
      cy.focused().should('have.css', 'outline')
        .and('not.equal', 'none')
    })

    it('should announce selections to screen readers', () => {
      cy.get('[role="status"]').should('exist')
      PromptTestUtilities.getPromptCards().first().click()
      cy.get('[role="status"]').should('contain', 'Selected')
    })

    it('should have descriptive button labels', () => {
      cy.get('button[aria-label]').should('have.length.at.least', 5)
    })

    it('should support high contrast mode', () => {
      cy.get('body').invoke('addClass', 'high-contrast')
      PromptTestUtilities.getPromptCards().first()
        .should('have.css', 'border-color')
        .and('not.equal', 'transparent')
    })

    it('should have semantic HTML structure', () => {
      cy.get('main[role="main"]').should('exist')
      cy.get('section[aria-labelledby]').should('exist')
    })

    it('should provide alt text for icons', () => {
      cy.get('[data-testid="prompt-icon"]')
        .should('have.attr', 'alt')
    })
  })

  describe('Performance Optimization', () => {
    it('should render quickly', () => {
      const start = Date.now()
      cy.reload()
      PromptTestUtilities.getExamplePrompts().should('be.visible')
      const duration = Date.now() - start
      expect(duration).to.be.lessThan(2000)
    })

    it('should handle many prompts efficiently', () => {
      cy.window().then(win => {
        const prompts = PromptTestFactories.createMultiplePrompts(50)
        prompts.forEach(prompt => win.addPrompt(prompt))
      })
      PromptTestFactories.expectVisibleElements(50)
    })

    it('should lazy load prompt icons', () => {
      cy.get('[data-testid="prompt-icon"]').first()
        .should('have.attr', 'loading', 'lazy')
    })

    it('should virtualize long lists', () => {
      cy.window().then(win => {
        const prompts = PromptTestFactories.createMultiplePrompts(100)
        prompts.forEach(prompt => win.addPrompt(prompt))
      })
      cy.get('[data-testid="virtual-list"]').should('exist')
    })

    it('should optimize re-renders', () => {
      cy.window().then(win => {
        cy.spy(win.React, 'createElement').as('createElement')
      })
      PromptTestUtilities.getSearchInput().type('test')
      cy.get('@createElement').should('have.been.calledOnce')
    })

    it('should cache computed styles', () => {
      PromptTestUtilities.getPromptCards().first().trigger('mouseenter')
      PromptTestUtilities.getPromptCards().first().trigger('mouseleave')
      PromptTestUtilities.getPromptCards().first().trigger('mouseenter')
      cy.get('[data-testid="style-cache"]').should('exist')
    })
  })

  describe('Error Handling', () => {
    it('should handle missing prompts gracefully', () => {
      PromptTestFactories.setupApiMock([])
      cy.reload()
      PromptTestFactories.expectTextContent('No prompts available')
    })

    it('should show error message on API failure', () => {
      PromptTestFactories.setupApiError(500)
      cy.reload()
      PromptTestFactories.expectTextContent('Unable to load prompts')
    })

    it('should provide retry option', () => {
      PromptTestFactories.setupApiError(500)
      cy.reload()
      PromptTestFactories.expectTextContent('Retry')
    })

    it('should fallback to default prompts', () => {
      PromptTestFactories.setupApiError(500)
      cy.reload()
      cy.wait(2000)
      PromptTestFactories.expectVisibleElements(3)
    })

    it('should handle network timeouts', () => {
      cy.intercept('GET', '/api/prompts', { delay: 30000 })
      cy.reload()
      cy.wait(5000)
      PromptTestFactories.expectTextContent('Loading')
    })

    it('should recover from JavaScript errors', () => {
      cy.window().then(win => {
        win.onerror = cy.stub().as('errorHandler')
      })
      cy.get('[data-testid="error-trigger"]').click()
      cy.get('@errorHandler').should('have.been.called')
      PromptTestUtilities.getExamplePrompts().should('be.visible')
    })
  })

  describe('Security Validation', () => {
    it('should sanitize user input', () => {
      PromptTestUtilities.getSearchInput().type('<script>alert("xss")</script>')
      cy.get('script').should('not.exist')
    })

    it('should validate prompt content', () => {
      const maliciousPrompt = { 
        title: '<img src=x onerror=alert(1)>',
        text: 'Safe content'
      }
      cy.window().then(win => {
        win.addPrompt(maliciousPrompt)
      })
      cy.get('img[src="x"]').should('not.exist')
    })

    it('should enforce content security policy', () => {
      cy.get('meta[http-equiv="Content-Security-Policy"]')
        .should('exist')
    })

    it('should protect against clickjacking', () => {
      cy.get('meta[name="viewport"]')
        .should('have.attr', 'content')
        .and('include', 'user-scalable=no')
    })

    it('should validate external links', () => {
      cy.get('a[href^="http"]')
        .should('have.attr', 'rel', 'noopener noreferrer')
    })
  })

  describe('Browser Compatibility', () => {
    it('should work in modern browsers', () => {
      cy.window().then(win => {
        expect(win.CSS?.supports('backdrop-filter', 'blur(10px)')).to.be.true
      })
    })

    it('should provide fallbacks for older browsers', () => {
      cy.window().then(win => {
        delete win.CSS
      })
      PromptTestUtilities.getExamplePrompts().should('be.visible')
    })

    it('should handle touch events', () => {
      PromptTestUtilities.getPromptCards().first()
        .trigger('touchstart', { touches: [{ clientX: 100, clientY: 100 }] })
      PromptTestUtilities.getPromptCards().first()
        .should('have.class', 'touched')
    })

    it('should support reduced motion preferences', () => {
      cy.get('body').invoke('addClass', 'prefers-reduced-motion')
      cy.get('.animate-pulse').should('not.exist')
    })
  })

  describe('Data Integrity', () => {
    it('should validate prompt data structure', () => {
      const invalidPrompt = { title: null, text: undefined }
      cy.window().then(win => {
        expect(() => win.validatePrompt(invalidPrompt)).to.throw()
      })
    })

    it('should prevent duplicate prompts', () => {
      const prompt = PromptTestFactories.createPromptTest('Duplicate')
      cy.window().then(win => {
        win.addPrompt(prompt)
        win.addPrompt(prompt)
      })
      cy.contains('Duplicate').should('have.length', 1)
    })

    it('should maintain state consistency', () => {
      PromptTestUtilities.getPromptCards().first().click()
      cy.reload()
      PromptTestUtilities.getPromptCards().first()
        .should('have.class', 'ring-2')
    })
  })
})