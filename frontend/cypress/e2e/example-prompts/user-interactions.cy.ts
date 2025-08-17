/// <reference types="cypress" />
import { PromptTestUtilities, PromptTestFactories, PromptTestValidators } from './test-utilities.cy'

/**
 * Example Prompts User Interaction Tests
 * BVJ: Free/Early segment - validates user interaction flow for conversion optimization
 */

describe('ExamplePrompts User Interactions', () => {
  beforeEach(() => {
    PromptTestUtilities.setupViewport()
  })

  describe('Interaction and Animation', () => {
    it('should expand prompt on click', () => {
      PromptTestUtilities.getPromptCards().first().click()
      PromptTestUtilities.getPromptCards().first()
        .should('have.class', 'scale-105')
    })

    it('should show hover effects', () => {
      PromptTestUtilities.getPromptCards().first().trigger('mouseenter')
      PromptTestValidators.validateStyling('[data-testid="prompt-card"]')
    })

    it('should animate card appearance', () => {
      PromptTestValidators.validateAnimation('[data-testid="prompt-card"]')
    })

    it('should show gradient animation', () => {
      cy.get('.animate-gradient').should('exist')
    })

    it('should display pulse animation on new prompts', () => {
      cy.get('.animate-pulse').should('exist')
    })

    it('should handle rapid clicking', () => {
      const card = PromptTestUtilities.getPromptCards().first()
      for(let i = 0; i < 5; i++) {
        card.click()
      }
      PromptTestUtilities.getPromptCards().first()
        .should('not.have.class', 'error')
    })
  })

  describe('Prompt Selection', () => {
    it('should populate message input on selection', () => {
      PromptTestUtilities.getPromptCards().first().click()
      PromptTestFactories.expectInputValue()
    })

    it('should copy exact prompt text', () => {
      cy.contains('Reduce AI Costs').click()
      PromptTestUtilities.getMessageInput()
        .should('have.value')
        .and('include', 'cost reduction')
    })

    it('should highlight selected prompt', () => {
      PromptTestUtilities.getPromptCards().first().click()
      PromptTestUtilities.getPromptCards().first()
        .should('have.class', 'ring-2')
    })

    it('should allow selecting different prompts', () => {
      PromptTestUtilities.getPromptCards().first().click()
      PromptTestUtilities.getPromptCards().last().click()
      PromptTestUtilities.getPromptCards().last()
        .should('have.class', 'ring-2')
      PromptTestUtilities.getPromptCards().first()
        .should('not.have.class', 'ring-2')
    })

    it('should trigger callback on selection', () => {
      cy.window().then(win => {
        cy.spy(win.console, 'log').as('consoleLog')
      })
      PromptTestUtilities.getPromptCards().first().click()
      cy.get('@consoleLog').should('have.been.called')
    })
  })

  describe('Collapsible Behavior', () => {
    it('should have collapse/expand button', () => {
      PromptTestUtilities.getToggleButton().should('be.visible')
    })

    it('should collapse prompt section', () => {
      PromptTestUtilities.getToggleButton().click()
      PromptTestUtilities.getPromptCards().should('not.be.visible')
    })

    it('should expand prompt section', () => {
      PromptTestUtilities.getToggleButton().click()
      PromptTestUtilities.getToggleButton().click()
      PromptTestUtilities.getPromptCards().should('be.visible')
    })

    it('should animate collapse/expand', () => {
      cy.get('[data-testid="prompts-container"]')
        .should('have.css', 'transition')
    })

    it('should remember collapsed state', () => {
      PromptTestUtilities.getToggleButton().click()
      cy.reload()
      PromptTestUtilities.getPromptCards().should('not.be.visible')
    })

    it('should show chevron icon animation', () => {
      cy.get('[data-testid="chevron-icon"]')
        .should('have.css', 'transform')
      PromptTestUtilities.getToggleButton().click()
      cy.get('[data-testid="chevron-icon"]')
        .should('have.css', 'transform')
        .and('include', 'rotate')
    })
  })

  describe('Copy to Clipboard', () => {
    it('should have copy button on each prompt', () => {
      PromptTestUtilities.getCopyButtons()
        .should('have.length.at.least', 5)
    })

    it('should copy prompt to clipboard', () => {
      PromptTestUtilities.getCopyButtons().first().click()
      PromptTestFactories.expectTextContent('Copied!')
    })

    it('should show copy success animation', () => {
      PromptTestUtilities.getCopyButtons().first().click()
      cy.get('[data-testid="copy-success"]')
        .should('have.class', 'animate-bounce')
    })

    it('should reset copy indicator', () => {
      PromptTestUtilities.getCopyButtons().first().click()
      PromptTestFactories.expectTextContent('Copied!')
      cy.wait(2000)
      cy.contains('Copied!').should('not.exist')
    })
  })

  describe('Mobile Touch Interactions', () => {
    beforeEach(() => {
      PromptTestUtilities.getMobileViewport()
    })

    it('should handle mobile touch interactions', () => {
      PromptTestUtilities.getPromptCards().first().trigger('touchstart')
      PromptTestUtilities.getPromptCards().first().trigger('touchend')
      PromptTestFactories.expectInputValue()
    })

    it('should show scrollable prompt list on mobile', () => {
      cy.get('[data-testid="prompts-container"]')
        .should('have.css', 'overflow-x', 'auto')
    })

    it('should collapse by default on mobile', () => {
      cy.reload()
      PromptTestUtilities.getPromptCards().should('not.be.visible')
    })

    it('should adapt to mobile viewport', () => {
      PromptTestUtilities.getExamplePrompts().should('be.visible')
    })

    it('should show mobile-optimized cards', () => {
      PromptTestUtilities.getPromptCards()
        .should('have.css', 'width', '100%')
    })
  })

  describe('Keyboard Interactions', () => {
    it('should support keyboard navigation', () => {
      PromptTestValidators.validateKeyboardNav()
    })

    it('should have proper focus indicators', () => {
      PromptTestUtilities.getPromptCards().first().focus()
      cy.focused().should('have.css', 'outline')
        .and('not.equal', 'none')
    })

    it('should allow tab navigation', () => {
      PromptTestUtilities.getPromptCards().first().focus()
      cy.focused().tab()
      cy.focused().should('have.attr', 'data-testid')
    })

    it('should handle escape key', () => {
      PromptTestUtilities.getPromptCards().first().click()
      cy.get('body').type('{esc}')
      PromptTestUtilities.getPromptCards().first()
        .should('not.have.class', 'ring-2')
    })

    it('should support arrow key navigation', () => {
      PromptTestUtilities.getPromptCards().first().focus()
      cy.focused().type('{downarrow}')
      cy.focused().should('not.be', PromptTestUtilities.getPromptCards().first())
    })
  })
})