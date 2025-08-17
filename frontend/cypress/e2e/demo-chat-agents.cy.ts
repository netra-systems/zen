/// <reference types="cypress" />

import {
  ChatNavigation,
  MessageInput,
  MessageAssertions,
  AgentProcessing,
  MetricsValidation,
  InsightsPanel,
  WaitHelpers
} from './utils/chat-test-helpers'

/**
 * Agent Processing and Business Features Tests
 * Tests AI agent interactions and business value demonstrations
 * Critical for showcasing value capture relative to customer AI spend
 */

describe('DemoChat Agent Processing & Business Features', () => {
  beforeEach(() => {
    ChatNavigation.setupTechnology()
  })

  describe('Agent Processing and Response', () => {
    it('should show agent processing indicators', () => {
      MessageInput.send('Analyze')
      AgentProcessing.assertProcessingIndicator()
    })

    it('should display multiple agent activations', () => {
      MessageInput.send('Complex analysis')
      AgentProcessing.assertAgentActivation()
    })

    it('should show agent names during processing', () => {
      MessageInput.send('Optimize')
      AgentProcessing.assertAgentNames()
    })

    it('should display agent response with formatting', () => {
      MessageInput.sendAndWait('Help me optimize')
      MessageAssertions.assertAssistantMessage()
      MessageAssertions.assertFormattedResponse()
    })

    it('should show processing time', () => {
      MessageInput.sendAndWait('Quick test')
      AgentProcessing.assertProcessingTime()
    })

    it('should display token usage', () => {
      MessageInput.sendAndWait('Analyze')
      AgentProcessing.assertTokenUsage()
    })
  })

  describe('Performance Metrics Display', () => {
    it('should show optimization metrics in response', () => {
      MessageInput.sendAndWait('Show optimization potential')
      MetricsValidation.assertCostSavings()
    })

    it('should display percentage improvements', () => {
      MessageInput.sendAndWait('Performance gains')
      MetricsValidation.assertPercentageGains()
    })

    it('should show latency reduction metrics', () => {
      MessageInput.sendAndWait('Reduce latency')
      MetricsValidation.assertLatencyMetrics()
    })

    it('should display implementation timeline', () => {
      MessageInput.sendAndWait('Implementation plan')
      MetricsValidation.assertTimeline()
    })

    it('should show ROI calculations', () => {
      MessageInput.sendAndWait('Calculate ROI for optimization')
      MetricsValidation.assertCostSavings()
      MetricsValidation.assertPercentageGains()
    })

    it('should display workload analysis results', () => {
      MessageInput.sendAndWait('Analyze my workload efficiency')
      cy.contains(/efficiency|utilization|performance/i).should('be.visible')
    })
  })

  describe('Optimization Insights Panel', () => {
    it('should display insights panel after analysis', () => {
      MessageInput.sendAndWait('Analyze my workload')
      InsightsPanel.assertVisible()
    })

    it('should show readiness score', () => {
      MessageInput.sendAndWait('Check optimization readiness')
      InsightsPanel.assertReadinessScore()
    })

    it('should display potential savings', () => {
      MessageInput.sendAndWait('Calculate savings')
      InsightsPanel.assertPotentialSavings()
      MetricsValidation.assertSavingsAmount()
    })

    it('should show quick actions', () => {
      MessageInput.sendAndWait('Show actions')
      InsightsPanel.assertQuickActions()
    })

    it('should provide upgrade recommendations', () => {
      MessageInput.sendAndWait('Recommend optimization tier')
      cy.contains(/Early|Mid|Enterprise/i).should('be.visible')
    })

    it('should show implementation complexity', () => {
      MessageInput.sendAndWait('How complex is implementation?')
      cy.contains(/simple|moderate|complex|expert/i).should('be.visible')
    })
  })

  describe('Industry-Specific Responses', () => {
    it('should provide Technology-specific optimization', () => {
      MessageInput.sendAndWait('Optimize code generation')
      cy.contains(/code|development|IDE/i).should('be.visible')
    })

    it('should reference Technology tools and frameworks', () => {
      MessageInput.sendAndWait('CI/CD pipeline')
      cy.contains(/Jenkins|GitHub|Docker|Kubernetes/i).should('be.visible')
    })

    it('should adapt to different industries', () => {
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Healthcare')
      MessageInput.sendAndWait('Optimize')
      cy.contains(/patient|diagnostic|medical/i).should('be.visible')
    })

    it('should provide industry-specific metrics', () => {
      MessageInput.sendAndWait('Show Technology industry benchmarks')
      cy.contains(/deployment|uptime|latency|throughput/i).should('be.visible')
    })

    it('should reference relevant compliance standards', () => {
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Healthcare')
      MessageInput.sendAndWait('Compliance requirements')
      cy.contains(/HIPAA|FDA|privacy/i).should('be.visible')
    })
  })

  describe('Business Value Demonstration', () => {
    it('should calculate cost savings for Free segment', () => {
      MessageInput.sendAndWait('What can I save as a startup?')
      cy.contains(/\$[\d,]+.*month/i).should('be.visible')
    })

    it('should show Early tier value proposition', () => {
      MessageInput.sendAndWait('Early tier benefits')
      cy.contains(/professional|support|advanced/i).should('be.visible')
    })

    it('should demonstrate Mid tier ROI', () => {
      MessageInput.sendAndWait('Mid tier return on investment')
      MetricsValidation.assertCostSavings()
      cy.contains(/team|scale|integration/i).should('be.visible')
    })

    it('should present Enterprise tier value', () => {
      MessageInput.sendAndWait('Enterprise optimization value')
      cy.contains(/enterprise|custom|dedicated/i).should('be.visible')
    })

    it('should show conversion incentives', () => {
      MessageInput.sendAndWait('Upgrade benefits')
      cy.contains(/upgrade|premium|unlock/i).should('be.visible')
    })

    it('should calculate AI spend optimization', () => {
      MessageInput.sendAndWait('My AI costs are $50k monthly, optimize')
      cy.contains(/50k|\$50,000/i).should('be.visible')
      MetricsValidation.assertPercentageGains()
    })
  })

  describe('Advanced Agent Orchestration', () => {
    it('should coordinate multiple agents for complex queries', () => {
      MessageInput.send('Analyze, optimize, and implement recommendations')
      AgentProcessing.assertAgentActivation()
      cy.get('[data-testid="agent-indicator"]').should('have.length.at.least', 2)
    })

    it('should show agent collaboration progress', () => {
      MessageInput.send('Complete system analysis')
      cy.contains(/analyzing|optimizing|recommending/i).should('be.visible')
    })

    it('should display agent decision reasoning', () => {
      MessageInput.sendAndWait('Why these recommendations?')
      cy.contains(/because|analysis shows|based on/i).should('be.visible')
    })

    it('should handle agent failures gracefully', () => {
      cy.intercept('POST', '/api/agents/**', { statusCode: 500 })
      MessageInput.send('Analyze')
      cy.contains(/fallback|alternative|retry/i).should('be.visible')
    })

    it('should show confidence scores', () => {
      MessageInput.sendAndWait('Optimization confidence level')
      cy.contains(/confidence|certainty|probability/i).should('be.visible')
      cy.contains(/%|score/i).should('be.visible')
    })
  })

  describe('Personalization and Context', () => {
    it('should adapt to user expertise level', () => {
      MessageInput.sendAndWait('I am a beginner, explain optimization')
      cy.contains(/simple|basic|introduction/i).should('be.visible')
    })

    it('should remember user preferences', () => {
      MessageInput.sendAndWait('I prefer detailed technical analysis')
      MessageInput.sendAndWait('Optimize my system')
      cy.contains(/technical|detailed|specifications/i).should('be.visible')
    })

    it('should provide contextual follow-up suggestions', () => {
      MessageInput.sendAndWait('Show optimization plan')
      cy.contains(/next steps|also consider|might want/i).should('be.visible')
    })

    it('should track conversation goals', () => {
      MessageInput.sendAndWait('My goal is 30% cost reduction')
      MessageInput.sendAndWait('How close am I to my goal?')
      cy.contains(/30%|cost reduction|goal/i).should('be.visible')
    })
  })
})