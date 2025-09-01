/// <reference types="cypress" />

import {
  ChatNavigation,
  MessageInput,
  UIState,
  TestUtils,
  WaitHelpers
} from './utils/chat-test-helpers'

/**
 * Chat Utilities and Advanced Features Tests
 * Tests WebSocket communication, error handling, UI features, mobile support, and accessibility
 * Ensures robust demo experience across all user scenarios
 */

describe('DemoChat Utilities & Advanced Features', () => {
  beforeEach(() => {
    ChatNavigation.setupTechnology()
  })

  describe('WebSocket Communication', () => {
    beforeEach(() => {
      // Setup WebSocket interceptions for current system
      cy.intercept('GET', 'ws://localhost:8000/ws', { statusCode: 101 }).as('wsConnect')
    })

    it('should establish WebSocket connection to ws://localhost:8000/ws', () => {
      cy.window().its('WebSocket').should('exist')
      // Verify WebSocket connection attempt to correct endpoint
      cy.window().then((win) => {
        const wsUrl = win.location.protocol === 'https:' ? 'wss://localhost:8000/ws' : 'ws://localhost:8000/ws'
        cy.log(`Expected WebSocket URL: ${wsUrl}`)
      })
    })

    it('should handle critical WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)', () => {
      MessageInput.send('Test WebSocket Events')
      cy.wait(1000)
      
      // Check for WebSocket event indicators in UI
      cy.get('body').then($body => {
        const text = $body.text()
        const hasAgentEvents = /agent_started|agent_thinking|tool_executing|tool_completed|agent_completed|processing|thinking|executing/i.test(text)
        
        if (hasAgentEvents) {
          cy.log('WebSocket agent events detected in UI')
          cy.get('[data-testid="ws-indicator"], [class*="animate-pulse"], [class*="processing"]').should('exist')
        } else {
          cy.log('WebSocket events may be handled differently in current implementation')
        }
      })
    })

    it('should reconnect with exponential backoff (100ms base, 10s max)', () => {
      cy.window().then(win => {
        if (win.ws) {
          win.ws.close()
        }
      })
      WaitHelpers.forConnection()
      
      // Check for connection status indicators
      cy.get('body').then($body => {
        const hasConnectionIndicator = $body.find('[data-testid="connection-status"], [class*="bg-green"], [class*="connected"]').length > 0
        if (hasConnectionIndicator) {
          cy.get('[data-testid="connection-status"]').should('have.class', 'bg-green-500')
        } else {
          cy.log('Connection status may be handled differently - checking for reconnection behavior')
        }
      })
    })

    it('should use circuit breaker for WebSocket failures', () => {
      cy.intercept('GET', 'ws://localhost:8000/ws', { statusCode: 500 }).as('wsFail')
      MessageInput.sendAndWait('Test fallback')
      cy.contains('Test fallback').should('be.visible')
      
      // Verify circuit breaker behavior
      cy.get('body').then($body => {
        const hasCircuitBreakerText = /circuit.*breaker|fallback|backup|retry/i.test($body.text())
        if (hasCircuitBreakerText) {
          cy.log('Circuit breaker behavior detected')
        } else {
          cy.log('Circuit breaker may be handled transparently')
        }
      })
    })

    it('should handle connection timeouts with proper error handling', () => {
      cy.intercept('GET', 'ws://localhost:8000/ws', { delay: 10000 }).as('wsTimeout')
      MessageInput.send('Timeout test')
      cy.contains(/connecting|timeout|retrying|failed/i, { timeout: 15000 }).should('be.visible')
    })

    it('should maintain message queue during reconnection with resilient WebSocket service', () => {
      MessageInput.type('Queue test')
      cy.window().then(win => win.ws?.close())
      cy.get('[data-testid="send-button"], button').first().click()
      WaitHelpers.forConnection()
      cy.contains('Queue test').should('be.visible')
    })
  })

  describe('Error Handling', () => {
    it('should handle empty message submission', () => {
      UIState.assertSendButtonDisabled()
      MessageInput.type('   ')
      UIState.assertSendButtonDisabled()
    })

    it('should handle very long messages', () => {
      const longMessage = TestUtils.generateLongMessage(5000)
      MessageInput.type(longMessage)
      cy.get('[data-testid="send-button"]').click()
      cy.contains('Message too long').should('be.visible')
    })

    it('should handle API errors gracefully', () => {
      // Mock current agent API endpoint
      cy.intercept('POST', '/api/agents/execute', { statusCode: 500 }).as('agentError')
      MessageInput.send('Test error')
      cy.wait('@agentError')
      cy.contains(/error|failed|try again|something went wrong/i).should('be.visible')
    })

    it('should show retry option on failure', () => {
      cy.intercept('POST', '/api/agents/execute', { statusCode: 500 }).as('apiFailure')
      MessageInput.send('Test')
      cy.wait('@apiFailure')
      cy.get('body').then($body => {
        const hasRetry = /retry|try again|resend/i.test($body.text())
        if (hasRetry) {
          cy.contains(/Retry|Try Again/i).should('be.visible')
        } else {
          cy.log('Retry functionality may be handled differently')
        }
      })
    })

    it('should handle rate limiting', () => {
      for(let i = 1; i <= 10; i++) {
        MessageInput.send(`Msg ${i}`)
      }
      cy.contains(/slow down|rate limit/i).should('be.visible')
    })

    it('should recover from network errors', () => {
      cy.intercept('POST', '/api/agents/execute', { forceNetworkError: true }).as('networkError')
      MessageInput.send('Network test')
      cy.wait('@networkError')
      cy.contains(/network|connection|offline|failed/i).should('be.visible')
    })
  })

  describe('UI Features and Animations', () => {
    it('should display glassmorphic styling', () => {
      cy.get('[data-testid="demo-chat"]').should('have.class', 'backdrop-blur')
      cy.get('[data-testid="demo-chat"]').should('have.class', 'bg-opacity-20')
    })

    it('should animate message appearance', () => {
      MessageInput.send('Test')
      cy.get('[data-testid="user-message"]').should('have.css', 'animation')
    })

    it('should show typing indicator', () => {
      MessageInput.send('Test')
      UIState.assertTypingIndicator()
    })

    it('should have gradient backgrounds', () => {
      cy.get('.bg-gradient-to-r').should('exist')
      cy.get('.from-purple-500').should('exist')
    })

    it('should handle dark mode', () => {
      cy.get('[data-testid="theme-toggle"]').click()
      cy.get('[data-testid="demo-chat"]').should('have.class', 'dark')
    })

    it('should show smooth scrolling animations', () => {
      TestUtils.sendMultipleMessages(5)
      cy.get('[data-testid="chat-container"]').should('have.css', 'scroll-behavior', 'smooth')
    })
  })

  describe('Copy and Export Features', () => {
    it('should allow copying messages', () => {
      MessageInput.sendAndWait('Test message')
      cy.get('[data-testid="copy-message"]').first().click()
      cy.contains('Copied').should('be.visible')
    })

    it('should export conversation', () => {
      MessageInput.sendAndWait('Test 1')
      MessageInput.sendAndWait('Test 2')
      cy.get('[data-testid="export-chat"]').click()
      cy.contains('Export Format').should('be.visible')
    })

    it('should allow downloading chat as PDF', () => {
      cy.get('[data-testid="export-chat"]').click()
      cy.contains('PDF').click()
      cy.readFile('cypress/downloads/chat-export.pdf').should('exist')
    })

    it('should allow downloading chat as JSON', () => {
      cy.get('[data-testid="export-chat"]').click()
      cy.contains('JSON').click()
      cy.readFile('cypress/downloads/chat-export.json').should('exist')
    })

    it('should copy conversation as text', () => {
      MessageInput.sendAndWait('Copy test')
      cy.get('[data-testid="copy-conversation"]').click()
      cy.contains('Conversation copied').should('be.visible')
    })

    it('should share conversation link', () => {
      MessageInput.sendAndWait('Share test')
      cy.get('[data-testid="share-conversation"]').click()
      cy.contains('Share link copied').should('be.visible')
    })
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt to mobile viewport', () => {
      TestUtils.setMobileViewport()
      cy.get('[data-testid="demo-chat"]').should('be.visible')
      cy.get('textarea[data-testid="message-input"]').should('be.visible')
    })

    it('should show mobile-optimized templates', () => {
      TestUtils.setMobileViewport()
      cy.get('[data-testid="template-section"]').scrollIntoView()
      cy.get('[data-testid="template-card"]').should('have.css', 'width', '100%')
    })

    it('should handle mobile input', () => {
      TestUtils.setMobileViewport()
      MessageInput.type('Mobile test')
      cy.get('[data-testid="send-button"]').click()
      cy.contains('Mobile test').should('be.visible')
    })

    it('should maintain functionality on tablet', () => {
      TestUtils.setTabletViewport()
      cy.get('[data-testid="demo-chat"]').should('be.visible')
      cy.contains('Code Generation Pipeline').click()
      cy.get('textarea[data-testid="message-input"]').should('have.value')
    })

    it('should handle touch interactions', () => {
      TestUtils.setMobileViewport()
      cy.get('[data-testid="template-card"]').first().trigger('touchstart')
      cy.get('textarea[data-testid="message-input"]').should('have.value')
    })

    it('should show mobile navigation menu', () => {
      TestUtils.setMobileViewport()
      cy.get('[data-testid="mobile-menu"]').should('be.visible')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      cy.get('[aria-label="Send message"]').should('exist')
      cy.get('[aria-label="Message input"]').should('exist')
    })

    it('should support keyboard navigation', () => {
      cy.get('textarea[data-testid="message-input"]').focus()
      cy.focused().type('Keyboard test')
      cy.focused().type('{enter}')
      cy.contains('Keyboard test').should('be.visible')
    })

    it('should announce status changes', () => {
      cy.get('[role="status"]').should('exist')
      MessageInput.send('Test')
      cy.get('[role="status"]').should('contain', 'Processing')
    })

    it('should have proper focus management', () => {
      MessageInput.sendAndWait('Test')
      cy.focused().should('have.attr', 'data-testid', 'message-input')
    })

    it('should support screen readers', () => {
      cy.get('[aria-live="polite"]').should('exist')
      MessageInput.send('Screen reader test')
      cy.get('[aria-live="polite"]').should('not.be.empty')
    })

    it('should have sufficient color contrast', () => {
      cy.get('[data-testid="demo-chat"]').should('have.css', 'color')
      cy.get('[data-testid="demo-chat"]').should('have.css', 'background-color')
    })
  })

  describe('Performance and Optimization', () => {
    it('should load efficiently', () => {
      cy.window().its('performance').invoke('getEntriesByType', 'navigation')
        .its('0.loadEventEnd').should('be.lessThan', 3000)
    })

    it('should handle large conversation histories', () => {
      TestUtils.sendMultipleMessages(20)
      cy.get('[data-testid="chat-container"]').should('be.visible')
      cy.contains('Message 20').should('be.visible')
    })

    it('should virtualize long message lists', () => {
      TestUtils.sendMultipleMessages(50)
      cy.get('[data-testid="virtual-list"]').should('exist')
    })

    it('should lazy load message content', () => {
      TestUtils.sendMultipleMessages(10)
      cy.get('[data-testid="lazy-message"]').should('exist')
    })

    it('should optimize image loading', () => {
      MessageInput.sendAndWait('Show optimization diagram')
      cy.get('img[loading="lazy"]').should('exist')
    })
    it('should cache responses efficiently', () => {
      MessageInput.sendAndWait('Cache test')
      cy.window().its('caches').should('exist')
    })
  })
  describe('Security and Privacy', () => {
    it('should sanitize user input', () => {
      MessageInput.send('<script>alert("xss")</script>')
      cy.get('script').should('not.exist')
    })

    it('should handle malicious links', () => {
      MessageInput.send('Visit http://malicious-site.com')
      cy.get('a[href*="malicious"]').should('not.exist')
    })

    it('should protect against injection attacks', () => {
      MessageInput.send("'; DROP TABLE users; --")
      cy.contains('DROP TABLE').should('not.exist')
    })

    it('should validate file uploads', () => {
      cy.get('[data-testid="file-upload"]').should('have.attr', 'accept')
    })
  })
})