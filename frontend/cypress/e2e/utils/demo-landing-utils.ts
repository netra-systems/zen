/// <reference types="cypress" />

/**
 * Demo Landing Page Test Utilities
 * 
 * BVJ: Free segment - Core landing page functionality validation
 * Business Goal: Validate first-time user experience and conversion funnel
 * Value Impact: Ensures Free users have smooth demo experience leading to paid tier conversion
 * Revenue Impact: Supports Free-to-paid conversion pipeline
 */

export class DemoLandingUtils {
  /**
   * Setup demo page with optimal viewport for desktop
   */
  static setupDemoPage(): void {
    cy.viewport(1920, 1080)
    cy.visit('/demo')
  }

  /**
   * Verify page load basics
   */
  static verifyPageLoad(): void {
    cy.url().should('include', '/demo')
    cy.contains('Enterprise AI Optimization Platform Beta').should('be.visible')
  }

  /**
   * Verify main header content is displayed
   */
  static verifyMainHeader(): void {
    cy.contains('Enterprise AI Optimization Platform Beta').should('be.visible')
    cy.contains('Reduce costs by 40-60% while improving performance by 2-3x').should('be.visible')
    cy.contains('Live Demo').should('be.visible')
  }

  /**
   * Verify value proposition cards are displayed
   */
  static verifyValuePropositions(): void {
    // Check for Card components with border class
    cy.get('[class*="border"]').within(() => {
      cy.contains('40-60% Cost Reduction').should('be.visible')
    })
    cy.get('[class*="border"]').within(() => {
      cy.contains('2-3x Performance Gain').should('be.visible')  
    })
    cy.get('[class*="border"]').within(() => {
      cy.contains('Enterprise Security').should('be.visible')
    })
  }

  /**
   * Verify industry selection card is displayed
   */
  static verifyIndustrySelection(): void {
    cy.contains('Select Your Industry').should('be.visible')
    cy.contains('Customize the demo experience for your specific sector').should('be.visible')
  }

  /**
   * Verify all industry options are visible
   */
  static verifyIndustryOptions(): void {
    const industries = ['Financial Services', 'Healthcare', 'E-commerce', 'Manufacturing', 'Technology', 'Government & Defense']
    industries.forEach(industry => {
      cy.contains(industry).should('be.visible')
    })
  }

  /**
   * Select an industry and verify transition to demo tabs
   */
  static selectIndustry(industry: string): void {
    cy.contains(industry).click()
    // Verify demo tabs appear after industry selection
    cy.get('[role="tablist"]').should('be.visible')
  }

  /**
   * Verify demo tabs are displayed after industry selection
   */
  static verifyDemoTabs(): void {
    const tabs = ['Overview', 'ROI Calculator', 'AI Chat', 'Metrics', 'Data Insights', 'Next Steps']
    tabs.forEach(tab => {
      cy.contains(tab).should('be.visible')
    })
  }

  /**
   * Verify overview tab content after industry selection
   */
  static verifyOverviewContent(selectedIndustry: string): void {
    cy.contains('Welcome to Netra AI Optimization Platform').should('be.visible')
    cy.contains(`Personalized for ${selectedIndustry}`).should('be.visible')
    
    // Check quick stats
    cy.contains('2,500+').should('be.visible') // Active Customers
    cy.contains('10B+/month').should('be.visible') // Requests Optimized
    cy.contains('380%').should('be.visible') // Average ROI
    
    // Check for call-to-action button
    cy.contains('Start ROI Analysis').should('be.visible')
  }

  /**
   * Navigate to a specific demo tab
   */
  static navigateToTab(tabName: string): void {
    cy.contains(tabName).click()
    cy.get('[role="tabpanel"]').should('be.visible')
  }

  /**
   * Verify industry-specific use cases are displayed in selection cards
   */
  static verifyIndustryUseCases(industry: string): void {
    const useCases = {
      'Financial Services': ['Fraud Detection', 'Risk Analysis', 'Trading Algorithms', 'Customer Service'],
      'Healthcare': ['Diagnostic AI', 'Drug Discovery', 'Patient Care', 'Medical Imaging'],
      'E-commerce': ['Recommendations', 'Search', 'Inventory', 'Customer Support'],
      'Technology': ['Code Generation', 'DevOps AI', 'Product Analytics', 'Content Creation']
    }

    if (useCases[industry]) {
      cy.contains(industry).parent().within(() => {
        useCases[industry].forEach(useCase => {
          cy.contains(useCase).should('be.visible')
        })
      })
    }
  }

  /**
   * Verify responsive design on mobile viewport
   */
  static verifyMobileLayout(): void {
    cy.viewport('iphone-x')
    cy.contains('Enterprise AI Optimization Platform Beta').should('be.visible')
    cy.contains('Financial Services').should('be.visible')
  }

  /**
   * Verify responsive design on tablet viewport
   */
  static verifyTabletLayout(): void {
    cy.viewport('ipad-2')
    cy.contains('Enterprise AI Optimization Platform Beta').should('be.visible')
    cy.contains('Financial Services').should('be.visible')
  }

  /**
   * Verify industry cards have proper hover effects and styling
   */
  static verifyIndustryCardStyling(): void {
    // Check for card-based layout with hover effects
    cy.get('[class*="cursor-pointer"]').should('have.length.at.least', 6)
    cy.get('[class*="hover:shadow-xl"]').should('exist')
  }

  /**
   * Verify proper accessibility elements
   */
  static verifyAccessibility(): void {
    cy.get('[aria-label]').should('have.length.at.least', 3)
    cy.get('h1').should('have.length', 1)
    cy.get('h2').should('exist')
    cy.get('h3').should('exist')
  }

  /**
   * Test keyboard navigation
   */
  static testKeyboardNavigation(): void {
    cy.get('body').tab()
    cy.focused().should('exist')
  }

  /**
   * Verify integration partner badges
   */
  static verifyIntegrationPartners(): void {
    const partners = ['OpenAI', 'Anthropic', 'AWS', 'Azure', 'GCP', 'Kubernetes']
    partners.forEach(partner => {
      cy.contains(partner).should('be.visible')
    })
  }
}

export const DEMO_LANDING_SELECTORS = {
  // Card-based selectors matching current UI
  valuePropositionCards: '[class*="border"]',
  industryCards: '[class*="cursor-pointer"]',
  demoTabs: '[role="tablist"]',
  tabPanels: '[role="tabpanel"]',
  
  // Button selectors
  primaryButtons: 'button[class*="px-4"]',
  startRoiButton: 'button:contains("Start ROI Analysis")',
  
  // Content selectors
  mainTitle: 'h1',
  industrySelection: '[class*="grid"][class*="gap"]',
  quickStats: '[class*="space-y"]'
} as const