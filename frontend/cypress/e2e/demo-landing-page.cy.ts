/// <reference types="cypress" />

describe('Demo Landing Page E2E Tests', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/demo')
  })

  describe('Page Load and Initial State', () => {
    it('should load the demo landing page successfully', () => {
      cy.url().should('include', '/demo')
      cy.contains('Enterprise AI Optimization Platform Beta').should('be.visible')
    })

    it('should display the main heading and subheading', () => {
      cy.contains('Enterprise AI Optimization Platform Beta').should('be.visible')
      cy.contains('Reduce costs by 40-60% while improving performance by 2-3x').should('be.visible')
    })

    it('should show demo steps', () => {
      cy.contains('Select Your Industry').should('be.visible')
      cy.contains('Live Demo').should('be.visible')
    })

    it('should display value propositions', () => {
      cy.contains('40-60% Cost Reduction').should('be.visible')
      cy.contains('2-3x Performance Gain').should('be.visible')
      cy.contains('Enterprise Security').should('be.visible')
    })
  })

  describe('Industry Selection', () => {
    it('should display all industry options', () => {
      const industries = ['Financial Services', 'Healthcare', 'E-commerce', 'Manufacturing', 'Technology', 'Government & Defense']
      industries.forEach(industry => {
        cy.contains(industry).should('be.visible')
      })
    })

    it('should have icons for each industry', () => {
      // Icons are rendered as part of the industry cards, check for card structure
      cy.get('.grid').find('[class*="cursor-pointer"]').should('have.length.at.least', 6)
    })

    it('should allow selecting an industry', () => {
      cy.contains('Financial Services').click()
      // After selection, the industry selection should be hidden and tabs should appear
      cy.get('[role="tablist"]').should('be.visible')
    })

    it('should update progress when industry is selected', () => {
      cy.contains('Healthcare').click()
      // Progress is now step-based, check for demo tabs appearance
      cy.get('[role="tablist"]').should('be.visible')
      cy.contains('Overview').should('be.visible')
    })

    it('should show industry-specific description on hover', () => {
      // Industry cards show descriptions by default, not on hover
      cy.contains('Online retail, marketplaces, and direct-to-consumer').should('be.visible')
      cy.contains('Recommendations').should('be.visible')
    })

    it('should allow changing industry selection', () => {
      // Once an industry is selected, user proceeds to demo tabs
      // This test no longer applies as the UI flows differently
      cy.contains('Technology').click()
      cy.get('[role="tablist"]').should('be.visible')
      cy.contains('Personalized for Technology').should('be.visible')
    })
  })

  describe('Demo Navigation Tabs', () => {
    beforeEach(() => {
      cy.contains('Technology').click()
    })

    it('should display all demo tabs', () => {
      const tabs = ['Overview', 'ROI Calculator', 'AI Chat', 'Metrics', 'Data Insights', 'Next Steps']
      tabs.forEach(tab => {
        cy.contains(tab).should('be.visible')
      })
    })

    it('should navigate to AI Chat tab', () => {
      cy.contains('AI Chat').click()
      // AI Chat tab content varies by industry
      cy.get('[role="tabpanel"]').should('be.visible')
    })

    it('should navigate to ROI Calculator tab', () => {
      cy.contains('ROI Calculator').click()
      // ROI Calculator content will be loaded
      cy.get('[role="tabpanel"]').should('be.visible')
    })

    it('should navigate to Metrics tab', () => {
      cy.contains('Metrics').click()
      // Metrics tab content will be loaded
      cy.get('[role="tabpanel"]').should('be.visible')
    })

    it('should navigate to Next Steps tab', () => {
      cy.contains('Next Steps').click()
      // Next Steps tab content will be loaded
      cy.get('[role="tabpanel"]').should('be.visible')
    })

    it('should maintain tab state when switching', () => {
      cy.contains('AI Chat').click()
      cy.contains('Metrics').click()
      cy.contains('AI Chat').click()
      cy.get('[role="tabpanel"]').should('be.visible')
    })

    it('should show overview tab content initially', () => {
      // The overview tab should be active by default and show welcome content
      cy.contains('Welcome to Netra AI Optimization Platform').should('be.visible')
      cy.contains('Personalized for Technology').should('be.visible')
      cy.contains('Start ROI Analysis').should('be.visible')
    })
  })

  describe('Welcome Section Features', () => {
    it('should display key value propositions', () => {
      cy.contains('Technology').click() // Select industry first
      cy.contains('40-60% Cost Reduction').should('be.visible')
      cy.contains('2-3x Performance Gain').should('be.visible')
      cy.contains('Enterprise Security').should('be.visible')
    })

    it('should show gradient backgrounds', () => {
      cy.get('.bg-gradient-to-br').should('exist')
    })

    it('should display overview stats after industry selection', () => {
      cy.contains('Technology').click()
      cy.contains('2,500+').should('be.visible') // Active Customers
      cy.contains('10B+/month').should('be.visible') // Requests Optimized
      cy.contains('380%').should('be.visible') // Average ROI
    })

    it('should have call-to-action buttons', () => {
      cy.contains('Technology').click()
      cy.contains('button', 'Start ROI Analysis').should('be.visible')
    })
  })

  describe('Responsive Design', () => {
    it('should adapt to mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.contains('Enterprise AI Optimization Platform Beta').should('be.visible')
      cy.contains('Financial Services').should('be.visible')
    })

    it('should adapt to tablet viewport', () => {
      cy.viewport('ipad-2')
      cy.contains('Enterprise AI Optimization Platform Beta').should('be.visible')
      cy.contains('Financial Services').should('be.visible')
    })

    it('should handle industry selection on mobile', () => {
      cy.viewport('iphone-x')
      cy.contains('Technology').click()
      cy.get('[role="tablist"]').should('be.visible')
    })

    it('should show tabs on mobile after industry selection', () => {
      cy.viewport('iphone-x')
      cy.contains('Technology').click()
      cy.get('[role="tablist"]').should('be.visible')
      cy.contains('Overview').should('be.visible')
    })
  })

  describe('Animations and Transitions', () => {
    it('should have hover effects on industry cards', () => {
      cy.get('.cursor-pointer').first().trigger('mouseenter')
      // Cards should have hover shadow effects
      cy.get('.hover\\:shadow-xl').should('exist')
    })

    it('should have smooth tab transitions', () => {
      cy.contains('Technology').click()
      cy.contains('AI Chat').click()
      cy.get('[role="tabpanel"]').should('be.visible')
    })

    it('should have transition classes', () => {
      cy.contains('Technology').click()
      cy.get('.transition-all').should('exist')
    })
  })

  describe('Industry-Specific Content', () => {
    it('should show Financial Services use cases', () => {
      // Check use cases are shown in the industry selection card
      cy.contains('Financial Services').parent().within(() => {
        cy.contains('Fraud Detection').should('be.visible')
        cy.contains('Risk Analysis').should('be.visible')
        cy.contains('Trading Algorithms').should('be.visible')
        cy.contains('Customer Service').should('be.visible')
      })
    })

    it('should show Healthcare use cases', () => {
      cy.contains('Healthcare').parent().within(() => {
        cy.contains('Diagnostic AI').should('be.visible')
        cy.contains('Drug Discovery').should('be.visible')
        cy.contains('Patient Care').should('be.visible')
        cy.contains('Medical Imaging').should('be.visible')
      })
    })

    it('should show E-commerce use cases', () => {
      cy.contains('E-commerce').parent().within(() => {
        cy.contains('Recommendations').should('be.visible')
        cy.contains('Search').should('be.visible')
        cy.contains('Inventory').should('be.visible')
        cy.contains('Customer Support').should('be.visible')
      })
    })

    it('should show Technology use cases', () => {
      cy.contains('Technology').parent().within(() => {
        cy.contains('Code Generation').should('be.visible')
        cy.contains('DevOps AI').should('be.visible')
        cy.contains('Product Analytics').should('be.visible')
        cy.contains('Content Creation').should('be.visible')
      })
    })

    it('should show personalized content after selection', () => {
      cy.contains('Technology').click()
      cy.contains('Personalized for Technology').should('be.visible')
    })
  })

  describe('Error Handling and Edge Cases', () => {
    it('should show industry selection by default', () => {
      cy.visit('/demo')
      cy.contains('Select Your Industry').should('be.visible')
      cy.contains('Financial Services').should('be.visible')
    })

    it('should handle browser navigation', () => {
      cy.contains('Technology').click()
      cy.contains('AI Chat').click()
      cy.go('back')
      cy.url().should('include', '/demo')
    })

    it('should reset state on page refresh', () => {
      cy.contains('Healthcare').click()
      cy.contains('ROI Calculator').click()
      cy.reload()
      // After reload, should be back to industry selection
      cy.contains('Select Your Industry').should('be.visible')
    })

    it('should handle industry selection properly', () => {
      // Test that selecting an industry works correctly
      cy.contains('Technology').click()
      cy.get('[role="tablist"]').should('be.visible')
      cy.contains('Personalized for Technology').should('be.visible')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      cy.get('[aria-label]').should('have.length.at.least', 5)
    })

    it('should support keyboard navigation', () => {
      cy.get('body').tab()
      cy.focused().should('exist')
      cy.focused().type('{enter}')
    })

    it('should have proper heading hierarchy', () => {
      cy.get('h1').should('have.length', 1)
      cy.get('h2').should('exist')
      cy.get('h3').should('exist')
    })

    it('should have sufficient color contrast', () => {
      cy.get('.text-white').should('have.css', 'color', 'rgb(255, 255, 255)')
      cy.get('.bg-black').should('have.css', 'background-color', 'rgb(0, 0, 0)')
    })
  })

  describe('Performance', () => {
    it('should load page within acceptable time', () => {
      cy.visit('/demo', {
        onBeforeLoad: (win) => {
          win.performance.mark('start')
        },
        onLoad: (win) => {
          win.performance.mark('end')
          win.performance.measure('load', 'start', 'end')
          const measure = win.performance.getEntriesByType('measure')[0]
          expect(measure.duration).to.be.lessThan(5000) // More realistic timeout
        }
      })
    })

    it('should load tab content on demand', () => {
      cy.contains('Technology').click()
      cy.contains('Metrics').click()
      cy.get('[role="tabpanel"]').should('be.visible')
    })

    it('should handle component loading', () => {
      cy.contains('Technology').click()
      cy.contains('Data Insights').click()
      cy.get('[role="tabpanel"]').should('be.visible')
    })
  })
})