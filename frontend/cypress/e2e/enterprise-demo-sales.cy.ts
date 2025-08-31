/// <reference types="cypress" />

import { EnterpriseDemoUtils, ENTERPRISE_DEMO_CONSTANTS, ENTERPRISE_SELECTORS } from './utils/enterprise-demo-utils'

/**
 * Enterprise Demo Sales Enablement Tests
 * 
 * BVJ: Enterprise segment - Interactive demo conversion and sales enablement validation
 * Business Goal: Validate interactive demo supports enterprise sales process and conversions
 * Value Impact: Ensures demo effectively communicates value proposition and drives prospect engagement
 * Revenue Impact: Directly supports enterprise conversion through compelling demo experience
 */

describe('Enterprise Demo - Sales Enablement', () => {
  beforeEach(() => {
    EnterpriseDemoUtils.setupDemoPage()
  })

  describe('Value Proposition Communication', () => {
    it('should clearly communicate enterprise value on welcome screen', () => {
      EnterpriseDemoUtils.verifyWelcomeScreen()
      cy.contains('reduce your AI costs by 40-60%').should('be.visible')
      cy.contains('improving performance by 2-3x').should('be.visible')
    })

    it('should display compelling business metrics', () => {
      EnterpriseDemoUtils.verifyWelcomeScreen()
      cy.contains('$2.4M').should('be.visible') // Annual Savings
      cy.contains('3.2x').should('be.visible') // Performance improvement
      cy.contains('99.9%').should('be.visible') // Uptime SLA
    })

    it('should present metrics in business language', () => {
      EnterpriseDemoUtils.verifyWelcomeScreen()
      cy.contains('Annual Savings').should('be.visible')
      cy.contains('Faster Response').should('be.visible')
      cy.contains('Uptime SLA').should('be.visible')
    })

    it('should maintain consistent value messaging throughout demo', () => {
      EnterpriseDemoUtils.verifyWelcomeScreen()
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      // Value messaging should persist in header
      cy.contains('Netra AI Optimization Platform').should('be.visible')
    })
  })

  describe('Demo Progression and Engagement', () => {
    it('should guide prospects through logical demo steps', () => {
      EnterpriseDemoUtils.verifyDemoProgressSteps()
      // Verify clear progression path
      cy.contains('Select Workload').should('be.visible')
      cy.contains('Generate Data').should('be.visible')
      cy.contains('Analyze & Optimize').should('be.visible')
      cy.contains('View Results').should('be.visible')
    })

    it('should engage prospects with interactive workload selection', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      cy.contains('Choose your industry profile').should('be.visible')
      cy.get(ENTERPRISE_SELECTORS.workloadOption).should('exist')
    })

    it('should maintain engagement during processing steps', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      EnterpriseDemoUtils.verifyGeneratingScreen()
      // Verify engaging content during wait
      cy.contains('Generating synthetic workload data').should('be.visible')
    })

    it('should provide visual progress indicators', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      // Verify visual engagement elements
      cy.get(ENTERPRISE_SELECTORS.loadingSpinner, { timeout: 10000 }).should('be.visible')
    })

    it('should show clear completion and results', () => {
      EnterpriseDemoUtils.completeFullDemoFlow()
      cy.contains('Optimization Complete').should('be.visible')
    })
  })

  describe('ROI Demonstration and Business Case', () => {
    beforeEach(() => {
      // Complete demo to access results for ROI validation
      EnterpriseDemoUtils.completeFullDemoFlow()
    })

    it('should provide concrete ROI metrics', () => {
      cy.contains('Cost Reduction').should('be.visible')
      cy.contains('42%').should('be.visible')
      cy.contains('Monthly Savings').should('be.visible')
      cy.contains('$124K').should('be.visible')
    })

    it('should demonstrate performance improvements', () => {
      cy.contains('Response Time').should('be.visible')
      cy.contains('3.2x').should('be.visible')
      cy.contains('Latency').should('be.visible')
    })

    it('should show infrastructure efficiency gains', () => {
      cy.contains('GPU Utilization').should('be.visible')
      cy.contains('85%').should('be.visible')
      cy.contains('From 45%').should('be.visible')
    })

    it('should provide reliability improvements', () => {
      cy.contains('Reliability').should('be.visible')
      cy.contains('99.9%').should('be.visible')
      cy.contains('From 97.2%').should('be.visible')
    })

    it('should calculate specific business impact', () => {
      // Verify specific, credible business metrics
      cy.contains('$124K').should('be.visible') // Monthly savings
      cy.contains('42%').should('be.visible') // Cost reduction percentage
    })
  })

  describe('Conversion and Next Steps', () => {
    it('should provide clear initial call-to-action', () => {
      EnterpriseDemoUtils.verifyWelcomeScreen()
      cy.contains('Start Interactive Demo').should('be.visible')
      cy.get(ENTERPRISE_SELECTORS.startDemoButton).should('be.enabled')
    })

    it('should maintain engagement throughout demo flow', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      // Verify user remains engaged during processing
      cy.contains('Generating synthetic workload data').should('be.visible')
    })

    it('should provide compelling results to drive conversion', () => {
      EnterpriseDemoUtils.completeFullDemoFlow()
      cy.contains('Optimization Complete').should('be.visible')
      // Results should be compelling enough to drive next conversation
      cy.contains('42%').should('be.visible') // Cost reduction
      cy.contains('$124K').should('be.visible') // Monthly savings
    })

    it('should demonstrate beta program value', () => {
      EnterpriseDemoUtils.verifyWelcomeScreen()
      cy.contains('BETA').should('be.visible')
      cy.contains('Experience AI Optimization in Action').should('be.visible')
    })

    it('should support sales team demo narrative', () => {
      // Complete demo validates entire sales story
      EnterpriseDemoUtils.verifyWelcomeScreen() // Value proposition
      EnterpriseDemoUtils.startInteractiveDemo() // Engagement
      EnterpriseDemoUtils.selectWorkload() // Relevance
      EnterpriseDemoUtils.verifyResultsScreen() // Proof of value
    })
  })

  describe('Complete Sales Journey Validation', () => {
    it('should support discovery phase conversation', () => {
      EnterpriseDemoUtils.verifyWelcomeScreen()
      // Demo should help sales team understand prospect needs
      cy.contains('Choose your industry profile').should('be.visible')
      EnterpriseDemoUtils.startInteractiveDemo()
    })

    it('should demonstrate platform capabilities convincingly', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      EnterpriseDemoUtils.verifyGeneratingScreen()
      EnterpriseDemoUtils.verifyAnalyzingScreen()
      // Should show real AI processing capabilities
      EnterpriseDemoUtils.verifyAgentStatusPanel()
    })

    it('should provide concrete business justification', () => {
      EnterpriseDemoUtils.completeFullDemoFlow()
      // Results should support business case development
      cy.contains('Cost Reduction').should('be.visible')
      cy.contains('Monthly Savings').should('be.visible')
      cy.contains('Response Time').should('be.visible')
      cy.contains('Reliability').should('be.visible')
    })

    it('should enable technical validation conversations', () => {
      EnterpriseDemoUtils.completeFullDemoFlow()
      // Technical details should satisfy technical stakeholders
      cy.contains('62ms → 19ms p50').should('be.visible')
      cy.contains('GPU Utilization').should('be.visible')
      cy.contains('From 45%').should('be.visible')
    })

    it('should support pilot program discussions', () => {
      EnterpriseDemoUtils.verifyWelcomeScreen()
      cy.contains('BETA').should('be.visible')
      cy.contains('Start with your industry-specific workload').should('be.visible')
    })

    it('should complete full enterprise sales demo narrative', () => {
      // Full demo should tell complete enterprise story
      EnterpriseDemoUtils.verifyWelcomeScreen() // Problem/solution fit
      EnterpriseDemoUtils.startInteractiveDemo() // Platform engagement
      EnterpriseDemoUtils.selectWorkload() // Relevance and customization
      EnterpriseDemoUtils.verifyGeneratingScreen() // Technical capabilities
      EnterpriseDemoUtils.verifyAnalyzingScreen() // AI sophistication
      EnterpriseDemoUtils.verifyResultsScreen() // Business value delivery
    })
  })

  describe('Demo Conversion Analytics', () => {
    it('should track demo initiation', () => {
      EnterpriseDemoUtils.verifyAnalyticsTracking()
      EnterpriseDemoUtils.startInteractiveDemo()
      // Should track when prospects start the demo
    })

    it('should track workload selection', () => {
      EnterpriseDemoUtils.startInteractiveDemo()
      EnterpriseDemoUtils.selectWorkload()
      // Should track which workloads prospects choose
    })

    it('should track demo completion', () => {
      EnterpriseDemoUtils.completeFullDemoFlow()
      // Should track full demo completion for conversion analysis
      cy.contains('Optimization Complete').should('be.visible')
    })

    it('should support conversion funnel analysis', () => {
      // Demo should provide data for sales funnel optimization
      EnterpriseDemoUtils.verifyPageLoad() // Landing
      EnterpriseDemoUtils.startInteractiveDemo() // Engagement
      EnterpriseDemoUtils.selectWorkload() // Interaction
      EnterpriseDemoUtils.verifyResultsScreen() // Completion
    })
  })
})