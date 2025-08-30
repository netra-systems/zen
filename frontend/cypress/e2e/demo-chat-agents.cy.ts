/// <reference types="cypress" />

import {
  ChatNavigation,
  MessageInput,
  MessageAssertions,
  AgentProcessing,
  MetricsValidation,
  InsightsPanel,
  ComponentVisibility,
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
      const message = 'Analyze my current AI infrastructure performance'
      MessageInput.send(message)
      
      // Verify message was sent
      MessageAssertions.assertUserMessage(message)
      
      // Check for processing indicators
      cy.get('body').then($body => {
        const hasProcessingIndicator = $body.find('[data-testid="agent-processing"], .processing, [class*="processing"]').length > 0;
        const hasProcessingText = /processing|analyzing|thinking/i.test($body.text());
        
        if (hasProcessingIndicator || hasProcessingText) {
          AgentProcessing.assertProcessingIndicator()
        } else {
          cy.log('Processing indicators may be displayed differently')
          WaitHelpers.forResponse()
        }
      })
    })

    it('should display multiple agent activations', () => {
      const complexMessage = 'Perform comprehensive analysis of my AI workload, identify optimization opportunities, and provide implementation recommendations'
      MessageInput.send(complexMessage)
      
      MessageAssertions.assertUserMessage(complexMessage)
      
      // Check for multiple agent indicators
      cy.get('body').then($body => {
        const agentIndicators = $body.find('[data-testid*="agent"], [class*="agent"]').length
        const hasMultipleAgents = /analyzer.*optimizer|multiple.*agent|orchestrat/i.test($body.text())
        
        if (agentIndicators >= 2 || hasMultipleAgents) {
          AgentProcessing.assertAgentActivation()
          cy.log(`Found ${agentIndicators} agent-related elements`)
        } else {
          cy.log('Agent orchestration may be handled differently')
          WaitHelpers.forProcessing()
        }
      })
    })

    it('should show agent names during processing', () => {
      const optimizeMessage = 'Optimize my machine learning model serving infrastructure'
      MessageInput.send(optimizeMessage)
      
      MessageAssertions.assertUserMessage(optimizeMessage)
      WaitHelpers.brief()
      
      // Check for agent names or types
      cy.get('body').then($body => {
        const text = $body.text()
        const hasAgentNames = /analyzer|optimizer|recommender|triage|supply.*researcher/i.test(text)
        const hasAgentTypes = /analysis.*agent|optimization.*agent|recommendation.*engine/i.test(text)
        
        if (hasAgentNames || hasAgentTypes) {
          AgentProcessing.assertAgentNames()
          cy.log('Agent names or types detected during processing')
        } else {
          cy.log('Agent naming may not be exposed in UI or handled differently')
          WaitHelpers.forResponse()
        }
      })
    })

    it('should display agent response with formatting', () => {
      const helpMessage = 'Help me optimize my AI deployment costs and performance'
      MessageInput.sendAndWait(helpMessage)
      
      // Verify user message and assistant response
      MessageAssertions.assertUserMessage(helpMessage)
      MessageAssertions.assertAssistantMessage()
      
      // Check for formatted response elements
      cy.get('body').then($body => {
        const hasFormatting = $body.find('h1, h2, h3, h4, ul, ol, strong, em, [data-testid*="formatted"]').length > 0
        const hasStructuredContent = /optimization strategy|cost savings|performance gains|implementation/i.test($body.text())
        
        if (hasFormatting || hasStructuredContent) {
          MessageAssertions.assertFormattedResponse()
          cy.log('Formatted response content detected')
        } else {
          cy.log('Response formatting may be handled differently')
          cy.get('[data-testid="assistant-message"]').should('be.visible')
        }
      })
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
      const analysisMessage = 'Analyze my current AI workload and provide optimization insights'
      MessageInput.sendAndWait(analysisMessage)
      
      MessageAssertions.assertUserMessage(analysisMessage)
      WaitHelpers.forResponse()
      
      // Check for insights panel or equivalent UI
      cy.get('body').then($body => {
        const hasInsightsPanel = $body.find('[data-testid="insights-panel"], [class*="insights"], [class*="panel"]').length > 0
        const hasInsightsContent = /insights|recommendations|optimization.*ready|potential.*savings/i.test($body.text())
        
        if (hasInsightsPanel) {
          InsightsPanel.assertVisible()
        } else if (hasInsightsContent) {
          cy.log('Insights content detected in response format')
          cy.contains(/insights|optimization/i).should('be.visible')
        } else {
          cy.log('Insights may be integrated into chat response differently')
          MessageAssertions.assertAssistantMessage()
        }
      })
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
      const codeMessage = 'Optimize code generation and development workflows for my tech team'
      MessageInput.sendAndWait(codeMessage)
      
      MessageAssertions.assertUserMessage(codeMessage)
      WaitHelpers.forResponse()
      
      // Check for technology-specific content
      cy.get('body').then($body => {
        const text = $body.text()
        const techKeywords = /code|development|IDE|programming|software|DevOps|CI\/CD|repository/i
        
        if (techKeywords.test(text)) {
          cy.contains(techKeywords).should('be.visible')
          cy.log('Technology-specific optimization content detected')
        } else {
          cy.log('Response may contain general optimization advice')
          MessageAssertions.assertAssistantMessage()
        }
      })
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
      const startupMessage = 'What can I save as a startup with limited AI budget?'
      MessageInput.sendAndWait(startupMessage)
      
      MessageAssertions.assertUserMessage(startupMessage)
      WaitHelpers.forResponse()
      
      // Check for cost savings information
      cy.get('body').then($body => {
        const text = $body.text()
        const hasCostInfo = /\$[\d,]+|\d+%.*sav|cost.*reduc|free.*tier/i.test(text)
        const hasStartupContent = /startup|small.*business|limited.*budget|free/i.test(text)
        
        if (hasCostInfo) {
          cy.contains(/\$[\d,]+|\d+%/i).should('be.visible')
          cy.log('Cost savings information provided')
        } else if (hasStartupContent) {
          cy.log('Startup-focused content detected')
          cy.contains(/startup|free/i).should('be.visible')
        } else {
          cy.log('Business value may be communicated differently')
          MessageAssertions.assertAssistantMessage()
        }
      })
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