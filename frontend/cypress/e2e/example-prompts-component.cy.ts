/// <reference types="cypress" />

describe('ExamplePrompts Component E2E Tests', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/')
    cy.wait(500)
  })

  describe('Component Initialization', () => {
    it('should render ExamplePrompts component', () => {
      cy.get('[data-testid="example-prompts"]').should('be.visible')
    })

    it('should display section heading', () => {
      cy.contains('Quick Start').should('be.visible')
      cy.contains('Select an optimization scenario').should('be.visible')
    })

    it('should show all example prompt cards', () => {
      cy.get('[data-testid="prompt-card"]').should('have.length.at.least', 5)
    })

    it('should have glassmorphic styling', () => {
      cy.get('[data-testid="prompt-card"]').first().should('have.class', 'backdrop-blur')
      cy.get('.bg-gradient-to-br').should('exist')
    })

    it('should display icons for each prompt', () => {
      cy.get('[data-testid="prompt-icon"]').should('have.length.at.least', 5)
    })
  })

  describe('Prompt Content', () => {
    it('should display cost optimization prompt', () => {
      cy.contains('Reduce AI Costs').should('be.visible')
      cy.contains('Analyze and optimize').should('be.visible')
    })

    it('should display latency optimization prompt', () => {
      cy.contains('Improve Latency').should('be.visible')
      cy.contains('response times').should('be.visible')
    })

    it('should display model selection prompt', () => {
      cy.contains('Model Selection').should('be.visible')
      cy.contains('best model').should('be.visible')
    })

    it('should display capacity planning prompt', () => {
      cy.contains('Capacity Planning').should('be.visible')
      cy.contains('scale').should('be.visible')
    })

    it('should display performance audit prompt', () => {
      cy.contains('Performance Audit').should('be.visible')
      cy.contains('comprehensive analysis').should('be.visible')
    })

    it('should show prompt descriptions', () => {
      cy.get('[data-testid="prompt-description"]').should('have.length.at.least', 5)
    })
  })

  describe('Interaction and Animation', () => {
    it('should expand prompt on click', () => {
      cy.get('[data-testid="prompt-card"]').first().click()
      cy.get('[data-testid="prompt-card"]').first().should('have.class', 'scale-105')
    })

    it('should show hover effects', () => {
      cy.get('[data-testid="prompt-card"]').first().trigger('mouseenter')
      cy.get('[data-testid="prompt-card"]').first().should('have.css', 'transform')
        .and('not.equal', 'none')
    })

    it('should animate card appearance', () => {
      cy.get('[data-testid="prompt-card"]').first().should('have.css', 'animation')
    })

    it('should show gradient animation', () => {
      cy.get('.animate-gradient').should('exist')
    })

    it('should display pulse animation on new prompts', () => {
      cy.get('.animate-pulse').should('exist')
    })

    it('should handle rapid clicking', () => {
      const card = cy.get('[data-testid="prompt-card"]').first()
      for(let i = 0; i < 5; i++) {
        card.click()
      }
      cy.get('[data-testid="prompt-card"]').first().should('not.have.class', 'error')
    })
  })

  describe('Prompt Selection', () => {
    it('should populate message input on selection', () => {
      cy.get('[data-testid="prompt-card"]').first().click()
      cy.get('textarea[data-testid="message-input"]').should('have.value')
    })

    it('should copy exact prompt text', () => {
      cy.contains('Reduce AI Costs').click()
      cy.get('textarea[data-testid="message-input"]')
        .should('have.value')
        .and('include', 'cost reduction')
    })

    it('should highlight selected prompt', () => {
      cy.get('[data-testid="prompt-card"]').first().click()
      cy.get('[data-testid="prompt-card"]').first().should('have.class', 'ring-2')
    })

    it('should allow selecting different prompts', () => {
      cy.get('[data-testid="prompt-card"]').first().click()
      cy.get('[data-testid="prompt-card"]').last().click()
      cy.get('[data-testid="prompt-card"]').last().should('have.class', 'ring-2')
      cy.get('[data-testid="prompt-card"]').first().should('not.have.class', 'ring-2')
    })

    it('should trigger callback on selection', () => {
      cy.window().then(win => {
        cy.spy(win.console, 'log').as('consoleLog')
      })
      cy.get('[data-testid="prompt-card"]').first().click()
      cy.get('@consoleLog').should('have.been.called')
    })
  })

  describe('Collapsible Behavior', () => {
    it('should have collapse/expand button', () => {
      cy.get('[data-testid="toggle-prompts"]').should('be.visible')
    })

    it('should collapse prompt section', () => {
      cy.get('[data-testid="toggle-prompts"]').click()
      cy.get('[data-testid="prompt-card"]').should('not.be.visible')
    })

    it('should expand prompt section', () => {
      cy.get('[data-testid="toggle-prompts"]').click()
      cy.get('[data-testid="toggle-prompts"]').click()
      cy.get('[data-testid="prompt-card"]').should('be.visible')
    })

    it('should animate collapse/expand', () => {
      cy.get('[data-testid="prompts-container"]').should('have.css', 'transition')
    })

    it('should remember collapsed state', () => {
      cy.get('[data-testid="toggle-prompts"]').click()
      cy.reload()
      cy.get('[data-testid="prompt-card"]').should('not.be.visible')
    })

    it('should show chevron icon animation', () => {
      cy.get('[data-testid="chevron-icon"]').should('have.css', 'transform')
      cy.get('[data-testid="toggle-prompts"]').click()
      cy.get('[data-testid="chevron-icon"]').should('have.css', 'transform')
        .and('include', 'rotate')
    })
  })

  describe('Categories and Filtering', () => {
    it('should display prompt categories', () => {
      cy.contains('Optimization').should('be.visible')
      cy.contains('Analysis').should('be.visible')
      cy.contains('Planning').should('be.visible')
    })

    it('should group prompts by category', () => {
      cy.get('[data-testid="category-optimization"]').should('exist')
      cy.get('[data-testid="category-analysis"]').should('exist')
    })

    it('should show category badges', () => {
      cy.get('[data-testid="category-badge"]').should('have.length.at.least', 3)
    })

    it('should filter prompts by category', () => {
      cy.get('[data-testid="category-filter"]').click()
      cy.contains('Optimization').click()
      cy.get('[data-testid="prompt-card"]:visible').should('have.length.at.least', 2)
    })

    it('should highlight active category', () => {
      cy.get('[data-testid="category-filter"]').click()
      cy.contains('Analysis').click()
      cy.get('[data-testid="category-analysis"]').should('have.class', 'bg-primary')
    })
  })

  describe('Dynamic Content Updates', () => {
    it('should update based on context', () => {
      cy.window().then(win => {
        win.updateContext({ industry: 'Healthcare' })
      })
      cy.contains('Patient').should('be.visible')
    })

    it('should show industry-specific prompts', () => {
      cy.visit('/demo')
      cy.contains('Financial Services').click()
      cy.get('[data-testid="example-prompts"]').should('contain', 'Risk')
    })

    it('should refresh prompts periodically', () => {
      cy.get('[data-testid="prompt-card"]').then($initial => {
        const initialCount = $initial.length
        cy.wait(10000)
        cy.get('[data-testid="prompt-card"]').should('have.length', initialCount)
      })
    })

    it('should show trending prompts', () => {
      cy.get('[data-testid="trending-badge"]').should('exist')
      cy.contains('Trending').should('be.visible')
    })

    it('should display new prompt indicator', () => {
      cy.get('[data-testid="new-badge"]').should('exist')
      cy.contains('New').should('be.visible')
    })
  })

  describe('Prompt Templates', () => {
    it('should support template variables', () => {
      cy.get('[data-testid="prompt-card"]').first().click()
      cy.get('textarea[data-testid="message-input"]').should('contain', '{')
    })

    it('should highlight template placeholders', () => {
      cy.get('[data-testid="prompt-card"]').contains('{{workload}}').should('be.visible')
    })

    it('should allow editing template values', () => {
      cy.get('[data-testid="prompt-card"]').first().click()
      cy.get('[data-testid="template-editor"]').should('be.visible')
      cy.get('input[name="workload"]').type('ML inference')
    })

    it('should preview filled template', () => {
      cy.get('[data-testid="prompt-card"]').first().click()
      cy.get('input[name="workload"]').type('ML inference')
      cy.get('[data-testid="preview"]').should('contain', 'ML inference')
    })

    it('should validate template inputs', () => {
      cy.get('[data-testid="prompt-card"]').first().click()
      cy.get('input[name="requests"]').type('abc')
      cy.contains('Must be a number').should('be.visible')
    })
  })

  describe('Visual Design Elements', () => {
    it('should display gradient backgrounds', () => {
      cy.get('.from-purple-500').should('exist')
      cy.get('.to-pink-500').should('exist')
    })

    it('should show icon colors', () => {
      cy.get('[data-testid="prompt-icon"]').first()
        .should('have.css', 'color')
        .and('not.equal', 'rgb(0, 0, 0)')
    })

    it('should have rounded corners', () => {
      cy.get('[data-testid="prompt-card"]').first()
        .should('have.css', 'border-radius')
        .and('not.equal', '0px')
    })

    it('should display shadows', () => {
      cy.get('[data-testid="prompt-card"]').first()
        .should('have.css', 'box-shadow')
        .and('not.equal', 'none')
    })

    it('should show border effects', () => {
      cy.get('[data-testid="prompt-card"]').first()
        .should('have.css', 'border')
    })
  })

  describe('Copy to Clipboard', () => {
    it('should have copy button on each prompt', () => {
      cy.get('[data-testid="copy-prompt"]').should('have.length.at.least', 5)
    })

    it('should copy prompt to clipboard', () => {
      cy.get('[data-testid="copy-prompt"]').first().click()
      cy.contains('Copied!').should('be.visible')
    })

    it('should show copy success animation', () => {
      cy.get('[data-testid="copy-prompt"]').first().click()
      cy.get('[data-testid="copy-success"]').should('have.class', 'animate-bounce')
    })

    it('should reset copy indicator', () => {
      cy.get('[data-testid="copy-prompt"]').first().click()
      cy.contains('Copied!').should('be.visible')
      cy.wait(2000)
      cy.contains('Copied!').should('not.exist')
    })
  })

  describe('Search and Discovery', () => {
    it('should display search input', () => {
      cy.get('[data-testid="prompt-search"]').should('be.visible')
    })

    it('should filter prompts by search', () => {
      cy.get('[data-testid="prompt-search"]').type('cost')
      cy.get('[data-testid="prompt-card"]:visible').should('have.length.at.least', 1)
      cy.contains('Reduce AI Costs').should('be.visible')
    })

    it('should show no results message', () => {
      cy.get('[data-testid="prompt-search"]').type('xyz123')
      cy.contains('No prompts found').should('be.visible')
    })

    it('should clear search', () => {
      cy.get('[data-testid="prompt-search"]').type('cost')
      cy.get('[data-testid="clear-search"]').click()
      cy.get('[data-testid="prompt-card"]').should('have.length.at.least', 5)
    })

    it('should highlight search matches', () => {
      cy.get('[data-testid="prompt-search"]').type('optimize')
      cy.get('.highlight').should('exist')
    })
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt to mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="example-prompts"]').should('be.visible')
    })

    it('should show mobile-optimized cards', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="prompt-card"]').should('have.css', 'width', '100%')
    })

    it('should handle mobile touch interactions', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="prompt-card"]').first().trigger('touchstart')
      cy.get('[data-testid="prompt-card"]').first().trigger('touchend')
      cy.get('textarea[data-testid="message-input"]').should('have.value')
    })

    it('should show scrollable prompt list on mobile', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="prompts-container"]')
        .should('have.css', 'overflow-x', 'auto')
    })

    it('should collapse by default on mobile', () => {
      cy.viewport('iphone-x')
      cy.reload()
      cy.get('[data-testid="prompt-card"]').should('not.be.visible')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      cy.get('[aria-label="Example prompts"]').should('exist')
      cy.get('[aria-label="Select prompt"]').should('have.length.at.least', 5)
    })

    it('should support keyboard navigation', () => {
      cy.get('[data-testid="prompt-card"]').first().focus()
      cy.focused().type('{enter}')
      cy.get('textarea[data-testid="message-input"]').should('have.value')
    })

    it('should have proper focus indicators', () => {
      cy.get('[data-testid="prompt-card"]').first().focus()
      cy.focused().should('have.css', 'outline')
        .and('not.equal', 'none')
    })

    it('should announce selections to screen readers', () => {
      cy.get('[role="status"]').should('exist')
      cy.get('[data-testid="prompt-card"]').first().click()
      cy.get('[role="status"]').should('contain', 'Selected')
    })

    it('should have descriptive button labels', () => {
      cy.get('button[aria-label]').should('have.length.at.least', 5)
    })
  })

  describe('Performance', () => {
    it('should render quickly', () => {
      const start = Date.now()
      cy.reload()
      cy.get('[data-testid="example-prompts"]').should('be.visible')
      const duration = Date.now() - start
      expect(duration).to.be.lessThan(2000)
    })

    it('should handle many prompts efficiently', () => {
      cy.window().then(win => {
        for(let i = 0; i < 50; i++) {
          win.addPrompt({ title: `Test ${i}`, text: `Prompt ${i}` })
        }
      })
      cy.get('[data-testid="prompt-card"]').should('have.length.at.least', 50)
    })

    it('should lazy load prompt icons', () => {
      cy.get('[data-testid="prompt-icon"]').first()
        .should('have.attr', 'loading', 'lazy')
    })

    it('should debounce search input', () => {
      let apiCalls = 0
      cy.intercept('GET', '/api/prompts/search*', () => {
        apiCalls++
      })
      cy.get('[data-testid="prompt-search"]').type('optimize')
      cy.wait(500)
      expect(apiCalls).to.be.lessThan(3)
    })
  })

  describe('Error Handling', () => {
    it('should handle missing prompts gracefully', () => {
      cy.intercept('GET', '/api/prompts', { body: [] })
      cy.reload()
      cy.contains('No prompts available').should('be.visible')
    })

    it('should show error message on API failure', () => {
      cy.intercept('GET', '/api/prompts', { statusCode: 500 })
      cy.reload()
      cy.contains('Unable to load prompts').should('be.visible')
    })

    it('should provide retry option', () => {
      cy.intercept('GET', '/api/prompts', { statusCode: 500 })
      cy.reload()
      cy.contains('Retry').should('be.visible')
    })

    it('should fallback to default prompts', () => {
      cy.intercept('GET', '/api/prompts', { statusCode: 500 })
      cy.reload()
      cy.wait(2000)
      cy.get('[data-testid="prompt-card"]').should('have.length.at.least', 3)
    })
  })
})