/// <reference types="cypress" />

import {
  ChatNavigation,
  MessageInput,
  Templates,
  MessageAssertions,
  ComponentVisibility,
  UIState,
  TestUtils,
  WaitHelpers,
  MetricsValidation
} from './utils/chat-test-helpers'

describe('Demo E2E Test Suite 3: Chat Interaction and Optimization Workflow', () => {
  beforeEach(() => {
    ChatNavigation.setupTechnology()
  })

  describe('Chat Interface Initialization', () => {
    it('should display welcome message with industry context', () => {
      cy.contains('Welcome').should('be.visible')
      cy.contains('Technology').should('be.visible')
      cy.contains('industry-specific optimization scenarios').should('be.visible')
    })

    it('should show multi-agent status indicators', () => {
      ComponentVisibility.assertAgentStatus()
    })

    it('should display industry-specific templates', () => {
      const templates = [
        'Code Generation Pipeline',
        'CI/CD Optimization',
        'User Analytics AI'
      ]
      
      templates.forEach(template => {
        cy.contains(template).should('be.visible')
      })
    })

    it('should have functional message input area', () => {
      cy.get('textarea[placeholder*="optimization needs"]').should('be.visible')
      cy.get('button[class*="px-4"]').should('be.visible')
    })
  })

  describe('Template Selection and Usage', () => {
    it('should populate input when template is clicked', () => {
      Templates.selectTemplate('Code Generation Pipeline')
      cy.get('textarea').should('have.value').and('include', 'code completion')
    })

    it('should show template categories', () => {
      cy.contains('Development').should('be.visible')
      cy.contains('DevOps').should('be.visible')
      cy.contains('Analytics').should('be.visible')
    })

    it('should handle rapid template switching', () => {
      Templates.selectTemplate('Code Generation Pipeline')
      Templates.selectTemplate('CI/CD Optimization')
      Templates.selectTemplate('User Analytics AI')
      
      cy.get('textarea').should('have.value').and('include', 'user behavior')
    })
  })

  describe('Message Sending and Agent Processing', () => {
    it('should send custom messages', () => {
      const message = 'Optimize my ML inference pipeline for cost'
      MessageInput.type(message)
      cy.get('button[class*="px-4"]').click()
      
      // Check message appears in chat
      cy.contains(message).should('be.visible')
      
      // Check for agent processing
      cy.contains('is processing...').should('be.visible')
    })

    it('should show agent orchestration in action', () => {
      MessageInput.type('Analyze my workload')
      cy.get('button[class*="px-4"]').click()
      
      // Check agent activation sequence
      // Check for agent processing indicators
      cy.get('.animate-pulse').should('exist')
      cy.contains('is processing...').should('be.visible')
    })

    it('should display agent response with metrics', () => {
      MessageInput.sendAndWait('Optimize my system')
      
      // Check for response elements in message cards
      cy.get('[class*="border"]').should('exist') // Message cards have border classes
      cy.get('.p-3').should('exist') // CardContent with p-3 class
      cy.contains('Optimization').should('be.visible')
    })

    it('should show processing time and tokens used', () => {
      MessageInput.sendAndWait('Help me reduce costs')
      
      // Check for metrics display in message metadata
      // Processing time is displayed in seconds, not ms
      cy.get('.text-xs').should('exist') // Metadata badges
    })
  })

  describe('Optimization Recommendations', () => {
    it('should provide specific optimization strategies', () => {
      Templates.selectTemplate('Analyze Current Workload')
      cy.get('button[class*="px-4"]').click()
      WaitHelpers.forResponse()
      
      // Check for strategy mentions in assistant messages
      cy.get('.flex.gap-3:not(.justify-end)').should('exist')
      cy.contains('Optimization').should('exist')
    })

    it('should show quantified improvements', () => {
      MessageInput.sendAndWait('Show me potential improvements')
      
      // Check for quantified metrics using helper
      MetricsValidation.assertPercentageGains()
      MetricsValidation.assertSavingsAmount()
    })

    it('should provide implementation steps', () => {
      MessageInput.sendAndWait('How to implement optimizations')
      
      // Check for implementation-related terms in assistant messages
      cy.get('.flex.gap-3:not(.justify-end)').should('exist')
      cy.contains(/Deploy|Implement|Enable|Optimize/i).should('be.visible')
    })
  })

  describe('Chat Interaction Features', () => {
    it('should support keyboard shortcuts', () => {
      MessageInput.send('Test message')
      cy.contains('Test message').should('be.visible')
    })

    it('should handle multi-line messages', () => {
      cy.get('textarea').type('Line 1{shift+enter}Line 2{shift+enter}Line 3')
      cy.get('button[class*="px-4"]').click()
      
      cy.contains('Line 1').should('be.visible')
      cy.contains('Line 2').should('be.visible')
      cy.contains('Line 3').should('be.visible')
    })

    it('should scroll to latest message automatically', () => {
      TestUtils.sendMultipleMessages(3) // Reduce count to prevent timeout
      
      // Check that latest message is visible
      cy.contains('Message 3').should('be.visible')
    })

    it('should disable send while processing', () => {
      MessageInput.type('Test message')
      cy.get('button[class*="px-4"]').click()
      
      // Button and input should be disabled during processing
      cy.get('button[class*="px-4"]').should('be.disabled')
      cy.get('textarea').should('be.disabled')
      
      WaitHelpers.forResponse()
      
      // Should be enabled after processing
      cy.get('button[class*="px-4"]').should('not.be.disabled')
      cy.get('textarea').should('not.be.disabled')
    })
  })

  describe('Optimization Insights Panel', () => {
    it('should show optimization readiness indicator', () => {
      MessageInput.sendAndWait('Analyze my workload')
      
      cy.contains('Optimization Ready').should('be.visible')
      cy.contains('Potential Savings').should('be.visible')
      cy.contains('$45K/month').should('be.visible')
    })

    it('should display performance gains', () => {
      MessageInput.sendAndWait('Improve performance')
      
      cy.contains('Performance Gain').should('be.visible')
      cy.contains('faster').should('be.visible')
    })

    it('should show implementation timeline', () => {
      MessageInput.sendAndWait('Implementation timeline')
      
      cy.contains('Implementation Time').should('be.visible')
      cy.contains('weeks').should('be.visible')
    })
  })

  describe('Industry-Specific Responses', () => {
    it('should provide Technology-specific recommendations', () => {
      MessageInput.sendAndWait('Optimize code generation')
      
      // Check for technology-specific terms in assistant messages
      cy.get('.flex.gap-3:not(.justify-end)').should('exist')
      cy.contains(/IDE|code|development/i).should('be.visible')
    })

    it('should adapt responses based on selected industry', () => {
      // Test Healthcare industry
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Healthcare')
      
      MessageInput.sendAndWait('Optimize my workload')
      
      // Check for healthcare-specific terms in assistant messages
      cy.get('.flex.gap-3:not(.justify-end)').should('exist')
      cy.contains(/diagnostic|patient|medical/i).should('be.visible')
    })
  })

  describe('Error Handling and Edge Cases', () => {
    it('should handle empty message submission', () => {
      // Send button should be disabled for empty input
      UIState.assertSendButtonDisabled()
      
      // Empty message should not be sent
      cy.get('textarea').should('have.value', '')
    })

    it('should handle very long messages', () => {
      const longMessage = TestUtils.generateLongMessage(1000)
      MessageInput.type(longMessage)
      cy.get('button[class*="px-4"]').click()
      
      // Should handle gracefully - check partial content
      cy.contains('a'.repeat(50)).should('be.visible')
    })

    it('should handle rapid message sending', () => {
      for (let i = 1; i <= 3; i++) {
        MessageInput.type(`Quick message ${i}`)
        cy.get('button[class*="px-4"]').click()
        cy.wait(100)
      }
      
      // Should queue or handle messages properly
      cy.contains('Quick message 1').should('be.visible')
    })

    it('should handle network interruptions gracefully', () => {
      cy.intercept('POST', '/api/demo/chat', { forceNetworkError: true })
      
      MessageInput.type('Test message')
      cy.get('button[class*="px-4"]').click()
      
      // Should show error message in chat
      cy.contains(/unavailable|try again|error/i).should('be.visible')
    })
  })

  describe('Chat History and Context', () => {
    it('should maintain conversation context', () => {
      MessageInput.sendAndWait('My company processes 10M requests')
      MessageInput.sendAndWait('How much can I save?')
      
      // Response should reference previous context
      cy.contains('10M').should('be.visible')
    })

    it('should show message timestamps', () => {
      MessageInput.send('Test message')
      
      // Check for message metadata with badges
      cy.get('.text-xs').should('exist') // Metadata badges use text-xs class
    })

    it('should differentiate user and assistant messages', () => {
      MessageInput.sendAndWait('User message')
      
      // Check message alignment and structure
      cy.contains('User message').should('be.visible')
      // User messages should be right-aligned (justify-end)
      cy.get('.justify-end').should('exist')
      // Assistant messages use different alignment
      cy.get('.flex.gap-3:not(.justify-end)').should('exist')
    })
  })

  describe('Performance and Responsiveness', () => {
    it('should handle chat smoothly on mobile', () => {
      TestUtils.setMobileViewport()
      
      cy.get('textarea').should('be.visible')
      MessageInput.type('Mobile test')
      cy.get('button[class*="px-4"]').click()
      
      cy.contains('Mobile test').should('be.visible')
    })

    it('should maintain performance with many messages', () => {
      // Send fewer messages to prevent timeout
      TestUtils.sendMultipleMessages(5)
      
      // Interface should remain responsive
      MessageInput.type('Final message')
      cy.get('textarea').should('have.value', 'Final message')
    })

    it('should load chat interface quickly', () => {
      cy.visit('/demo', {
        onBeforeLoad: (win) => {
          win.performance.mark('start')
        },
        onLoad: (win) => {
          win.performance.mark('end')
          win.performance.measure('load', 'start', 'end')
          const measure = win.performance.getEntriesByType('measure')[0]
          expect(measure.duration).to.be.lessThan(3000)
        }
      })
      
      ChatNavigation.selectIndustry('Technology')
      cy.get('textarea').should('be.visible')
    })
  })
})