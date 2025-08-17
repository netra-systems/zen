/// <reference types="cypress" />
import { PromptTestUtilities, PromptTestFactories, PromptTestValidators } from './test-utilities.cy'

/**
 * Example Prompts Component Foundation Tests
 * BVJ: Free/Early segment - validates core component rendering for user onboarding
 */

describe('ExamplePrompts Component Foundation', () => {
  beforeEach(() => {
    PromptTestUtilities.setupViewport()
  })

  describe('Component Initialization', () => {
    it('should render ExamplePrompts component', () => {
      PromptTestUtilities.getExamplePrompts().should('be.visible')
    })

    it('should display section heading', () => {
      PromptTestFactories.expectTextContent('Quick Start')
      PromptTestFactories.expectTextContent('Select an optimization scenario')
    })

    it('should show all example prompt cards', () => {
      PromptTestFactories.expectVisibleElements(5)
    })

    it('should have glassmorphic styling', () => {
      PromptTestUtilities.getPromptCards()
        .first().should('have.class', 'backdrop-blur')
      cy.get('.bg-gradient-to-br').should('exist')
    })

    it('should display icons for each prompt', () => {
      cy.get('[data-testid="prompt-icon"]')
        .should('have.length.at.least', 5)
    })
  })

  describe('Prompt Content Validation', () => {
    it('should display cost optimization prompt', () => {
      PromptTestFactories.expectTextContent('Reduce AI Costs')
      PromptTestFactories.expectTextContent('Analyze and optimize')
    })

    it('should display latency optimization prompt', () => {
      PromptTestFactories.expectTextContent('Improve Latency')
      PromptTestFactories.expectTextContent('response times')
    })

    it('should display model selection prompt', () => {
      PromptTestFactories.expectTextContent('Model Selection')
      PromptTestFactories.expectTextContent('best model')
    })

    it('should display capacity planning prompt', () => {
      PromptTestFactories.expectTextContent('Capacity Planning')
      PromptTestFactories.expectTextContent('scale')
    })

    it('should display performance audit prompt', () => {
      PromptTestFactories.expectTextContent('Performance Audit')
      PromptTestFactories.expectTextContent('comprehensive analysis')
    })

    it('should show prompt descriptions', () => {
      cy.get('[data-testid="prompt-description"]')
        .should('have.length.at.least', 5)
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
      PromptTestUtilities.getPromptCards().first()
        .should('have.css', 'border-radius')
        .and('not.equal', '0px')
    })

    it('should display shadows', () => {
      PromptTestUtilities.getPromptCards().first()
        .should('have.css', 'box-shadow')
        .and('not.equal', 'none')
    })

    it('should show border effects', () => {
      PromptTestUtilities.getPromptCards().first()
        .should('have.css', 'border')
    })
  })

  describe('Categories and Organization', () => {
    it('should display prompt categories', () => {
      PromptTestFactories.expectTextContent('Optimization')
      PromptTestFactories.expectTextContent('Analysis')
      PromptTestFactories.expectTextContent('Planning')
    })

    it('should group prompts by category', () => {
      cy.get('[data-testid="category-optimization"]').should('exist')
      cy.get('[data-testid="category-analysis"]').should('exist')
    })

    it('should show category badges', () => {
      cy.get('[data-testid="category-badge"]')
        .should('have.length.at.least', 3)
    })

    it('should filter prompts by category', () => {
      cy.get('[data-testid="category-filter"]').click()
      cy.contains('Optimization').click()
      PromptTestFactories.expectVisibleElements(2)
    })

    it('should highlight active category', () => {
      cy.get('[data-testid="category-filter"]').click()
      cy.contains('Analysis').click()
      cy.get('[data-testid="category-analysis"]')
        .should('have.class', 'bg-primary')
    })
  })

  describe('Dynamic Content Updates', () => {
    it('should update based on context', () => {
      cy.window().then(win => {
        win.updateContext({ industry: 'Healthcare' })
      })
      PromptTestFactories.expectTextContent('Patient')
    })

    it('should show industry-specific prompts', () => {
      cy.visit('/demo')
      cy.contains('Financial Services').click()
      PromptTestUtilities.getExamplePrompts()
        .should('contain', 'Risk')
    })

    it('should refresh prompts periodically', () => {
      PromptTestUtilities.getPromptCards().then($initial => {
        const initialCount = $initial.length
        cy.wait(10000)
        PromptTestUtilities.getPromptCards()
          .should('have.length', initialCount)
      })
    })

    it('should show trending prompts', () => {
      cy.get('[data-testid="trending-badge"]').should('exist')
      PromptTestFactories.expectTextContent('Trending')
    })

    it('should display new prompt indicator', () => {
      cy.get('[data-testid="new-badge"]').should('exist')
      PromptTestFactories.expectTextContent('New')
    })
  })

  describe('Prompt Templates', () => {
    it('should support template variables', () => {
      PromptTestUtilities.getPromptCards().first().click()
      PromptTestUtilities.getMessageInput().should('contain', '{')
    })

    it('should highlight template placeholders', () => {
      PromptTestUtilities.getPromptCards()
        .contains('{{workload}}').should('be.visible')
    })

    it('should allow editing template values', () => {
      PromptTestUtilities.getPromptCards().first().click()
      cy.get('[data-testid="template-editor"]').should('be.visible')
      cy.get('input[name="workload"]').type('ML inference')
    })

    it('should preview filled template', () => {
      PromptTestUtilities.getPromptCards().first().click()
      cy.get('input[name="workload"]').type('ML inference')
      cy.get('[data-testid="preview"]').should('contain', 'ML inference')
    })

    it('should validate template inputs', () => {
      PromptTestUtilities.getPromptCards().first().click()
      cy.get('input[name="requests"]').type('abc')
      PromptTestFactories.expectTextContent('Must be a number')
    })
  })
})