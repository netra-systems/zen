/// <reference types="cypress" />

describe('DemoChat Component E2E Tests', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/demo')
    cy.contains('Technology').click()
    cy.contains('AI Chat').click()
    cy.wait(500)
  })

  describe('Component Initialization', () => {
    it('should render DemoChat component', () => {
      cy.get('[data-testid="demo-chat"]').should('be.visible')
    })

    it('should display chat header with title', () => {
      cy.get('[data-testid="chat-header"]').should('be.visible')
      cy.contains('Netra AI Optimization Demo').should('be.visible')
    })

    it('should show industry context badge', () => {
      cy.get('[data-testid="industry-badge"]').should('be.visible')
      cy.contains('Technology').should('be.visible')
    })

    it('should display agent status indicators', () => {
      cy.get('[data-testid="agent-status"]').should('be.visible')
      cy.contains('Ready').should('be.visible')
    })

    it('should show WebSocket connection status', () => {
      cy.get('[data-testid="connection-status"]').should('exist')
      cy.get('[data-testid="connection-status"]').should('have.class', 'bg-green-500')
    })
  })

  describe('Template System', () => {
    it('should display industry-specific templates', () => {
      cy.get('[data-testid="template-section"]').should('be.visible')
      cy.contains('Quick Start Templates').should('be.visible')
    })

    it('should show Technology industry templates', () => {
      const templates = [
        'Code Generation Pipeline',
        'CI/CD Optimization', 
        'User Analytics AI',
        'API Performance Tuning'
      ]
      templates.forEach(template => {
        cy.contains(template).should('be.visible')
      })
    })

    it('should categorize templates', () => {
      cy.contains('Development').should('be.visible')
      cy.contains('DevOps').should('be.visible')
      cy.contains('Analytics').should('be.visible')
    })

    it('should populate message on template click', () => {
      cy.contains('Code Generation Pipeline').click()
      cy.get('textarea[data-testid="message-input"]')
        .should('have.value')
        .and('include', 'code completion')
    })

    it('should show template description on hover', () => {
      cy.contains('CI/CD Optimization').trigger('mouseenter')
      cy.contains('Optimize your continuous integration').should('be.visible')
    })

    it('should handle template switching', () => {
      cy.contains('Code Generation Pipeline').click()
      cy.contains('API Performance Tuning').click()
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
      cy.get('[data-testid="send-button"]').should('be.disabled')
      cy.get('textarea[data-testid="message-input"]').type('Test message')
      cy.get('[data-testid="send-button"]').should('not.be.disabled')
    })

    it('should send message on button click', () => {
      cy.get('textarea[data-testid="message-input"]').type('Optimize my workload')
      cy.get('[data-testid="send-button"]').click()
      cy.contains('Optimize my workload').should('be.visible')
    })

    it('should send message on Enter key', () => {
      cy.get('textarea[data-testid="message-input"]').type('Test message{enter}')
      cy.contains('Test message').should('be.visible')
    })

    it('should support multi-line with Shift+Enter', () => {
      cy.get('textarea[data-testid="message-input"]')
        .type('Line 1{shift+enter}Line 2')
      cy.get('textarea[data-testid="message-input"]')
        .should('have.value', 'Line 1\nLine 2')
    })

    it('should clear input after sending', () => {
      cy.get('textarea[data-testid="message-input"]').type('Test{enter}')
      cy.get('textarea[data-testid="message-input"]').should('have.value', '')
    })

    it('should disable input while processing', () => {
      cy.get('textarea[data-testid="message-input"]').type('Test{enter}')
      cy.get('textarea[data-testid="message-input"]').should('be.disabled')
      cy.wait(2000)
      cy.get('textarea[data-testid="message-input"]').should('not.be.disabled')
    })
  })

  describe('Agent Processing and Response', () => {
    it('should show agent processing indicators', () => {
      cy.get('textarea[data-testid="message-input"]').type('Analyze{enter}')
      cy.get('[data-testid="agent-processing"]').should('be.visible')
      cy.contains('Processing').should('be.visible')
    })

    it('should display multiple agent activations', () => {
      cy.get('textarea[data-testid="message-input"]').type('Complex analysis{enter}')
      cy.get('[data-testid="agent-indicator"]').should('have.length.at.least', 1)
    })

    it('should show agent names during processing', () => {
      cy.get('textarea[data-testid="message-input"]').type('Optimize{enter}')
      cy.contains(/Analyzer|Optimizer|Recommender/).should('be.visible')
    })

    it('should display agent response with formatting', () => {
      cy.get('textarea[data-testid="message-input"]').type('Help me optimize{enter}')
      cy.wait(3000)
      cy.get('[data-testid="assistant-message"]').should('be.visible')
      cy.get('[data-testid="assistant-message"]').find('h3').should('exist')
    })

    it('should show processing time', () => {
      cy.get('textarea[data-testid="message-input"]').type('Quick test{enter}')
      cy.wait(3000)
      cy.contains(/\d+ms/).should('be.visible')
    })

    it('should display token usage', () => {
      cy.get('textarea[data-testid="message-input"]').type('Analyze{enter}')
      cy.wait(3000)
      cy.contains('tokens').should('be.visible')
    })
  })

  describe('Performance Metrics Display', () => {
    it('should show optimization metrics in response', () => {
      cy.get('textarea[data-testid="message-input"]').type('Show optimization potential{enter}')
      cy.wait(3000)
      cy.contains('Cost Savings').should('be.visible')
      cy.contains('$').should('be.visible')
    })

    it('should display percentage improvements', () => {
      cy.get('textarea[data-testid="message-input"]').type('Performance gains{enter}')
      cy.wait(3000)
      cy.contains('%').should('be.visible')
    })

    it('should show latency reduction metrics', () => {
      cy.get('textarea[data-testid="message-input"]').type('Reduce latency{enter}')
      cy.wait(3000)
      cy.contains(/ms|latency/i).should('be.visible')
    })

    it('should display implementation timeline', () => {
      cy.get('textarea[data-testid="message-input"]').type('Implementation plan{enter}')
      cy.wait(3000)
      cy.contains(/week|day|phase/i).should('be.visible')
    })
  })

  describe('Chat History Management', () => {
    it('should maintain conversation context', () => {
      cy.get('textarea[data-testid="message-input"]').type('My system processes 1M requests{enter}')
      cy.wait(3000)
      cy.get('textarea[data-testid="message-input"]').type('How much can I save?{enter}')
      cy.wait(3000)
      cy.contains('1M').should('be.visible')
    })

    it('should scroll to latest message', () => {
      for(let i = 1; i <= 5; i++) {
        cy.get('textarea[data-testid="message-input"]').type(`Message ${i}{enter}`)
        cy.wait(1000)
      }
      cy.contains('Message 5').should('be.visible')
    })

    it('should display message timestamps', () => {
      cy.get('textarea[data-testid="message-input"]').type('Test{enter}')
      cy.get('[data-testid="message-timestamp"]').should('be.visible')
    })

    it('should differentiate user and assistant messages', () => {
      cy.get('textarea[data-testid="message-input"]').type('User message{enter}')
      cy.wait(3000)
      cy.get('[data-testid="user-message"]').should('have.class', 'justify-end')
      cy.get('[data-testid="assistant-message"]').should('have.class', 'justify-start')
    })

    it('should show message avatars', () => {
      cy.get('textarea[data-testid="message-input"]').type('Test{enter}')
      cy.wait(3000)
      cy.get('[data-testid="user-avatar"]').should('be.visible')
      cy.get('[data-testid="assistant-avatar"]').should('be.visible')
    })
  })

  describe('WebSocket Communication', () => {
    it('should establish WebSocket connection', () => {
      cy.window().its('WebSocket').should('exist')
    })

    it('should handle WebSocket messages', () => {
      cy.get('textarea[data-testid="message-input"]').type('Test WebSocket{enter}')
      cy.wait(1000)
      cy.get('[data-testid="ws-indicator"]').should('have.class', 'animate-pulse')
    })

    it('should reconnect on connection loss', () => {
      cy.window().then(win => {
        if (win.ws) {
          win.ws.close()
        }
      })
      cy.wait(2000)
      cy.get('[data-testid="connection-status"]').should('have.class', 'bg-green-500')
    })

    it('should fallback to HTTP on WebSocket failure', () => {
      cy.intercept('GET', '/ws', { statusCode: 500 })
      cy.get('textarea[data-testid="message-input"]').type('Test fallback{enter}')
      cy.wait(3000)
      cy.contains('Test fallback').should('be.visible')
    })
  })

  describe('Optimization Insights Panel', () => {
    it('should display insights panel after analysis', () => {
      cy.get('textarea[data-testid="message-input"]').type('Analyze my workload{enter}')
      cy.wait(3000)
      cy.get('[data-testid="insights-panel"]').should('be.visible')
    })

    it('should show readiness score', () => {
      cy.get('textarea[data-testid="message-input"]').type('Check optimization readiness{enter}')
      cy.wait(3000)
      cy.contains('Optimization Ready').should('be.visible')
      cy.get('[data-testid="readiness-score"]').should('contain', '%')
    })

    it('should display potential savings', () => {
      cy.get('textarea[data-testid="message-input"]').type('Calculate savings{enter}')
      cy.wait(3000)
      cy.contains('Potential Savings').should('be.visible')
      cy.contains(/\$[\d,]+/).should('be.visible')
    })

    it('should show quick actions', () => {
      cy.get('textarea[data-testid="message-input"]').type('Show actions{enter}')
      cy.wait(3000)
      cy.contains('Quick Actions').should('be.visible')
      cy.contains('Generate Report').should('be.visible')
      cy.contains('Schedule Call').should('be.visible')
    })
  })

  describe('Industry-Specific Responses', () => {
    it('should provide Technology-specific optimization', () => {
      cy.get('textarea[data-testid="message-input"]').type('Optimize code generation{enter}')
      cy.wait(3000)
      cy.contains(/code|development|IDE/i).should('be.visible')
    })

    it('should reference Technology tools and frameworks', () => {
      cy.get('textarea[data-testid="message-input"]').type('CI/CD pipeline{enter}')
      cy.wait(3000)
      cy.contains(/Jenkins|GitHub|Docker|Kubernetes/i).should('be.visible')
    })

    it('should adapt to different industries', () => {
      cy.visit('/demo')
      cy.contains('Healthcare').click()
      cy.contains('AI Chat').click()
      cy.get('textarea[data-testid="message-input"]').type('Optimize{enter}')
      cy.wait(3000)
      cy.contains(/patient|diagnostic|medical/i).should('be.visible')
    })
  })

  describe('Error Handling', () => {
    it('should handle empty message submission', () => {
      cy.get('[data-testid="send-button"]').should('be.disabled')
      cy.get('textarea[data-testid="message-input"]').type('   ')
      cy.get('[data-testid="send-button"]').should('be.disabled')
    })

    it('should handle very long messages', () => {
      const longMessage = 'a'.repeat(5000)
      cy.get('textarea[data-testid="message-input"]').type(longMessage, { delay: 0 })
      cy.get('[data-testid="send-button"]').click()
      cy.contains('Message too long').should('be.visible')
    })

    it('should handle API errors gracefully', () => {
      cy.intercept('POST', '/api/demo/chat', { statusCode: 500 })
      cy.get('textarea[data-testid="message-input"]').type('Test error{enter}')
      cy.contains(/error|failed|try again/i).should('be.visible')
    })

    it('should show retry option on failure', () => {
      cy.intercept('POST', '/api/demo/chat', { statusCode: 500 })
      cy.get('textarea[data-testid="message-input"]').type('Test{enter}')
      cy.contains('Retry').should('be.visible')
    })

    it('should handle rate limiting', () => {
      for(let i = 1; i <= 10; i++) {
        cy.get('textarea[data-testid="message-input"]').type(`Msg ${i}{enter}`)
      }
      cy.contains(/slow down|rate limit/i).should('be.visible')
    })
  })

  describe('UI Features and Animations', () => {
    it('should display glassmorphic styling', () => {
      cy.get('[data-testid="demo-chat"]').should('have.class', 'backdrop-blur')
      cy.get('[data-testid="demo-chat"]').should('have.class', 'bg-opacity-20')
    })

    it('should animate message appearance', () => {
      cy.get('textarea[data-testid="message-input"]').type('Test{enter}')
      cy.get('[data-testid="user-message"]').should('have.css', 'animation')
    })

    it('should show typing indicator', () => {
      cy.get('textarea[data-testid="message-input"]').type('Test{enter}')
      cy.get('[data-testid="typing-indicator"]').should('be.visible')
      cy.get('.animate-pulse').should('exist')
    })

    it('should have gradient backgrounds', () => {
      cy.get('.bg-gradient-to-r').should('exist')
      cy.get('.from-purple-500').should('exist')
    })

    it('should handle dark mode', () => {
      cy.get('[data-testid="theme-toggle"]').click()
      cy.get('[data-testid="demo-chat"]').should('have.class', 'dark')
    })
  })

  describe('Copy and Export Features', () => {
    it('should allow copying messages', () => {
      cy.get('textarea[data-testid="message-input"]').type('Test message{enter}')
      cy.wait(3000)
      cy.get('[data-testid="copy-message"]').first().click()
      cy.contains('Copied').should('be.visible')
    })

    it('should export conversation', () => {
      cy.get('textarea[data-testid="message-input"]').type('Test 1{enter}')
      cy.wait(2000)
      cy.get('textarea[data-testid="message-input"]').type('Test 2{enter}')
      cy.wait(2000)
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
  })

  describe('Mobile Responsiveness', () => {
    it('should adapt to mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="demo-chat"]').should('be.visible')
      cy.get('textarea[data-testid="message-input"]').should('be.visible')
    })

    it('should show mobile-optimized templates', () => {
      cy.viewport('iphone-x')
      cy.get('[data-testid="template-section"]').scrollIntoView()
      cy.get('[data-testid="template-card"]').should('have.css', 'width', '100%')
    })

    it('should handle mobile input', () => {
      cy.viewport('iphone-x')
      cy.get('textarea[data-testid="message-input"]').type('Mobile test')
      cy.get('[data-testid="send-button"]').click()
      cy.contains('Mobile test').should('be.visible')
    })

    it('should maintain functionality on tablet', () => {
      cy.viewport('ipad-2')
      cy.get('[data-testid="demo-chat"]').should('be.visible')
      cy.contains('Code Generation Pipeline').click()
      cy.get('textarea[data-testid="message-input"]').should('have.value')
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
      cy.get('textarea[data-testid="message-input"]').type('Test{enter}')
      cy.get('[role="status"]').should('contain', 'Processing')
    })

    it('should have proper focus management', () => {
      cy.get('textarea[data-testid="message-input"]').type('Test{enter}')
      cy.wait(3000)
      cy.focused().should('have.attr', 'data-testid', 'message-input')
    })
  })
})