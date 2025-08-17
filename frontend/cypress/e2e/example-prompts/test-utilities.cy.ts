/// <reference types="cypress" />

/**
 * Example Prompts Test Utilities & Factories
 * BVJ: Free/Early segment - improves onboarding, drives conversion to paid
 */

export class PromptTestUtilities {
  static setupViewport(): void {
    cy.viewport(1920, 1080)
    cy.visit('/')
    cy.wait(500)
  }

  static getMobileViewport(): void {
    cy.viewport('iphone-x')
  }

  static getPromptCards(): Cypress.Chainable {
    return cy.get('[data-testid="prompt-card"]')
  }

  static getExamplePrompts(): Cypress.Chainable {
    return cy.get('[data-testid="example-prompts"]')
  }

  static getMessageInput(): Cypress.Chainable {
    return cy.get('textarea[data-testid="message-input"]')
  }

  static getToggleButton(): Cypress.Chainable {
    return cy.get('[data-testid="toggle-prompts"]')
  }

  static getSearchInput(): Cypress.Chainable {
    return cy.get('[data-testid="prompt-search"]')
  }

  static getCopyButtons(): Cypress.Chainable {
    return cy.get('[data-testid="copy-prompt"]')
  }
}

export class PromptTestFactories {
  static createPromptTest(title: string): any {
    return {
      title,
      text: `Test prompt for ${title}`,
      category: 'optimization'
    }
  }

  static createMultiplePrompts(count: number): any[] {
    return Array.from({ length: count }, (_, i) => 
      this.createPromptTest(`Test ${i}`)
    )
  }

  static setupApiMock(response: any): void {
    cy.intercept('GET', '/api/prompts', { body: response })
  }

  static setupApiError(statusCode: number): void {
    cy.intercept('GET', '/api/prompts', { statusCode })
  }

  static expectVisibleElements(count: number): void {
    PromptTestUtilities.getPromptCards()
      .should('have.length.at.least', count)
  }

  static expectTextContent(text: string): void {
    cy.contains(text).should('be.visible')
  }

  static expectInputValue(hasValue: boolean = true): void {
    const assertion = hasValue ? 'have.value' : 'not.have.value'
    PromptTestUtilities.getMessageInput().should(assertion)
  }
}

export class PromptTestValidators {
  static validateStyling(selector: string): void {
    cy.get(selector).should('have.css', 'transform')
      .and('not.equal', 'none')
  }

  static validateAnimation(selector: string): void {
    cy.get(selector).should('have.css', 'animation')
  }

  static validateAccessibility(element: string): void {
    cy.get(element).should('have.attr', 'aria-label')
  }

  static validateKeyboardNav(): void {
    PromptTestUtilities.getPromptCards().first().focus()
    cy.focused().type('{enter}')
    PromptTestFactories.expectInputValue()
  }
}