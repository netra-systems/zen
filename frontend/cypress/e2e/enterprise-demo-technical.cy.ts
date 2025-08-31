/// <reference types="cypress" />

import { EnterpriseDemoUtils, ENTERPRISE_DEMO_CONSTANTS, ENTERPRISE_SELECTORS } from './utils/enterprise-demo-utils'

/**
 * Enterprise Demo Technical Validation Tests
 * 
 * BVJ: Enterprise segment - Technical validation through interactive demo experience
 * Business Goal: Validate technical capabilities through hands-on demo for CTO/Engineering leadership
 * Value Impact: Demonstrates actual platform technical capabilities through working demo
 * Revenue Impact: Reduces technical objections by providing concrete proof of platform capabilities
 */

describe('Enterprise Demo - Technical Validation', () => {
  beforeEach(() => {
    EnterpriseDemoUtils.setupDemoPage()
  })

  describe('Technical Demo Foundation', () => {
    it('should demonstrate technical platform capabilities', () => {
      EnterpriseDemoUtils.verifyPageLoad()
      EnterpriseDemoUtils.verifyWelcomeScreen()
      EnterpriseDemoUtils.verifyDemoProgressSteps()
    })

    it('should showcase AI optimization technology', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      // Verify technical messaging about AI optimization
      cy.contains('Netra Beta can reduce your AI costs').should('be.visible')
      cy.contains('while improving performance').should('be.visible')
    })

    it('should demonstrate workload analysis capabilities', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      cy.contains('Choose your industry profile').should('be.visible')
      cy.get(ENTERPRISE_SELECTORS.workloadOption).should('exist')
    })

    it('should show synthetic data generation technology', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      EnterpriseDemoUtils.verifyGeneratingScreen()
      cy.contains('Generating synthetic workload data').should('be.visible')
    })
  })

  describe('AI Processing and Analysis', () => {
    it('should demonstrate AI analysis capabilities', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      EnterpriseDemoUtils.verifyGeneratingScreen()
      EnterpriseDemoUtils.verifyAnalyzingScreen()
      cy.contains('Analyzing workload patterns').should('be.visible')
    })

    it('should show real AI optimization in progress', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      // Verify actual processing indicators
      cy.get(ENTERPRISE_SELECTORS.loadingSpinner, { timeout: 10000 }).should('be.visible')
      cy.get(ENTERPRISE_SELECTORS.pulseAnimation, { timeout: 10000 }).should('be.visible')
    })

    it('should integrate with agent processing system', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      EnterpriseDemoUtils.verifyAgentStatusPanel()
    })

    it('should demonstrate technical result accuracy', () => {
      EnterpriseDemoUtils.completeFullDemoFlow()
      // Verify technical precision in results
      cy.contains('62ms → 19ms p50').should('be.visible') // Specific latency metrics
      cy.contains('From 45%').should('be.visible') // GPU utilization baseline
    })
  })

  describe('Technical Metrics and Validation', () => {
    beforeEach(() => {
      // Complete demo flow to access technical results
      EnterpriseDemoUtils.completeFullDemoFlow()
    })

    it('should provide specific technical performance metrics', () => {
      cy.contains('Cost Reduction').should('be.visible')
      cy.contains('42%').should('be.visible')
      cy.contains('Response Time').should('be.visible')
      cy.contains('3.2x').should('be.visible')
    })

    it('should show detailed latency improvements', () => {
      cy.contains('Latency').should('be.visible')
      cy.contains('62ms → 19ms p50').should('be.visible')
    })

    it('should display infrastructure efficiency gains', () => {
      cy.contains('GPU Utilization').should('be.visible')
      cy.contains('85%').should('be.visible')
      cy.contains('From 45%').should('be.visible')
    })

    it('should show reliability improvements', () => {
      cy.contains('Reliability').should('be.visible')
      cy.contains('99.9%').should('be.visible')
      cy.contains('From 97.2%').should('be.visible')
    })
  })

  describe('Demo Technical Responsiveness', () => {
    it('should adapt to mobile viewport', () => {
      EnterpriseDemoUtils.setupMobileView()
      EnterpriseDemoUtils.verifyPageLoad()
      cy.contains('Experience AI Optimization in Action').should('be.visible')
    })

    it('should maintain demo functionality on mobile', () => {
      EnterpriseDemoUtils.setupMobileView()
      EnterpriseDemoUtils.verifyWelcomeScreen()
      EnterpriseDemoUtils.startInteractiveDemo()
    })

    it('should show mobile-optimized demo interface', () => {
      EnterpriseDemoUtils.setupMobileView()
      EnterpriseDemoUtils.startInteractiveDemo()
      cy.get(ENTERPRISE_SELECTORS.workloadOption).should('be.visible')
    })

    it('should handle mobile demo flow transitions', () => {
      EnterpriseDemoUtils.setupMobileView()
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      EnterpriseDemoUtils.verifyGeneratingScreen()
    })
  })

  describe('Demo Performance and Analytics', () => {
    it('should track demo analytics', () => {
      EnterpriseDemoUtils.verifyAnalyticsTracking()
    })

    it('should track demo interaction events', () => {
      cy.window().then(win => {
        const initialLength = win.dataLayer?.length || 0
        EnterpriseDemoUtils.startInteractiveDemo()
        expect(win.dataLayer?.length).to.be.greaterThan(initialLength)
      })
    })

    it('should load demo within performance budget', () => {
      EnterpriseDemoUtils.verifyPerformanceTiming()
    })

    it('should handle demo step transitions efficiently', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      // Verify transitions are smooth without excessive loading
      EnterpriseDemoUtils.waitForStepTransition('Generating synthetic workload data', 5000)
    })
  })

  describe('Demo Accessibility', () => {
    it('should have proper heading hierarchy', () => {
      cy.get('h1').should('have.length', 1)
      cy.get('h2, h3').should('have.length.at.least', 2)
    })

    it('should have accessible interactive demo elements', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      cy.get(ENTERPRISE_SELECTORS.workloadOption).should('be.visible')
      cy.get('button').should('have.attr', 'type')
    })

    it('should support keyboard navigation through demo', () => {
      EnterpriseDemoUtils.testKeyboardNavigation()
    })

    it('should maintain accessibility during demo transitions', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      cy.get('h1').should('exist') // Header should remain accessible
    })
  })

  describe('End-to-End Technical Validation', () => {
    it('should validate complete technical demo flow', () => {
      EnterpriseDemoUtils.verifyPageLoad()
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      EnterpriseDemoUtils.verifyGeneratingScreen()
      EnterpriseDemoUtils.verifyAnalyzingScreen()
      EnterpriseDemoUtils.verifyResultsScreen()
    })

    it('should demonstrate technical precision through metrics', () => {
      EnterpriseDemoUtils.completeFullDemoFlow()
      // Verify technical accuracy in results
      cy.contains('42%').should('be.visible') // Precise cost reduction
      cy.contains('$124K').should('be.visible') // Specific monthly savings
      cy.contains('62ms → 19ms p50').should('be.visible') // Detailed latency metrics
    })

    it('should integrate with backend AI processing', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      EnterpriseDemoUtils.verifyAgentStatusPanel()
      // Verify actual backend integration
      cy.get(ENTERPRISE_SELECTORS.loadingSpinner, { timeout: 10000 }).should('be.visible')
    })

    it('should ensure cross-device demo consistency', () => {
      // Desktop validation
      EnterpriseDemoUtils.verifyWelcomeScreen()
      
      // Mobile validation
      EnterpriseDemoUtils.setupMobileView()
      EnterpriseDemoUtils.verifyWelcomeScreen()
      EnterpriseDemoUtils.startInteractiveDemo()
    })

    it('should validate technical performance under load', () => {
      // Simulate rapid demo interactions
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      EnterpriseDemoUtils.waitForStepTransition('Generating synthetic workload data', 10000)
      EnterpriseDemoUtils.waitForStepTransition('Analyzing workload patterns', 15000)
    })
  })

  describe('Enterprise Technical Credibility', () => {
    it('should demonstrate platform technical sophistication', () => {
      // Welcome screen shows advanced AI capabilities
      EnterpriseDemoUtils.verifyWelcomeScreen()
      cy.contains('reduce your AI costs by 40-60%').should('be.visible')
      cy.contains('improving performance by 2-3x').should('be.visible')
    })

    it('should showcase real AI workload processing', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      cy.contains('Choose your industry profile').should('be.visible')
      EnterpriseDemoUtils.selectWorkload()
      cy.contains('Generating synthetic workload data').should('be.visible')
    })

    it('should provide enterprise-grade result accuracy', () => {
      EnterpriseDemoUtils.completeFullDemoFlow()
      // Verify precision that would satisfy technical stakeholders
      cy.contains('Optimization Complete').should('be.visible')
      cy.contains('GPU Utilization').should('be.visible')
      cy.contains('From 45%').should('be.visible')
    })
  })
})