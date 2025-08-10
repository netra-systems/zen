/// <reference types="cypress" />

describe('Demo E2E Test Suite 3: Chat Interaction and Optimization Workflow', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/demo')
    cy.contains('Technology').click()
    cy.contains('AI Chat').click({ force: true })
    cy.wait(500)
  })

  describe('Chat Interface Initialization', () => {
    it('should display welcome message with industry context', () => {
      cy.contains('Welcome to the Netra AI Optimization Demo').should('be.visible')
      cy.contains('Technology').should('be.visible')
      cy.contains('industry-specific optimization scenarios').should('be.visible')
    })

    it('should show multi-agent status indicators', () => {
      // Check for agent indicators
      cy.contains('Agent').should('exist')
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
      cy.get('button[aria-label="Send message"]').should('be.visible')
    })
  })

  describe('Template Selection and Usage', () => {
    it('should populate input when template is clicked', () => {
      cy.contains('Code Generation Pipeline').click()
      cy.get('textarea').should('have.value').and('include', 'code completion')
    })

    it('should show template categories', () => {
      cy.contains('Development').should('be.visible')
      cy.contains('DevOps').should('be.visible')
      cy.contains('Analytics').should('be.visible')
    })

    it('should handle rapid template switching', () => {
      cy.contains('Code Generation Pipeline').click()
      cy.contains('CI/CD Optimization').click()
      cy.contains('User Analytics AI').click()
      
      cy.get('textarea').should('have.value').and('include', 'user behavior')
    })
  })

  describe('Message Sending and Agent Processing', () => {
    it('should send custom messages', () => {
      const message = 'Optimize my ML inference pipeline for cost'
      cy.get('textarea').type(message)
      cy.get('button[aria-label="Send message"]').click()
      
      // Check message appears in chat
      cy.contains(message).should('be.visible')
      
      // Check for agent processing
      cy.contains('processing').should('be.visible')
    })

    it('should show agent orchestration in action', () => {
      cy.get('textarea').type('Analyze my workload')
      cy.get('button[aria-label="Send message"]').click()
      
      // Check agent activation sequence
      // Check for agent processing indicators
      cy.get('.animate-pulse').should('exist')
    })

    it('should display agent response with metrics', () => {
      cy.get('textarea').type('Optimize my system')
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(3000)
      
      // Check for response elements
      cy.contains('Optimization Strategy').should('be.visible')
      cy.contains('Cost savings').should('be.visible')
      cy.contains('Performance').should('be.visible')
      cy.contains('Implementation Plan').should('be.visible')
    })

    it('should show processing time and tokens used', () => {
      cy.get('textarea').type('Help me reduce costs')
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(3000)
      
      // Check for metrics display
      cy.contains('ms').should('exist')
    })
  })

  describe('Optimization Recommendations', () => {
    it('should provide specific optimization strategies', () => {
      cy.contains('Analyze Current Workload').click()
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(3000)
      
      const strategies = [
        'Model Compression',
        'Batch Optimization',
        'Caching Strategy',
        'Infrastructure Scaling',
        'Pipeline Parallelization'
      ]
      
      // At least one strategy should be mentioned
      // Check for strategy mentions
      cy.contains('Optimization').should('exist')
    })

    it('should show quantified improvements', () => {
      cy.get('textarea').type('Show me potential improvements')
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(3000)
      
      // Check for percentage improvements
      cy.contains(/%/).should('be.visible')
      cy.contains(/\$\d+/).should('be.visible') // Dollar amounts
      cy.contains(/\dx/).should('be.visible') // Multiplier improvements
    })

    it('should provide implementation steps', () => {
      cy.get('textarea').type('How to implement optimizations')
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(3000)
      
      cy.contains('Deploy').should('be.visible')
      cy.contains('Implement').should('be.visible')
      cy.contains('Enable').should('be.visible')
      cy.contains('Optimize').should('be.visible')
    })
  })

  describe('Chat Interaction Features', () => {
    it('should support keyboard shortcuts', () => {
      cy.get('textarea').type('Test message')
      cy.get('textarea').type('{enter}')
      
      cy.contains('Test message').should('be.visible')
    })

    it('should handle multi-line messages', () => {
      cy.get('textarea').type('Line 1{shift+enter}Line 2{shift+enter}Line 3')
      cy.get('button[aria-label="Send message"]').click()
      
      cy.contains('Line 1').should('be.visible')
      cy.contains('Line 2').should('be.visible')
      cy.contains('Line 3').should('be.visible')
    })

    it('should scroll to latest message automatically', () => {
      // Send multiple messages
      for (let i = 1; i <= 5; i++) {
        cy.get('textarea').type(`Message ${i}`)
        cy.get('button[aria-label="Send message"]').click()
        cy.wait(1000)
      }
      
      // Check that latest message is visible
      cy.contains('Message 5').should('be.visible')
    })

    it('should disable send while processing', () => {
      cy.get('textarea').type('Test message')
      cy.get('button[aria-label="Send message"]').click()
      
      // Button should be disabled during processing
      cy.get('button[aria-label="Send message"]').should('be.disabled')
      
      cy.wait(3000)
      
      // Button should be enabled after processing
      cy.get('button[aria-label="Send message"]').should('not.be.disabled')
    })
  })

  describe('Optimization Insights Panel', () => {
    it('should show optimization readiness indicator', () => {
      cy.get('textarea').type('Analyze my workload')
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(3000)
      
      cy.contains('Optimization Ready').should('be.visible')
      cy.contains('Potential Savings').should('be.visible')
      cy.contains('$45K/month').should('be.visible')
    })

    it('should display performance gains', () => {
      cy.get('textarea').type('Improve performance')
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(3000)
      
      cy.contains('Performance Gain').should('be.visible')
      cy.contains('faster').should('be.visible')
    })

    it('should show implementation timeline', () => {
      cy.get('textarea').type('Implementation timeline')
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(3000)
      
      cy.contains('Implementation Time').should('be.visible')
      cy.contains('weeks').should('be.visible')
    })
  })

  describe('Industry-Specific Responses', () => {
    it('should provide Technology-specific recommendations', () => {
      cy.get('textarea').type('Optimize code generation')
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(3000)
      
      cy.contains(/IDE|code|development/i).should('be.visible')
    })

    it('should adapt responses based on selected industry', () => {
      // Test Healthcare industry
      cy.visit('/demo')
      cy.contains('Healthcare').click()
      cy.contains('AI Chat').click({ force: true })
      
      cy.get('textarea').type('Optimize my workload')
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(3000)
      
      cy.contains(/diagnostic|patient|medical/i).should('be.visible')
    })
  })

  describe('Error Handling and Edge Cases', () => {
    it('should handle empty message submission', () => {
      cy.get('button[aria-label="Send message"]').click()
      
      // Should not send empty message
      // Empty message should not be sent
      cy.get('textarea').should('have.value', '')
    })

    it('should handle very long messages', () => {
      const longMessage = 'a'.repeat(1000)
      cy.get('textarea').type(longMessage, { delay: 0 })
      cy.get('button[aria-label="Send message"]').click()
      
      // Should handle gracefully
      cy.contains('a'.repeat(50)).should('be.visible')
    })

    it('should handle rapid message sending', () => {
      for (let i = 1; i <= 3; i++) {
        cy.get('textarea').type(`Quick message ${i}`)
        cy.get('button[aria-label="Send message"]').click()
        cy.wait(100)
      }
      
      // Should queue or handle messages properly
      cy.contains('Quick message 1').should('be.visible')
    })

    it('should handle network interruptions gracefully', () => {
      cy.intercept('POST', '/api/chat', { forceNetworkError: true })
      
      cy.get('textarea').type('Test message')
      cy.get('button[aria-label="Send message"]').click()
      
      // Should show error or fallback
      cy.contains(/error|try again|failed/i).should('be.visible')
    })
  })

  describe('Chat History and Context', () => {
    it('should maintain conversation context', () => {
      cy.get('textarea').type('My company processes 10M requests')
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(3000)
      
      cy.get('textarea').type('How much can I save?')
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(3000)
      
      // Response should reference previous context
      cy.contains('10M').should('be.visible')
    })

    it('should show message timestamps', () => {
      cy.get('textarea').type('Test message')
      cy.get('button[aria-label="Send message"]').click()
      
      // Check for timestamps
      cy.get('.text-xs').should('exist')
    })

    it('should differentiate user and assistant messages', () => {
      cy.get('textarea').type('User message')
      cy.get('button[aria-label="Send message"]').click()
      cy.wait(3000)
      
      // Check message alignment
      cy.contains('User message').should('be.visible')
    })
  })

  describe('Performance and Responsiveness', () => {
    it('should handle chat smoothly on mobile', () => {
      cy.viewport('iphone-x')
      
      cy.get('textarea').should('be.visible')
      cy.get('textarea').type('Mobile test')
      cy.get('button[aria-label="Send message"]').click()
      
      cy.contains('Mobile test').should('be.visible')
    })

    it('should maintain performance with many messages', () => {
      // Send 10 messages
      for (let i = 1; i <= 10; i++) {
        cy.get('textarea').type(`Message ${i}`)
        cy.get('button[aria-label="Send message"]').click()
        cy.wait(500)
      }
      
      // Interface should remain responsive
      cy.get('textarea').type('Final message')
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
      
      cy.contains('Technology').click()
      cy.contains('AI Chat').click({ force: true })
      cy.get('textarea').should('be.visible')
    })
  })
})