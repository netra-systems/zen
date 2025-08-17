/// <reference types="cypress" />
import { PromptTestUtilities, PromptTestFactories, PromptTestValidators } from './test-utilities.cy'

/**
 * Example Prompts Advanced Features Tests
 * BVJ: Free/Early segment - validates advanced features that drive user engagement
 */

describe('ExamplePrompts Advanced Features', () => {
  beforeEach(() => {
    PromptTestUtilities.setupViewport()
  })

  describe('Search and Discovery', () => {
    it('should display search input', () => {
      PromptTestUtilities.getSearchInput().should('be.visible')
    })

    it('should filter prompts by search', () => {
      PromptTestUtilities.getSearchInput().type('cost')
      PromptTestFactories.expectVisibleElements(1)
      PromptTestFactories.expectTextContent('Reduce AI Costs')
    })

    it('should show no results message', () => {
      PromptTestUtilities.getSearchInput().type('xyz123')
      PromptTestFactories.expectTextContent('No prompts found')
    })

    it('should clear search', () => {
      PromptTestUtilities.getSearchInput().type('cost')
      cy.get('[data-testid="clear-search"]').click()
      PromptTestFactories.expectVisibleElements(5)
    })

    it('should highlight search matches', () => {
      PromptTestUtilities.getSearchInput().type('optimize')
      cy.get('.highlight').should('exist')
    })

    it('should debounce search input', () => {
      let apiCalls = 0
      cy.intercept('GET', '/api/prompts/search*', () => {
        apiCalls++
      })
      PromptTestUtilities.getSearchInput().type('optimize')
      cy.wait(500)
      expect(apiCalls).to.be.lessThan(3)
    })

    it('should search by category keywords', () => {
      PromptTestUtilities.getSearchInput().type('analysis')
      PromptTestFactories.expectTextContent('Performance Audit')
    })

    it('should handle special characters in search', () => {
      PromptTestUtilities.getSearchInput().type('AI & ML')
      PromptTestFactories.expectVisibleElements(1)
    })
  })

  describe('Smart Filtering', () => {
    it('should combine search and category filters', () => {
      cy.get('[data-testid="category-filter"]').click()
      cy.contains('Optimization').click()
      PromptTestUtilities.getSearchInput().type('cost')
      PromptTestFactories.expectVisibleElements(1)
    })

    it('should filter by difficulty level', () => {
      cy.get('[data-testid="difficulty-filter"]').click()
      cy.contains('Beginner').click()
      PromptTestFactories.expectVisibleElements(2)
    })

    it('should filter by industry', () => {
      cy.get('[data-testid="industry-filter"]').click()
      cy.contains('Healthcare').click()
      PromptTestFactories.expectTextContent('Patient')
    })

    it('should apply multiple filters simultaneously', () => {
      cy.get('[data-testid="category-filter"]').click()
      cy.contains('Optimization').click()
      cy.get('[data-testid="difficulty-filter"]').click()
      cy.contains('Advanced').click()
      PromptTestFactories.expectVisibleElements(1)
    })

    it('should reset all filters', () => {
      PromptTestUtilities.getSearchInput().type('cost')
      cy.get('[data-testid="reset-filters"]').click()
      PromptTestFactories.expectVisibleElements(5)
    })
  })

  describe('Personalization Features', () => {
    it('should show recently used prompts', () => {
      PromptTestUtilities.getPromptCards().first().click()
      cy.reload()
      cy.get('[data-testid="recent-prompts"]').should('exist')
    })

    it('should save favorite prompts', () => {
      cy.get('[data-testid="favorite-button"]').first().click()
      cy.get('[data-testid="favorites-section"]').should('be.visible')
    })

    it('should recommend similar prompts', () => {
      PromptTestUtilities.getPromptCards().first().click()
      cy.get('[data-testid="similar-prompts"]').should('exist')
    })

    it('should track prompt usage analytics', () => {
      cy.window().then(win => {
        cy.spy(win, 'analytics').as('analytics')
      })
      PromptTestUtilities.getPromptCards().first().click()
      cy.get('@analytics').should('have.been.called')
    })

    it('should adapt to user preferences', () => {
      cy.window().then(win => {
        win.setUserPreference('industry', 'fintech')
      })
      PromptTestFactories.expectTextContent('Financial')
    })
  })

  describe('Content Management', () => {
    it('should load prompts dynamically', () => {
      cy.intercept('GET', '/api/prompts', { 
        body: PromptTestFactories.createMultiplePrompts(10)
      })
      cy.reload()
      PromptTestFactories.expectVisibleElements(10)
    })

    it('should lazy load additional prompts', () => {
      cy.scrollTo('bottom')
      cy.wait(1000)
      PromptTestFactories.expectVisibleElements(8)
    })

    it('should cache prompts locally', () => {
      cy.window().then(win => {
        expect(win.localStorage.getItem('cached_prompts')).to.exist
      })
    })

    it('should refresh stale content', () => {
      cy.clock()
      cy.tick(600000) // 10 minutes
      PromptTestFactories.expectTextContent('Refreshing')
    })

    it('should validate prompt structure', () => {
      const invalidPrompt = { title: '', text: null }
      cy.window().then(win => {
        expect(() => win.validatePrompt(invalidPrompt)).to.throw()
      })
    })
  })

  describe('Integration Features', () => {
    it('should integrate with chat history', () => {
      PromptTestUtilities.getPromptCards().first().click()
      cy.get('[data-testid="chat-history"]').should('contain', 'cost')
    })

    it('should sync with user workspace', () => {
      cy.window().then(win => {
        win.setWorkspace({ name: 'Test Workspace' })
      })
      PromptTestFactories.expectTextContent('Test Workspace')
    })

    it('should export selected prompts', () => {
      PromptTestUtilities.getPromptCards().first().click()
      cy.get('[data-testid="export-prompt"]').click()
      cy.get('[data-testid="export-modal"]').should('be.visible')
    })

    it('should import custom prompts', () => {
      cy.get('[data-testid="import-prompt"]').click()
      cy.get('input[type="file"]').attachFile('custom-prompts.json')
      PromptTestFactories.expectVisibleElements(7)
    })

    it('should share prompts via URL', () => {
      PromptTestUtilities.getPromptCards().first().click()
      cy.get('[data-testid="share-prompt"]').click()
      cy.get('[data-testid="share-url"]').should('contain', 'prompt=')
    })
  })

  describe('Advanced UI Features', () => {
    it('should support bulk operations', () => {
      cy.get('[data-testid="select-all"]').click()
      PromptTestUtilities.getPromptCards()
        .should('have.class', 'selected')
    })

    it('should show prompt preview modal', () => {
      cy.get('[data-testid="preview-button"]').first().click()
      cy.get('[data-testid="prompt-preview"]').should('be.visible')
    })

    it('should allow inline editing', () => {
      cy.get('[data-testid="edit-button"]').first().click()
      cy.get('[data-testid="inline-editor"]').should('be.visible')
    })

    it('should validate edited content', () => {
      cy.get('[data-testid="edit-button"]').first().click()
      cy.get('[data-testid="prompt-title"]').clear().type('New Title')
      cy.get('[data-testid="save-edit"]').click()
      PromptTestFactories.expectTextContent('New Title')
    })

    it('should support drag and drop reordering', () => {
      PromptTestUtilities.getPromptCards().first()
        .trigger('dragstart')
      PromptTestUtilities.getPromptCards().last()
        .trigger('drop')
      cy.get('[data-testid="order-updated"]').should('exist')
    })
  })
})