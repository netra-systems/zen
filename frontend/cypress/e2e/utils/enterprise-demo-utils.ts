/// <reference types="cypress" />

/**
 * Enterprise Demo Test Utilities
 * 
 * BVJ: Enterprise segment - Shared testing utilities for step-based interactive enterprise demo
 * Supports sales process validation and interactive demo flow testing
 * 
 * Business Value:
 * - Reduces test maintenance overhead for step-based demo flow
 * - Ensures consistent enterprise demo testing across multi-step process
 * - Supports sales team interactive demo validation
 * - Validates enterprise conversion pipeline through demo experience
 */

export class EnterpriseDemoUtils {
  /**
   * Setup enterprise demo page with optimal viewport
   */
  static setupDemoPage(): void {
    cy.viewport(1920, 1080)
    cy.visit('/enterprise-demo')
  }

  /**
   * Verify page load basics - step-based demo
   */
  static verifyPageLoad(): void {
    cy.url().should('include', '/enterprise-demo')
    cy.contains('Netra AI Optimization Platform').should('be.visible')
    cy.contains('Enterprise Demo').should('be.visible')
  }

  /**
   * Verify welcome screen content and metrics
   */
  static verifyWelcomeScreen(): void {
    cy.contains('Experience AI Optimization in Action').should('be.visible')
    cy.contains('Annual Savings').should('be.visible')
    cy.contains('Faster Response').should('be.visible')
    cy.contains('Uptime SLA').should('be.visible')
    cy.contains('Start Interactive Demo').should('be.visible')
  }

  /**
   * Start the interactive demo from welcome screen
   */
  static startInteractiveDemo(): void {
    cy.contains('Start Interactive Demo').click()
    cy.contains('Select Workload').should('be.visible')
  }

  /**
   * Select a workload and proceed to generation step
   */
  static selectWorkload(workloadType: string = 'ecommerce'): void {
    // Wait for workload options to be visible
    cy.get('[data-testid="workload-option"]', { timeout: 10000 }).should('be.visible')
    // Click the first workload option or specific type
    if (workloadType === 'ecommerce') {
      cy.get('[data-testid="workload-option"]').first().click()
    } else {
      cy.contains(workloadType).click()
    }
  }

  /**
   * Wait for and verify generating screen
   */
  static verifyGeneratingScreen(): void {
    cy.contains('Generating synthetic workload data', { timeout: 15000 }).should('be.visible')
    cy.get('.animate-spin', { timeout: 10000 }).should('be.visible')
  }

  /**
   * Wait for and verify analyzing screen
   */
  static verifyAnalyzingScreen(): void {
    cy.contains('Analyzing workload patterns', { timeout: 20000 }).should('be.visible')
    cy.get('.animate-pulse', { timeout: 10000 }).should('be.visible')
  }

  /**
   * Wait for and verify results screen
   */
  static verifyResultsScreen(): void {
    cy.contains('Optimization Complete', { timeout: 25000 }).should('be.visible')
    cy.contains('Cost Reduction').should('be.visible')
    cy.contains('Response Time').should('be.visible')
    cy.contains('Reliability').should('be.visible')
    cy.contains('GPU Utilization').should('be.visible')
  }

  /**
   * Verify demo progress steps in header
   */
  static verifyDemoProgressSteps(): void {
    cy.contains('Select Workload').should('be.visible')
    cy.contains('Generate Data').should('be.visible')
    cy.contains('Analyze & Optimize').should('be.visible')
    cy.contains('View Results').should('be.visible')
  }

  /**
   * Complete full demo flow from start to results
   */
  static completeFullDemoFlow(workloadType: string = 'ecommerce'): void {
    this.verifyWelcomeScreen()
    this.startInteractiveDemo()
    this.selectWorkload(workloadType)
    this.verifyGeneratingScreen()
    this.verifyAnalyzingScreen()
    this.verifyResultsScreen()
  }

  /**
   * Verify agent status panel appears during processing
   */
  static verifyAgentStatusPanel(): void {
    // Agent status panel should appear when processing
    cy.get('[data-testid="agent-status-panel"]', { timeout: 15000 }).should('be.visible')
  }

  /**
   * Wait for demo step transition with timeout
   */
  static waitForStepTransition(targetStep: string, timeout: number = 15000): void {
    cy.contains(targetStep, { timeout }).should('be.visible')
  }

  /**
   * Test mobile responsiveness setup
   */
  static setupMobileView(): void {
    cy.viewport('iphone-x')
  }

  /**
   * Track analytics event
   */
  static trackAnalyticsEvent(eventName: string): void {
    cy.window().then(win => {
      const initialLength = win.dataLayer?.length || 0
      return initialLength
    }).as('initialAnalytics')
  }

  /**
   * Verify analytics tracking
   */
  static verifyAnalyticsTracking(): void {
    cy.window().then(win => {
      expect(win.dataLayer).to.exist
    })
  }

  /**
   * Check performance timing
   */
  static verifyPerformanceTiming(): void {
    cy.visit('/enterprise-demo', {
      onBeforeLoad: (win) => {
        win.performance.mark('start')
      },
      onLoad: (win) => {
        win.performance.mark('end')
        win.performance.measure('load', 'start', 'end')
        const measure = win.performance.getEntriesByType('measure')[0]
        expect(measure.duration).to.be.lessThan(4000)
      }
    })
  }

  /**
   * Test keyboard navigation
   */
  static testKeyboardNavigation(): void {
    cy.get('body').tab()
    cy.focused().should('have.attr', 'href').or('have.attr', 'type', 'button')
  }

  /**
   * Verify ARIA accessibility
   */
  static verifyARIALabels(minCount: number = 5): void {
    cy.get('button[aria-label]').should('have.length.at.least', minCount)
  }
}

/**
 * Enterprise Demo Constants
 */
export const ENTERPRISE_DEMO_CONSTANTS = {
  DEMO_STEPS: ['Select Workload', 'Generate Data', 'Analyze & Optimize', 'View Results'],
  WORKLOAD_TYPES: ['E-commerce', 'Healthcare', 'Financial Services', 'Manufacturing'],
  METRICS: {
    ANNUAL_SAVINGS: '$2.4M',
    PERFORMANCE: '3.2x',
    UPTIME: '99.9%'
  },
  RESULTS_METRICS: {
    COST_REDUCTION: '42%',
    MONTHLY_SAVINGS: '$124K',
    RESPONSE_TIME: '3.2x',
    LATENCY_IMPROVEMENT: '62ms → 19ms p50',
    RELIABILITY: '99.9%',
    GPU_UTILIZATION: '85%'
  }
}

/**
 * Enterprise Demo Selectors
 */
export const ENTERPRISE_SELECTORS = {
  demoHeader: '[data-testid="demo-header"]',
  welcomeScreen: '[data-testid="welcome-screen"]',
  workloadOption: '[data-testid="workload-option"]',
  progressSteps: '[data-testid="progress-steps"]',
  generatingScreen: '[data-testid="generating-screen"]',
  analyzingScreen: '[data-testid="analyzing-screen"]',
  resultsScreen: '[data-testid="results-screen"]',
  agentStatusPanel: '[data-testid="agent-status-panel"]',
  startDemoButton: 'button:contains("Start Interactive Demo")',
  metricsDisplay: '[data-testid="metrics-display"]',
  loadingSpinner: '.animate-spin',
  pulseAnimation: '.animate-pulse'
}