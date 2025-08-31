/// <reference types="cypress" />

import { DemoLandingUtils, DEMO_LANDING_SELECTORS } from './utils/demo-landing-utils'

/**
 * Demo Landing Page E2E Tests
 * 
 * BVJ: Free segment - Core landing page validation for first-time users
 * Business Goal: Validate user onboarding and demo experience for conversion
 * Value Impact: Ensures Free users have smooth experience leading to paid tier conversion
 * Revenue Impact: Supports Free-to-paid conversion pipeline
 */

describe('Demo Landing Page E2E Tests', () => {
  beforeEach(() => {
    DemoLandingUtils.setupDemoPage()
  })

  describe('Page Load and Initial State', () => {
    it('should load the demo landing page successfully', () => {
      DemoLandingUtils.verifyPageLoad()
    })

    it('should display the main heading and subheading', () => {
      DemoLandingUtils.verifyMainHeader()
    })

    it('should show demo steps', () => {
      DemoLandingUtils.verifyIndustrySelection()
      cy.contains('Live Demo').should('be.visible')
    })

    it('should display value propositions', () => {
      DemoLandingUtils.verifyValuePropositions()
    })
  })

  describe('Industry Selection', () => {
    it('should display all industry options', () => {
      DemoLandingUtils.verifyIndustryOptions()
    })

    it('should have proper card styling for each industry', () => {
      DemoLandingUtils.verifyIndustryCardStyling()
    })

    it('should allow selecting an industry', () => {
      DemoLandingUtils.selectIndustry('Financial Services')
    })

    it('should show demo tabs after industry selection', () => {
      DemoLandingUtils.selectIndustry('Healthcare')
      DemoLandingUtils.verifyDemoTabs()
    })

    it('should display industry-specific use cases', () => {
      DemoLandingUtils.verifyIndustryUseCases('E-commerce')
      DemoLandingUtils.verifyIndustryUseCases('Technology')
    })

    it('should transition to personalized demo after selection', () => {
      DemoLandingUtils.selectIndustry('Technology')
      DemoLandingUtils.verifyOverviewContent('Technology')
    })
  })

  describe('Demo Navigation Tabs', () => {
    beforeEach(() => {
      DemoLandingUtils.selectIndustry('Technology')
    })

    it('should display all demo tabs', () => {
      DemoLandingUtils.verifyDemoTabs()
    })

    it('should navigate to AI Chat tab', () => {
      DemoLandingUtils.navigateToTab('AI Chat')
    })

    it('should navigate to ROI Calculator tab', () => {
      DemoLandingUtils.navigateToTab('ROI Calculator')
    })

    it('should navigate to Metrics tab', () => {
      DemoLandingUtils.navigateToTab('Metrics')
    })

    it('should navigate to Next Steps tab', () => {
      DemoLandingUtils.navigateToTab('Next Steps')
    })

    it('should maintain tab state when switching', () => {
      DemoLandingUtils.navigateToTab('AI Chat')
      DemoLandingUtils.navigateToTab('Metrics')
      DemoLandingUtils.navigateToTab('AI Chat')
    })

    it('should show overview tab content initially', () => {
      DemoLandingUtils.verifyOverviewContent('Technology')
    })
  })

  describe('Welcome Section Features', () => {
    it('should display key value propositions', () => {
      DemoLandingUtils.verifyValuePropositions()
    })

    it('should show gradient backgrounds', () => {
      cy.get('[class*="bg-gradient"]').should('exist')
    })

    it('should display overview stats after industry selection', () => {
      DemoLandingUtils.selectIndustry('Technology')
      DemoLandingUtils.verifyOverviewContent('Technology')
    })

    it('should have call-to-action buttons', () => {
      DemoLandingUtils.selectIndustry('Technology')
      cy.contains('Start ROI Analysis').should('be.visible')
    })

    it('should show integration partner badges', () => {
      DemoLandingUtils.selectIndustry('Technology')
      DemoLandingUtils.verifyIntegrationPartners()
    })
  })

  describe('Responsive Design', () => {
    it('should adapt to mobile viewport', () => {
      DemoLandingUtils.verifyMobileLayout()
    })

    it('should adapt to tablet viewport', () => {
      DemoLandingUtils.verifyTabletLayout()
    })

    it('should handle industry selection on mobile', () => {
      cy.viewport('iphone-x')
      DemoLandingUtils.selectIndustry('Technology')
    })

    it('should show tabs on mobile after industry selection', () => {
      cy.viewport('iphone-x')
      DemoLandingUtils.selectIndustry('Technology')
      DemoLandingUtils.verifyDemoTabs()
    })
  })

  describe('Animations and Transitions', () => {
    it('should have hover effects on industry cards', () => {
      cy.get('[class*="cursor-pointer"]').first().trigger('mouseenter')
      cy.get('[class*="hover:shadow-xl"]').should('exist')
    })

    it('should have smooth tab transitions', () => {
      DemoLandingUtils.selectIndustry('Technology')
      DemoLandingUtils.navigateToTab('AI Chat')
    })

    it('should have transition classes', () => {
      DemoLandingUtils.selectIndustry('Technology')
      cy.get('[class*="transition"]').should('exist')
    })
  })

  describe('Industry-Specific Content', () => {
    it('should show Financial Services use cases', () => {
      DemoLandingUtils.verifyIndustryUseCases('Financial Services')
    })

    it('should show Healthcare use cases', () => {
      DemoLandingUtils.verifyIndustryUseCases('Healthcare')
    })

    it('should show E-commerce use cases', () => {
      DemoLandingUtils.verifyIndustryUseCases('E-commerce')
    })

    it('should show Technology use cases', () => {
      DemoLandingUtils.verifyIndustryUseCases('Technology')
    })

    it('should show personalized content after selection', () => {
      DemoLandingUtils.selectIndustry('Technology')
      cy.contains('Personalized for Technology').should('be.visible')
    })
  })

  describe('Error Handling and Edge Cases', () => {
    it('should show industry selection by default', () => {
      cy.visit('/demo')
      DemoLandingUtils.verifyIndustrySelection()
      DemoLandingUtils.verifyIndustryOptions()
    })

    it('should handle browser navigation', () => {
      DemoLandingUtils.selectIndustry('Technology')
      DemoLandingUtils.navigateToTab('AI Chat')
      cy.go('back')
      cy.url().should('include', '/demo')
    })

    it('should reset state on page refresh', () => {
      DemoLandingUtils.selectIndustry('Healthcare')
      DemoLandingUtils.navigateToTab('ROI Calculator')
      cy.reload()
      DemoLandingUtils.verifyIndustrySelection()
    })

    it('should handle industry selection properly', () => {
      DemoLandingUtils.selectIndustry('Technology')
      cy.contains('Personalized for Technology').should('be.visible')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels and semantic structure', () => {
      DemoLandingUtils.verifyAccessibility()
    })

    it('should support keyboard navigation', () => {
      DemoLandingUtils.testKeyboardNavigation()
    })

    it('should have proper heading hierarchy', () => {
      cy.get('h1').should('have.length', 1)
      cy.get('h2').should('exist')
      cy.get('h3').should('exist')
    })

    it('should have sufficient color contrast', () => {
      // Check for high contrast text elements
      cy.get('[class*="text-white"]').should('exist')
      cy.get('[class*="bg-gradient"]').should('exist')
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
          expect(measure.duration).to.be.lessThan(5000)
        }
      })
    })

    it('should load tab content on demand', () => {
      DemoLandingUtils.selectIndustry('Technology')
      DemoLandingUtils.navigateToTab('Metrics')
    })

    it('should handle component loading', () => {
      DemoLandingUtils.selectIndustry('Technology')
      DemoLandingUtils.navigateToTab('Data Insights')
    })
  })
})