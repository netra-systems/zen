/// <reference types="cypress" />

import {
  ChatNavigation,
  MessageInput,
  Templates,
  MessageAssertions,
  ComponentVisibility,
  UIState,
  TestUtils,
  WaitHelpers
} from './utils/chat-test-helpers'

/**
 * Core Chat Functionality Tests
 * Tests fundamental chat operations for demo experience
 * Critical for Free segment conversion to paid tiers
 */

describe('DemoChat Core Functionality', () => {
  beforeEach(() => {
    ChatNavigation.setupTechnology()
  })

  describe('Component Initialization', () => {
    it('should render DemoChat component', () => {
      ComponentVisibility.assertChatComponent()
    })

    it('should display chat header with title', () => {
      ComponentVisibility.assertHeader()
    })

    it('should show industry context badge', () => {
      ComponentVisibility.assertIndustryBadge('Technology')
    })

    it('should display agent status indicators', () => {
      ComponentVisibility.assertAgentStatus()
    })

    it('should show WebSocket connection status', () => {
      ComponentVisibility.assertConnectionStatus()
    })
  })

  describe('Template System', () => {
    it('should display industry-specific templates', () => {
      cy.get('[data-testid="template-section"]').should('be.visible')
      cy.contains('Quick Start Templates').should('be.visible')
    })

    it('should show Technology industry templates', () => {
      const templates = Templates.getTechnologyTemplates()
      templates.forEach(template => {
        Templates.assertTemplateVisible(template)
      })
    })

    it('should categorize templates', () => {
      cy.contains('Development').should('be.visible')
      cy.contains('DevOps').should('be.visible')
      cy.contains('Analytics').should('be.visible')
    })

    it('should populate message on template click', () => {
      Templates.selectTemplate('Code Generation Pipeline')
      cy.get('textarea[data-testid="message-input"]')
        .should('have.value')
        .and('include', 'code completion')
    })

    it('should show template description on hover', () => {
      Templates.hoverTemplate('CI/CD Optimization')
      cy.contains('Optimize your continuous integration').should('be.visible')
    })

    it('should handle template switching', () => {
      Templates.selectTemplate('Code Generation Pipeline')
      Templates.selectTemplate('API Performance Tuning')
      cy.get('textarea[data-testid="message-input"]')
        .should('have.value')
        .and('include', 'API')
    })
  })

  describe('Message Input and Sending', () => {
    it('should have message input textarea', () => {
      cy.get('textarea[data-testid="message-input"]').should('be.visible')
      cy.get('textarea[data-testid="message-input"]').should('have.attr', 'placeholder')
    })

    it('should enable send button with text', () => {
      UIState.assertSendButtonDisabled()
      MessageInput.type('Test message')
      UIState.assertSendButtonEnabled()
    })

    it('should send message on button click', () => {
      MessageInput.type('Optimize my workload')
      cy.get('[data-testid="send-button"]').click()
      MessageAssertions.assertUserMessage('Optimize my workload')
    })

    it('should send message on Enter key', () => {
      MessageInput.send('Test message')
      MessageAssertions.assertUserMessage('Test message')
    })

    it('should support multi-line with Shift+Enter', () => {
      cy.get('textarea[data-testid="message-input"]')
        .type('Line 1{shift+enter}Line 2')
      cy.get('textarea[data-testid="message-input"]')
        .should('have.value', 'Line 1\nLine 2')
    })

    it('should clear input after sending', () => {
      MessageInput.send('Test')
      MessageInput.assertEmpty()
    })

    it('should disable input while processing', () => {
      MessageInput.send('Test')
      UIState.assertInputDisabled()
      WaitHelpers.forResponse()
      UIState.assertInputEnabled()
    })
  })

  describe('Chat History Management', () => {
    it('should maintain conversation context', () => {
      MessageInput.sendAndWait('My system processes 1M requests')
      MessageInput.sendAndWait('How much can I save?')
      cy.contains('1M').should('be.visible')
    })

    it('should scroll to latest message', () => {
      TestUtils.sendMultipleMessages(5)
      cy.contains('Message 5').should('be.visible')
    })

    it('should display message timestamps', () => {
      MessageInput.send('Test')
      MessageAssertions.assertTimestamp()
    })

    it('should differentiate user and assistant messages', () => {
      MessageInput.sendAndWait('User message')
      MessageAssertions.assertUserMessage('User message')
      MessageAssertions.assertAssistantMessage()
    })

    it('should show message avatars', () => {
      MessageInput.sendAndWait('Test')
      cy.get('[data-testid="user-avatar"]').should('be.visible')
      cy.get('[data-testid="assistant-avatar"]').should('be.visible')
    })
  })

  describe('Industry Context Switching', () => {
    it('should adapt templates to different industries', () => {
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Healthcare')
      cy.get('[data-testid="template-section"]').should('be.visible')
      cy.contains('Quick Start Templates').should('be.visible')
    })

    it('should maintain chat state on industry switch', () => {
      MessageInput.type('Initial message')
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Healthcare')
      cy.get('textarea[data-testid="message-input"]').should('have.value', '')
    })

    it('should show appropriate industry badge', () => {
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Healthcare')
      ComponentVisibility.assertIndustryBadge('Healthcare')
    })

    it('should reset agent status on industry change', () => {
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Healthcare')
      ComponentVisibility.assertAgentStatus()
    })
  })

  describe('Message Validation', () => {
    it('should prevent empty message submission', () => {
      UIState.assertSendButtonDisabled()
      MessageInput.type('   ')
      UIState.assertSendButtonDisabled()
    })

    it('should trim whitespace from messages', () => {
      MessageInput.type('  Test message  ')
      cy.get('[data-testid="send-button"]').click()
      MessageAssertions.assertUserMessage('Test message')
    })

    it('should handle special characters', () => {
      const specialMessage = 'Test @#$%^&*()_+ message'
      MessageInput.send(specialMessage)
      MessageAssertions.assertUserMessage(specialMessage)
    })

    it('should preserve line breaks in display', () => {
      cy.get('textarea[data-testid="message-input"]')
        .type('Line 1{shift+enter}Line 2{enter}')
      cy.contains('Line 1').should('be.visible')
      cy.contains('Line 2').should('be.visible')
    })
  })

  describe('Chat State Management', () => {
    it('should preserve messages on page refresh', () => {
      MessageInput.sendAndWait('Persistent message')
      cy.reload()
      WaitHelpers.brief()
      cy.contains('Persistent message').should('be.visible')
    })

    it('should maintain scroll position', () => {
      TestUtils.sendMultipleMessages(3)
      cy.get('[data-testid="chat-container"]').scrollTo('top')
      MessageInput.send('New message')
      cy.contains('New message').should('be.visible')
    })

    it('should handle browser back/forward', () => {
      MessageInput.sendAndWait('Test message')
      cy.go('back')
      cy.go('forward')
      cy.contains('Test message').should('be.visible')
    })

    it('should clear state on explicit reset', () => {
      MessageInput.sendAndWait('Message to clear')
      cy.get('[data-testid="clear-chat"]').click()
      cy.contains('Message to clear').should('not.exist')
    })
  })
})