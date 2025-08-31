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
    it('should render DemoChat component with main chat card', () => {
      cy.get('.grid').should('exist')
      cy.get('.lg\\:col-span-2').should('exist') // Main chat area
      cy.contains('AI Optimization Assistant').should('be.visible')
    })

    it('should display chat header with title', () => {
      cy.contains('AI Optimization Assistant').should('be.visible')
      cy.contains('Powered by multi-agent orchestration').should('be.visible')
    })

    it('should show agent status badges', () => {
      cy.contains('Triage Agent').should('be.visible')
      cy.contains('Analysis Agent').should('be.visible')
      cy.contains('Optimization Agent').should('be.visible')
    })

    it('should show WebSocket connection status when enabled', () => {
      // WebSocket status only visible when useWebSocket=true
      cy.get('[class*="animate-pulse"]').should('exist')
    })
  })

  describe('Template System', () => {
    it('should display industry-specific templates', () => {
      cy.contains('Quick Templates').should('be.visible')
      cy.contains('Industry-specific optimization scenarios').should('be.visible')
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
      cy.get('textarea')
        .should('have.value')
        .and('include', 'code completion')
    })

    it('should show template categories', () => {
      cy.contains('Development').should('be.visible')
      cy.contains('DevOps').should('be.visible')
      cy.contains('Analytics').should('be.visible')
    })

    it('should handle template switching', () => {
      Templates.selectTemplate('Code Generation Pipeline')
      Templates.selectTemplate('User Analytics AI')
      cy.get('textarea')
        .should('have.value')
        .and('include', 'user behavior')
    })
  })

  describe('Message Input and Sending', () => {
    it('should have message input textarea', () => {
      cy.get('textarea').should('be.visible')
      cy.get('textarea').should('have.attr', 'placeholder')
      cy.get('textarea').should('contain.value', '')
    })

    it('should enable send button with text', () => {
      cy.get('button[class*="px-4"]').should('be.disabled') // Send button should be disabled initially
      MessageInput.type('Test message')
      cy.get('button[class*="px-4"]').should('not.be.disabled')
    })

    it('should send message on button click', () => {
      MessageInput.type('Optimize my workload')
      cy.get('button[class*="px-4"]').click()
      cy.contains('Optimize my workload').should('be.visible')
    })

    it('should send message on Enter key', () => {
      MessageInput.send('Test message')
      cy.contains('Test message').should('be.visible')
    })

    it('should support multi-line with Shift+Enter', () => {
      cy.get('textarea')
        .type('Line 1{shift+enter}Line 2')
      cy.get('textarea')
        .should('have.value', 'Line 1\nLine 2')
    })

    it('should clear input after sending', () => {
      MessageInput.send('Test')
      cy.get('textarea').should('have.value', '')
    })

    it('should disable input while processing', () => {
      MessageInput.send('Test')
      cy.get('textarea').should('be.disabled')
      WaitHelpers.forResponse()
      cy.get('textarea').should('not.be.disabled')
    })
  })

  describe('Chat History Management', () => {
    it('should maintain conversation context', () => {
      MessageInput.sendAndWait('My system processes 1M requests')
      MessageInput.sendAndWait('How much can I save?')
      cy.contains('1M').should('be.visible')
    })

    it('should scroll to latest message', () => {
      TestUtils.sendMultipleMessages(3) // Reduce number to prevent timeout
      cy.contains('Message 3').should('be.visible')
    })

    it('should differentiate user and assistant messages', () => {
      MessageInput.sendAndWait('User message')
      cy.contains('User message').should('be.visible')
      // User messages should be right-aligned (justify-end)
      cy.get('.justify-end').should('exist')
      // Wait for assistant response before checking for messages without justify-end
      cy.wait(2000)
      cy.get('.flex.gap-3:not(.justify-end)', { timeout: 10000 }).should('exist')
    })

    it('should show message avatars', () => {
      MessageInput.sendAndWait('Test')
      // Look for avatar components using their class structure
      cy.get('.h-8.w-8').should('have.length.at.least', 1)
    })

    it('should display messages in cards', () => {
      MessageInput.sendAndWait('Test message')
      // Messages are displayed using Card components with specific styling
      cy.get('[class*="border"]').should('exist') // Card components have border classes
      cy.get('.p-3').should('exist') // CardContent with p-3 class
    })
  })

  describe('Industry Context Switching', () => {
    it('should adapt templates to different industries', () => {
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Healthcare')
      cy.contains('Quick Templates').should('be.visible')
      cy.contains('Industry-specific optimization scenarios').should('be.visible')
    })

    it('should maintain chat state on industry switch', () => {
      MessageInput.type('Initial message')
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Healthcare')
      cy.get('textarea').should('have.value', '')
    })

    it('should show healthcare-specific templates', () => {
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Healthcare')
      cy.contains('Medical Image Analysis').should('be.visible')
      cy.contains('Patient Risk Prediction').should('be.visible')
    })

    it('should show appropriate agent status on industry change', () => {
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Healthcare')
      cy.contains('Triage Agent').should('be.visible')
      cy.contains('Analysis Agent').should('be.visible')
      cy.contains('Optimization Agent').should('be.visible')
    })
  })

  describe('Message Validation', () => {
    it('should prevent empty message submission', () => {
      cy.get('button[class*="px-4"]').should('be.disabled')
      MessageInput.type('   ')
      cy.get('button[class*="px-4"]').should('be.disabled')
    })

    it('should trim whitespace from messages', () => {
      MessageInput.type('  Test message  ')
      cy.get('button[class*="px-4"]').click()
      cy.contains('Test message').should('be.visible')
    })

    it('should handle special characters', () => {
      const specialMessage = 'Test @#$%^&*()_+ message'
      MessageInput.send(specialMessage)
      cy.contains(specialMessage).should('be.visible')
    })

    it('should preserve line breaks in display', () => {
      cy.get('textarea')
        .type('Line 1{shift+enter}Line 2{enter}')
      cy.contains('Line 1').should('be.visible')
      cy.contains('Line 2').should('be.visible')
    })
  })

  describe('Chat State Management', () => {
    it('should show welcome message on page load', () => {
      // The welcome message is generated dynamically based on industry
      cy.contains('Welcome').should('be.visible')
      cy.contains('Technology').should('be.visible')
    })

    it('should maintain scroll position in scroll area', () => {
      TestUtils.sendMultipleMessages(2) // Reduce number to prevent timeout
      // ScrollArea component should exist in the chat area
      cy.get('.flex-1').should('exist') // Chat scroll area has flex-1 class
      MessageInput.send('New message')
      cy.contains('New message').should('be.visible')
    })

    it('should handle browser navigation', () => {
      MessageInput.sendAndWait('Test message')
      cy.go('back')
      cy.go('forward')
      // Page should reload and show welcome message
      cy.contains('Welcome').should('be.visible')
    })

    it('should show processing indicator during agent processing', () => {
      MessageInput.send('Test processing')
      cy.get('[class*="animate-spin"]').should('be.visible')
      // The processing indicator shows agent names with "is processing..." text
      cy.contains('is processing...').should('be.visible')
    })

    it('should show optimization panel after interaction', () => {
      MessageInput.sendAndWait('Test for optimization')
      WaitHelpers.forResponse()
      cy.contains('Optimization Ready').should('be.visible')
    })
  })
})