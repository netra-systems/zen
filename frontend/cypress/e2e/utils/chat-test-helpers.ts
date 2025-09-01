/// <reference types="cypress" />

/**
 * Shared Chat Test Utilities
 * Modular helper functions for chat component testing
 * Supports demo experience quality for Free segment conversion
 */

// Navigation and Setup Helpers
export const ChatNavigation = {
  visitDemo(): void {
    cy.viewport(1920, 1080)
    cy.visit('/demo')
  },

  selectIndustry(industry: string): void {
    // Wait for the page to load and industry options to be available
    cy.contains(industry, { timeout: 10000 }).should('be.visible')
    cy.contains(industry).click()
    cy.wait(2000) // Wait for the industry selection to process and tabs to appear
    // Navigate to the AI Chat tab where DemoChat is rendered
    cy.contains('AI Chat').click()
    cy.wait(1000) // Wait for tab content to load
  },

  setupTechnology(): void {
    this.visitDemo()
    this.selectIndustry('Technology')
  }
}

// Message Input Helpers
export const MessageInput = {
  type(message: string): void {
    cy.get('[data-testid="message-textarea"]').type(message)
  },

  send(message: string): void {
    cy.get('[data-testid="message-textarea"]').type(message)
    cy.get('[data-testid="send-button"]').click()
  },

  sendAndWait(message: string, waitTime: number = 3000): void {
    this.send(message)
    cy.wait(waitTime)
  },

  clear(): void {
    cy.get('[data-testid="message-textarea"]').clear()
  },

  assertEmpty(): void {
    cy.get('[data-testid="message-textarea"]').should('have.value', '')
  }
}

// Template System Helpers
export const Templates = {
  getTechnologyTemplates(): string[] {
    return [
      'Code Generation Pipeline',
      'CI/CD Optimization',
      'User Analytics AI'
    ]
  },

  selectTemplate(templateName: string): void {
    cy.contains(templateName).click()
  },

  hoverTemplate(templateName: string): void {
    cy.contains(templateName).trigger('mouseenter')
  },

  assertTemplateVisible(templateName: string): void {
    cy.contains(templateName).should('be.visible')
  }
}

// Message Assertion Helpers
export const MessageAssertions = {
  assertUserMessage(content: string): void {
    cy.contains(content).should('be.visible')
    cy.get('.justify-end').should('exist')
  },

  assertAssistantMessage(): void {
    cy.get('.justify-start').should('exist')
  },

  assertFormattedResponse(): void {
    cy.get('[class*="Card"]').should('exist')
  },

  assertTimestamp(): void {
    // Timestamps not currently implemented in the UI
    cy.log('Timestamp assertion skipped - not implemented in current UI')
  }
}

// Agent Processing Helpers
export const AgentProcessing = {
  assertProcessingIndicator(): void {
    cy.get('[data-testid="agent-processing"]').should('be.visible')
    cy.contains('Processing').should('be.visible')
  },

  assertAgentActivation(): void {
    cy.get('[data-testid="agent-indicator"]').should('have.length.at.least', 1)
  },

  assertAgentNames(): void {
    cy.contains(/Analyzer|Optimizer|Recommender/).should('be.visible')
  },

  assertProcessingTime(): void {
    cy.contains(/\d+ms/).should('be.visible')
  },

  assertTokenUsage(): void {
    cy.contains('tokens').should('be.visible')
  }
}

// Performance Metrics Helpers
export const MetricsValidation = {
  assertCostSavings(): void {
    cy.contains('Cost Savings').should('be.visible')
    cy.contains('$').should('be.visible')
  },

  assertPercentageGains(): void {
    cy.contains('%').should('be.visible')
  },

  assertLatencyMetrics(): void {
    cy.contains(/ms|latency/i).should('be.visible')
  },

  assertTimeline(): void {
    cy.contains(/week|day|phase/i).should('be.visible')
  },

  assertSavingsAmount(): void {
    cy.contains(/\$[\d,]+/).should('be.visible')
  }
}

// UI State Helpers
export const UIState = {
  assertSendButtonDisabled(): void {
    cy.get('[data-testid="send-button"]').should('be.disabled')
  },

  assertSendButtonEnabled(): void {
    cy.get('[data-testid="send-button"]').should('not.be.disabled')
  },

  assertInputDisabled(): void {
    cy.get('[data-testid="message-textarea"]').should('be.disabled')
  },

  assertInputEnabled(): void {
    cy.get('[data-testid="message-textarea"]').should('not.be.disabled')
  },

  assertTypingIndicator(): void {
    cy.get('[class*="animate-pulse"], [data-testid="agent-processing"]').should('exist')
  }
}

// Component Visibility Helpers
export const ComponentVisibility = {
  assertChatComponent(): void {
    cy.get('.grid').should('exist')
    cy.get('.lg\\:col-span-2').should('exist')
  },

  assertHeader(): void {
    cy.contains('AI Optimization Assistant').should('be.visible')
    cy.contains('Powered by multi-agent orchestration').should('be.visible')
  },

  assertIndustryBadge(industry: string): void {
    cy.contains(industry).should('be.visible')
  },

  assertAgentStatus(): void {
    cy.contains('Triage Agent').should('be.visible')
    cy.contains('Analysis Agent').should('be.visible')
    cy.contains('Optimization Agent').should('be.visible')
  },

  assertConnectionStatus(): void {
    cy.get('[class*="animate-pulse"]').should('exist')
  }
}

// Insight Panel Helpers
export const InsightsPanel = {
  assertVisible(): void {
    cy.get('[data-testid="insights-panel"]').should('be.visible')
  },

  assertReadinessScore(): void {
    cy.contains('Optimization Ready').should('be.visible')
    cy.get('[data-testid="readiness-score"]').should('contain', '%')
  },

  assertPotentialSavings(): void {
    cy.contains('Potential Savings').should('be.visible')
  },

  assertQuickActions(): void {
    cy.contains('Quick Actions').should('be.visible')
    cy.contains('Generate Report').should('be.visible')
    cy.contains('Schedule Call').should('be.visible')
  }
}

// Utility Functions
export const TestUtils = {
  generateLongMessage(length: number): string {
    return 'a'.repeat(length)
  },

  sendMultipleMessages(count: number): void {
    for(let i = 1; i <= count; i++) {
      MessageInput.send(`Message ${i}`)
      cy.wait(1000)
    }
  },

  setMobileViewport(): void {
    cy.viewport('iphone-x')
  },

  setTabletViewport(): void {
    cy.viewport('ipad-2')
  },

  setDesktopViewport(): void {
    cy.viewport(1920, 1080)
  }
}

// Common Wait Functions
export const WaitHelpers = {
  forProcessing(): void {
    cy.wait(3000)
  },

  forResponse(): void {
    cy.wait(2000)
  },

  brief(): void {
    cy.wait(500)
  },

  forConnection(): void {
    cy.wait(2000)
  }
}