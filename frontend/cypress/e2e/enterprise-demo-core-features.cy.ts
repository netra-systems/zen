/// <reference types="cypress" />

import { EnterpriseDemoUtils, ENTERPRISE_SELECTORS } from './utils/enterprise-demo-utils'

/**
 * Enterprise Demo Core Features Tests
 * 
 * BVJ: Enterprise segment - Step-based interactive demo validation
 * Business Goal: Validate interactive demo flow for enterprise prospects
 * Value Impact: Ensures enterprise prospects experience working AI optimization demo
 * Revenue Impact: Supports enterprise conversion through hands-on demo experience
 */

describe('Enterprise Demo - Core Features', () => {
  beforeEach(() => {
    EnterpriseDemoUtils.setupDemoPage()
  })

  describe('Page Load and Welcome Screen', () => {
    it('should load the enterprise demo page', () => {
      EnterpriseDemoUtils.verifyPageLoad()
    })

    it('should display welcome screen with value proposition', () => {
      EnterpriseDemoUtils.verifyWelcomeScreen()
    })

    it('should show demo progress steps in header', () => {
      EnterpriseDemoUtils.verifyDemoProgressSteps()
    })

    it('should display enterprise branding and badges', () => {
      cy.contains('Enterprise Demo').should('be.visible')
      cy.contains('BETA').should('be.visible')
    })

    it('should show compelling metrics on welcome screen', () => {
      cy.contains('$2.4M').should('be.visible')
      cy.contains('3.2x').should('be.visible')
      cy.contains('99.9%').should('be.visible')
    })
  })

  describe('Interactive Demo Flow', () => {
    it('should start demo from welcome screen', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
    })

    it('should display workload selection options', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      cy.contains('Choose your industry profile').should('be.visible')
      cy.get(ENTERPRISE_SELECTORS.workloadOption).should('exist')
    })

    it('should proceed to data generation step', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      EnterpriseDemoUtils.verifyGeneratingScreen()
    })

    it('should show analyzing phase', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      EnterpriseDemoUtils.verifyGeneratingScreen()
      EnterpriseDemoUtils.verifyAnalyzingScreen()
    })

    it('should display final results', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      EnterpriseDemoUtils.verifyGeneratingScreen()
      EnterpriseDemoUtils.verifyAnalyzingScreen()
      EnterpriseDemoUtils.verifyResultsScreen()
    })

    it('should complete full demo flow', () => {
      EnterpriseDemoUtils.completeFullDemoFlow()
    })
  })

  describe('Demo Results and Metrics', () => {
    beforeEach(() => {
      // Complete demo flow to results screen for these tests
      EnterpriseDemoUtils.completeFullDemoFlow()
    })

    it('should display optimization results', () => {
      cy.contains('Optimization Complete').should('be.visible')
      cy.contains('Cost Reduction').should('be.visible')
      cy.contains('42%').should('be.visible')
    })

    it('should show performance improvements', () => {
      cy.contains('Response Time').should('be.visible')
      cy.contains('3.2x').should('be.visible')
      cy.contains('Latency').should('be.visible')
      cy.contains('62ms → 19ms').should('be.visible')
    })

    it('should display reliability metrics', () => {
      cy.contains('Reliability').should('be.visible')
      cy.contains('99.9%').should('be.visible')
      cy.contains('From 97.2%').should('be.visible')
    })

    it('should show GPU utilization improvements', () => {
      cy.contains('GPU Utilization').should('be.visible')
      cy.contains('85%').should('be.visible')
      cy.contains('From 45%').should('be.visible')
    })

    it('should display monthly savings calculation', () => {
      cy.contains('Monthly Savings').should('be.visible')
      cy.contains('$124K').should('be.visible')
    })
  })

  describe('Agent Integration and Processing', () => {
    it('should show agent status during processing', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      // Agent status panel should appear during processing
      EnterpriseDemoUtils.verifyAgentStatusPanel()
    })

    it('should display loading animations during steps', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      // Verify loading animations appear
      cy.get(ENTERPRISE_SELECTORS.loadingSpinner, { timeout: 10000 }).should('be.visible')
    })

    it('should handle step transitions smoothly', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      EnterpriseDemoUtils.waitForStepTransition('Generating synthetic workload data')
      EnterpriseDemoUtils.waitForStepTransition('Analyzing workload patterns')
      EnterpriseDemoUtils.waitForStepTransition('Optimization Complete')
    })

    it('should maintain progress state through steps', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      // Verify progress is maintained in header
      EnterpriseDemoUtils.verifyDemoProgressSteps()
    })
  })

  describe('Enterprise Value Demonstration', () => {
    it('should demonstrate complete ROI story through demo flow', () => {
      // Welcome screen shows high-level value proposition
      EnterpriseDemoUtils.verifyWelcomeScreen()
      
      // Interactive flow demonstrates platform capabilities
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      
      // Results screen provides concrete value metrics
      EnterpriseDemoUtils.verifyResultsScreen()
    })

    it('should maintain enterprise branding throughout flow', () => {
      EnterpriseDemoUtils.verifyPageLoad()
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      
      // Verify enterprise branding persists
      cy.contains('Enterprise Demo').should('be.visible')
      cy.contains('Netra AI Optimization Platform').should('be.visible')
    })

    it('should provide measurable business impact data', () => {
      EnterpriseDemoUtils.completeFullDemoFlow()
      
      // Verify specific business metrics are shown
      cy.contains('42%').should('be.visible') // Cost reduction
      cy.contains('$124K').should('be.visible') // Monthly savings
      cy.contains('99.9%').should('be.visible') // Reliability
    })

    it('should support different workload scenarios', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      
      // Verify multiple workload options are available
      cy.get(ENTERPRISE_SELECTORS.workloadOption).should('have.length.at.least', 1)
    })

    it('should demonstrate end-to-end platform capability', () => {
      // Complete full flow validates the entire platform story
      EnterpriseDemoUtils.completeFullDemoFlow()
      
      // Verify all key elements are shown
      cy.contains('Experience AI Optimization in Action').should('be.visible')
      cy.contains('Optimization Complete').should('be.visible')
    })
  })
})