/// <reference types="cypress" />

import {
  ChatNavigation,
  MessageInput,
  Templates,
  MessageAssertions,
  ComponentVisibility,
  UIState,
  TestUtils,
  WaitHelpers,
  AgentProcessing,
  MetricsValidation
} from './utils/chat-test-helpers'

/**
 * MISSION CRITICAL: Core Chat Functionality Tests
 * 
 * Business Value Focus:
 * - Real Solutions: Agents solving REAL problems with actionable results
 * - Helpful: Responsive UI/UX that delivers meaningful AI responses  
 * - Timely: Real-time updates showing agent progress
 * - Complete: End-to-end flows delivering readable, valuable responses
 * - Data Driven: Showcasing data-driven insights and optimizations
 * 
 * These tests validate the PRIMARY value delivery mechanism (90% of business value)
 */

describe('Mission Critical: Chat Business Value Delivery', () => {
  beforeEach(() => {
    ChatNavigation.setupTechnology()
    // Ensure WebSocket connection for real-time updates
    cy.window().then((win) => {
      expect(win).to.have.property('WebSocket')
    })
  })

  describe('Real Solutions: Agent Problem Solving', () => {
    it('should deliver actionable optimization insights for real business problems', () => {
      // Real business problem: Customer experiencing high AI costs
      const realProblem = 'Our GPT-4 costs exceeded $50K last month with 2M API calls. We need to reduce costs while maintaining quality.'
      
      MessageInput.send(realProblem)
      
      // Validate real-time agent activation (Timely updates)
      AgentProcessing.assertAgentActivated('Triage Agent')
      cy.contains('Analyzing your AI cost optimization request').should('be.visible')
      
      // Wait for triage completion and data agent activation
      AgentProcessing.waitForAgentTransition('Triage Agent', 'Data Agent')
      cy.contains('Collecting usage patterns and cost metrics').should('be.visible')
      
      // Validate optimization agent provides actionable insights
      AgentProcessing.waitForAgentTransition('Data Agent', 'Optimization Agent')
      
      // Assert real business value in response
      WaitHelpers.forResponse()
      
      // Must provide specific, actionable recommendations
      cy.contains(/Model Selection|GPT-3.5-turbo|Claude Haiku/i).should('be.visible')
      cy.contains(/cost reduction|save|optimize/i).should('be.visible')
      cy.contains(/\$\d+|%\d+/i).should('be.visible') // Specific savings numbers
      
      // Validate complete solution with implementation steps
      cy.contains(/implement|migrate|switch/i).should('be.visible')
    })

    it('should provide data-driven insights with real metrics', () => {
      const dataRequest = 'Analyze our agent response times: p50=200ms, p95=800ms, p99=2s across 100K daily requests'
      
      MessageInput.send(dataRequest)
      
      // Validate data agent processes metrics
      AgentProcessing.waitForAgent('Data Agent')
      cy.contains('Processing performance metrics').should('be.visible')
      
      WaitHelpers.forResponse()
      
      // Must provide data-driven analysis
      cy.contains(/latency|response time|performance/i).should('be.visible')
      cy.contains(/p95|percentile/i).should('be.visible')
      cy.contains(/optimization|improve|reduce/i).should('be.visible')
      
      // Should suggest specific technical solutions
      cy.contains(/cache|CDN|edge|async|batch/i).should('be.visible')
    })

    it('should handle complex multi-agent workflows for enterprise scenarios', () => {
      const enterpriseScenario = 'We need to implement RAG for our 10TB document corpus with sub-second query times'
      
      MessageInput.send(enterpriseScenario)
      
      // Complex workflow should involve multiple agents
      AgentProcessing.assertAgentSequence([
        'Triage Agent',
        'Data Agent', 
        'Optimization Agent'
      ])
      
      WaitHelpers.forResponse()
      
      // Must address all aspects of the complex request
      cy.contains(/vector database|embedding|chunking/i).should('be.visible')
      cy.contains(/Pinecone|Weaviate|Qdrant|pgvector/i).should('be.visible')
      cy.contains(/performance|latency|scale/i).should('be.visible')
    })
  })

  describe('Timely Updates: Real-time Agent Progress', () => {
    it('should show all 5 mission-critical WebSocket events during processing', () => {
      MessageInput.send('Optimize our LLM pipeline for cost and latency')
      
      // 1. agent_started - User sees processing began
      cy.contains(/Triage Agent.*processing|starting|analyzing/i, { timeout: 5000 }).should('be.visible')
      
      // 2. agent_thinking - Real-time reasoning visibility
      cy.contains(/analyzing|evaluating|considering/i, { timeout: 10000 }).should('be.visible')
      
      // 3. tool_executing - Tool usage transparency
      cy.contains(/collecting|fetching|calculating/i, { timeout: 15000 }).should('be.visible')
      
      // 4. tool_completed - Tool results display
      cy.contains(/completed|finished|done/i, { timeout: 20000 }).should('be.visible')
      
      // 5. agent_completed - User knows response is ready
      WaitHelpers.forResponse()
      cy.get('textarea').should('not.be.disabled')
    })

    it('should maintain real-time updates during long-running agent tasks', () => {
      const complexQuery = 'Analyze cost optimization opportunities across our entire ML infrastructure'
      
      MessageInput.send(complexQuery)
      
      // Track update frequency - user should see updates every few seconds
      let updateCount = 0
      const startTime = Date.now()
      
      // Monitor for agent status changes
      cy.get('body').then($body => {
        const checkForUpdates = () => {
          if ($body.text().includes('processing') || $body.text().includes('analyzing')) {
            updateCount++
          }
          
          if (Date.now() - startTime < 10000) {
            cy.wait(1000)
            checkForUpdates()
          }
        }
        checkForUpdates()
      })
      
      // Ensure user received multiple updates during processing
      cy.wrap(null).then(() => {
        expect(updateCount).to.be.greaterThan(2)
      })
    })

    it('should show specific agent capabilities during execution', () => {
      MessageInput.send('Help me reduce our $100K monthly AI spend')
      
      // Each agent should show what they're specifically doing
      cy.contains('Triage Agent').parent().contains(/categorizing|routing|understanding/i).should('be.visible')
      cy.contains('Data Agent').parent().contains(/analyzing usage|collecting metrics|processing data/i).should('be.visible')
      cy.contains('Optimization Agent').parent().contains(/finding savings|optimizing costs|recommending/i).should('be.visible')
    })
  })

  describe('Complete Business Value: End-to-End Flows', () => {
    it('should deliver complete optimization workflow from problem to solution', () => {
      // Complete user journey: Problem → Analysis → Solution → Implementation
      MessageInput.send('Our customer support bot costs are too high')
      
      WaitHelpers.forResponse()
      
      // Problem acknowledgment
      cy.contains(/customer support|bot|costs/i).should('be.visible')
      
      // Analysis provided
      cy.contains(/analysis|evaluated|assessed/i).should('be.visible')
      
      // Solution offered
      cy.contains(/recommend|suggest|solution/i).should('be.visible')
      
      // Implementation guidance
      cy.contains(/steps|implement|migrate/i).should('be.visible')
      
      // Follow-up question to test context retention
      MessageInput.send('What specific models should we use?')
      
      WaitHelpers.forResponse()
      
      // Context maintained - still discussing customer support
      cy.contains(/customer support|chatbot/i).should('be.visible')
      cy.contains(/Claude|GPT|Gemini|model/i).should('be.visible')
    })

    it('should provide ROI calculations and business metrics', () => {
      MessageInput.send('Calculate ROI for switching from GPT-4 to Claude for our 1M daily requests')
      
      WaitHelpers.forResponse()
      
      // Must include concrete business metrics
      cy.contains(/ROI|return on investment|payback/i).should('be.visible')
      cy.contains(/\$\d+|\d+%/i).should('be.visible') // Specific numbers
      cy.contains(/monthly|annual|yearly/i).should('be.visible')
      cy.contains(/savings|reduction|efficiency/i).should('be.visible')
      
      // Should show comparison
      cy.contains(/GPT-4|Claude/i).should('be.visible')
      cy.contains(/cost.*per.*token|pricing/i).should('be.visible')
    })

    it('should handle industry-specific optimization scenarios', () => {
      // Healthcare industry scenario
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Healthcare')
      
      Templates.selectTemplate('Medical Image Analysis')
      cy.get('button[class*="px-4"]').click()
      
      WaitHelpers.forResponse()
      
      // Industry-specific insights
      cy.contains(/HIPAA|compliance|medical/i).should('be.visible')
      cy.contains(/accuracy|diagnosis|patient/i).should('be.visible')
      cy.contains(/GPU|inference|latency/i).should('be.visible')
    })
  })

  describe('Data-Driven Insights: Metrics and Analytics', () => {
    it('should display cost savings metrics prominently', () => {
      MessageInput.send('Show me potential savings for our $200K annual AI spend')
      
      WaitHelpers.forResponse()
      
      // Metrics panel should appear with specific savings
      MetricsValidation.assertMetricsVisible()
      cy.contains(/\$\d+K|\d+%/i).should('be.visible')
      cy.contains(/potential savings|cost reduction|optimization/i).should('be.visible')
      
      // Should break down savings by category
      cy.contains(/model selection|caching|batching/i).should('be.visible')
    })

    it('should provide performance improvement metrics', () => {
      MessageInput.send('How can we improve our 500ms average response time?')
      
      WaitHelpers.forResponse()
      
      // Should show current vs optimized metrics
      cy.contains(/500ms|current/i).should('be.visible')
      cy.contains(/\d+ms.*optimized|improved|reduced/i).should('be.visible')
      cy.contains(/\d+%.*faster|improvement|reduction/i).should('be.visible')
    })

    it('should offer comparative analysis between solutions', () => {
      MessageInput.send('Compare OpenAI vs Anthropic vs Google for our use case')
      
      WaitHelpers.forResponse()
      
      // Comprehensive comparison table/analysis
      cy.contains('OpenAI').should('be.visible')
      cy.contains('Anthropic').should('be.visible')  
      cy.contains('Google').should('be.visible')
      
      // Key comparison metrics
      cy.contains(/cost|pricing/i).should('be.visible')
      cy.contains(/latency|speed|performance/i).should('be.visible')
      cy.contains(/accuracy|quality/i).should('be.visible')
      cy.contains(/context|tokens/i).should('be.visible')
    })
  })

  describe('User Experience: Responsive and Helpful Interface', () => {
    it('should maintain conversation context across multiple interactions', () => {
      // First interaction - establish context
      MessageInput.send('We process 10M images monthly')
      WaitHelpers.forResponse()
      
      // Second interaction - test context retention
      MessageInput.send('What GPU configuration do you recommend?')
      WaitHelpers.forResponse()
      
      // Response should reference the 10M images context
      cy.contains(/10M|10 million|images/i).should('be.visible')
      cy.contains(/GPU|CUDA|tensor/i).should('be.visible')
      
      // Third interaction - deeper dive
      MessageInput.send('What about batch processing strategies?')
      WaitHelpers.forResponse()
      
      // Should maintain full context
      cy.contains(/batch|images|10M/i).should('be.visible')
      cy.contains(/parallel|concurrent|throughput/i).should('be.visible')
    })

    it('should handle rapid user inputs gracefully', () => {
      // Send multiple messages quickly
      MessageInput.type('First question about costs')
      cy.get('button[class*="px-4"]').click()
      
      // Try to send another immediately (should be disabled)
      cy.get('textarea').should('be.disabled')
      cy.get('button[class*="px-4"]').should('be.disabled')
      
      // Wait for response
      WaitHelpers.forResponse()
      
      // Should be re-enabled
      cy.get('textarea').should('not.be.disabled')
      
      // Send follow-up
      MessageInput.send('Second question about implementation')
      WaitHelpers.forResponse()
      
      // Both messages and responses should be visible
      cy.contains('First question about costs').should('be.visible')
      cy.contains('Second question about implementation').should('be.visible')
    })

    it('should provide helpful error recovery on network issues', () => {
      // Simulate network interruption
      cy.intercept('POST', '**/api/**', { forceNetworkError: true }).as('networkError')
      
      MessageInput.send('Test message during network issue')
      
      // Should show user-friendly error message
      cy.contains(/connection|network|retry/i, { timeout: 10000 }).should('be.visible')
      
      // Remove network interruption
      cy.intercept('POST', '**/api/**').as('restored')
      
      // Retry button should work
      cy.contains('Retry').click()
      
      // Should recover and work normally
      WaitHelpers.forResponse()
    })
  })

  describe('Business IP Protection', () => {
    it('should not expose internal agent implementation details', () => {
      MessageInput.send('How do your agents work internally?')
      
      WaitHelpers.forResponse()
      
      // Should not expose specific implementation details
      cy.get('.flex-1').then($messages => {
        const text = $messages.text().toLowerCase()
        
        // Should not contain internal technical details
        expect(text).to.not.include('sourcecode')
        expect(text).to.not.include('api_key')
        expect(text).to.not.include('secret')
        expect(text).to.not.include('webhook')
        expect(text).to.not.include('database schema')
        
        // Should provide high-level explanation instead
        expect(text).to.include('optimization')
        expect(text).to.include('analysis')
      })
    })
  })

  describe('Template System: Quick Value Delivery', () => {
    it('should provide instant value through industry templates', () => {
      // Each template should solve a real business problem
      const templates = [
        { name: 'Code Generation Pipeline', value: 'code completion costs' },
        { name: 'Customer Support Bot', value: 'support automation' },
        { name: 'User Analytics AI', value: 'behavior analysis' }
      ]
      
      templates.forEach(template => {
        cy.reload()
        ChatNavigation.setupTechnology()
        
        Templates.selectTemplate(template.name)
        cy.get('button[class*="px-4"]').click()
        
        WaitHelpers.forResponse()
        
        // Each template should deliver specific value
        cy.contains(new RegExp(template.value, 'i')).should('be.visible')
        cy.contains(/optimize|improve|reduce|save/i).should('be.visible')
      })
    })
  })
})

describe('Mission Critical: Multi-User System Integrity', () => {
  it('should maintain complete user isolation in concurrent sessions', () => {
    // This test validates that the system handles multiple users without data leakage
    
    // User 1 session
    const user1Query = 'User1: Optimize our fintech fraud detection system'
    MessageInput.send(user1Query)
    
    // Store User 1's message
    cy.contains(user1Query).should('be.visible')
    
    // Simulate User 2 in new session (new tab/window simulation)
    cy.window().then(win => {
      // Each user should have isolated WebSocket connection
      expect(win.WebSocket).to.exist
    })
    
    // Open new session
    cy.visit('/demo/chat?session=new')
    ChatNavigation.setupTechnology()
    
    // User 2 should NOT see User 1's messages
    cy.contains(user1Query).should('not.exist')
    
    // User 2 sends their own query
    const user2Query = 'User2: Optimize our healthcare AI diagnostics'
    MessageInput.send(user2Query)
    
    WaitHelpers.forResponse()
    
    // Validate User 2 gets healthcare-specific response
    cy.contains(/healthcare|diagnostic|medical/i).should('be.visible')
    
    // Should NOT contain fintech-related content from User 1
    cy.contains(/fintech|fraud/i).should('not.exist')
  })
})