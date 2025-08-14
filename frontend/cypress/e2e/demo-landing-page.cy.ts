/// <reference types="cypress" />

describe('Demo Landing Page E2E Tests', () => {
  beforeEach(() => {
    cy.viewport(1920, 1080)
    cy.visit('/demo')
  })

  describe('Page Load and Initial State', () => {
    it('should load the demo landing page successfully', () => {
      cy.url().should('include', '/demo')
      cy.contains('Enterprise AI Optimization Demo').should('be.visible')
    })

    it('should display the main heading and subheading', () => {
      cy.contains('Enterprise AI Optimization Demo').should('be.visible')
      cy.contains('Experience how Netra transforms your AI workloads').should('be.visible')
    })

    it('should show demo steps', () => {
      cy.contains('Industry Selection').should('be.visible')
      cy.contains('ROI Analysis').should('be.visible')
    })

    it('should display value propositions', () => {
      cy.contains('40-60% Cost Reduction').should('be.visible')
      cy.contains('10x Performance Boost').should('be.visible')
    })
  })

  describe('Industry Selection', () => {
    it('should display all industry options', () => {
      const industries = ['Financial Services', 'Healthcare', 'E-commerce', 'Technology']
      industries.forEach(industry => {
        cy.contains(industry).should('be.visible')
      })
    })

    it('should have icons for each industry', () => {
      cy.get('[data-testid="industry-icon"]').should('have.length.at.least', 4)
    })

    it('should allow selecting an industry', () => {
      cy.contains('Financial Services').click()
      cy.contains('Financial Services').parent().should('have.class', 'ring-2')
    })

    it('should update progress when industry is selected', () => {
      cy.contains('Healthcare').click()
      cy.contains('25% Complete').should('be.visible')
    })

    it('should show industry-specific description on hover', () => {
      cy.contains('E-commerce').trigger('mouseenter')
      cy.contains('Optimize product recommendations').should('be.visible')
    })

    it('should allow changing industry selection', () => {
      cy.contains('Technology').click()
      cy.contains('Financial Services').click()
      cy.contains('Financial Services').parent().should('have.class', 'ring-2')
      cy.contains('Technology').parent().should('not.have.class', 'ring-2')
    })
  })

  describe('Demo Navigation Tabs', () => {
    beforeEach(() => {
      cy.contains('Technology').click()
    })

    it('should display all demo tabs', () => {
      const tabs = ['AI Chat', 'ROI Calculator', 'Performance', 'Implementation']
      tabs.forEach(tab => {
        cy.contains(tab).should('be.visible')
      })
    })

    it('should navigate to AI Chat tab', () => {
      cy.contains('AI Chat').click()
      cy.contains('Welcome to the Netra AI Optimization Demo').should('be.visible')
    })

    it('should navigate to ROI Calculator tab', () => {
      cy.contains('ROI Calculator').click()
      cy.contains('Calculate Your AI Optimization Savings').should('be.visible')
    })

    it('should navigate to Performance tab', () => {
      cy.contains('Performance').click()
      cy.contains('Real-Time Performance Metrics').should('be.visible')
    })

    it('should navigate to Implementation tab', () => {
      cy.contains('Implementation').click()
      cy.contains('Implementation Roadmap').should('be.visible')
    })

    it('should maintain tab state when switching', () => {
      cy.contains('AI Chat').click()
      cy.contains('Performance').click()
      cy.contains('AI Chat').click()
      cy.contains('Welcome to the Netra AI Optimization Demo').should('be.visible')
    })

    it('should update progress as tabs are visited', () => {
      cy.contains('AI Chat').click()
      cy.contains('50% Complete').should('be.visible')
      cy.contains('ROI Calculator').click()
      cy.contains('75% Complete').should('be.visible')
      cy.contains('Performance').click()
      cy.contains('100% Complete').should('be.visible')
    })
  })

  describe('Welcome Section Features', () => {
    it('should display key value propositions', () => {
      cy.contains('75% Cost Reduction').should('be.visible')
      cy.contains('10x Faster Processing').should('be.visible')
      cy.contains('Enterprise Ready').should('be.visible')
    })

    it('should show animated gradient backgrounds', () => {
      cy.get('.bg-gradient-to-br').should('exist')
      cy.get('.animate-gradient').should('exist')
    })

    it('should display feature cards with icons', () => {
      cy.get('[data-testid="feature-card"]').should('have.length.at.least', 3)
    })

    it('should have call-to-action buttons', () => {
      cy.contains('button', 'Start Demo').should('be.visible')
      cy.contains('a', 'Learn More').should('be.visible')
    })
  })

  describe('Responsive Design', () => {
    it('should adapt to mobile viewport', () => {
      cy.viewport('iphone-x')
      cy.contains('Netra AI Optimization Platform').should('be.visible')
      cy.get('[data-testid="mobile-menu"]').should('be.visible')
    })

    it('should adapt to tablet viewport', () => {
      cy.viewport('ipad-2')
      cy.contains('Netra AI Optimization Platform').should('be.visible')
      cy.contains('Financial Services').should('be.visible')
    })

    it('should handle industry selection on mobile', () => {
      cy.viewport('iphone-x')
      cy.contains('Technology').click()
      cy.contains('Technology').parent().should('have.class', 'ring-2')
    })

    it('should show mobile-optimized navigation', () => {
      cy.viewport('iphone-x')
      cy.contains('Technology').click()
      cy.get('[data-testid="mobile-tabs"]').should('be.visible')
    })
  })

  describe('Animations and Transitions', () => {
    it('should animate industry cards on hover', () => {
      cy.contains('Financial Services')
        .parent()
        .trigger('mouseenter')
        .should('have.css', 'transform')
        .and('not.equal', 'none')
    })

    it('should have smooth tab transitions', () => {
      cy.contains('Technology').click()
      cy.contains('AI Chat').click()
      cy.get('.transition-all').should('exist')
    })

    it('should animate progress bar updates', () => {
      cy.contains('Healthcare').click()
      cy.get('[data-testid="progress-bar"]')
        .should('have.css', 'transition')
        .and('include', 'width')
    })

    it('should use Framer Motion animations', () => {
      cy.get('[data-framer-motion]').should('exist')
    })
  })

  describe('Industry-Specific Content', () => {
    it('should show Financial Services specific content', () => {
      cy.contains('Financial Services').click()
      cy.contains('AI Chat').click()
      cy.contains('Risk Assessment').should('be.visible')
      cy.contains('Fraud Detection').should('be.visible')
    })

    it('should show Healthcare specific content', () => {
      cy.contains('Healthcare').click()
      cy.contains('AI Chat').click()
      cy.contains('Diagnostic AI').should('be.visible')
      cy.contains('Patient Care').should('be.visible')
    })

    it('should show E-commerce specific content', () => {
      cy.contains('E-commerce').click()
      cy.contains('AI Chat').click()
      cy.contains('Product Recommendations').should('be.visible')
      cy.contains('Customer Segmentation').should('be.visible')
    })

    it('should show Technology specific content', () => {
      cy.contains('Technology').click()
      cy.contains('AI Chat').click()
      cy.contains('Code Generation Pipeline').should('be.visible')
      cy.contains('CI/CD Optimization').should('be.visible')
    })
  })

  describe('Error Handling and Edge Cases', () => {
    it('should handle direct navigation to tabs without industry selection', () => {
      cy.visit('/demo#ai-chat')
      cy.contains('Please select an industry').should('be.visible')
    })

    it('should handle browser back button', () => {
      cy.contains('Technology').click()
      cy.contains('AI Chat').click()
      cy.go('back')
      cy.url().should('include', '/demo')
    })

    it('should maintain state on page refresh', () => {
      cy.contains('Healthcare').click()
      cy.contains('ROI Calculator').click()
      cy.reload()
      cy.contains('Healthcare').parent().should('have.class', 'ring-2')
    })

    it('should handle rapid clicking between industries', () => {
      const industries = ['Financial Services', 'Healthcare', 'E-commerce', 'Technology']
      industries.forEach(industry => {
        cy.contains(industry).click()
      })
      cy.contains('Technology').parent().should('have.class', 'ring-2')
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
          expect(measure.duration).to.be.lessThan(3000)
        }
      })
    })

    it('should lazy load heavy components', () => {
      cy.contains('Technology').click()
      cy.contains('Performance').click()
      cy.get('[data-testid="performance-metrics"]').should('be.visible')
    })

    it('should optimize image loading', () => {
      cy.get('img').each(($img) => {
        cy.wrap($img).should('have.attr', 'loading', 'lazy')
      })
    })
  })
})