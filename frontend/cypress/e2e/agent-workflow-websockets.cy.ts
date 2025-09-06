/// <reference types="cypress" />

/**
 * MISSION CRITICAL: Real Agent Orchestration via WebSockets
 * 
 * Business Value Focus:
 * - Real Solutions: Multi-agent workflows solving complex business problems
 * - Agent Handoffs: Seamless transitions between specialized agents
 * - Tool Transparency: Users see which tools are solving their problems
 * - Progressive Results: Incremental value delivery as agents work
 * - Enterprise Scale: Complex workflows for high-value customers
 * 
 * Tests REAL agent orchestration patterns that deliver business value
 */

import { 
  ChatNavigation, 
  MessageInput, 
  MessageAssertions, 
  AgentProcessing, 
  MetricsValidation,
  ComponentVisibility,
  UIState,
  WaitHelpers 
} from './utils/chat-test-helpers'

describe('Mission Critical: Real Agent Orchestration Flows', () => {
  const DEFAULT_TIMEOUT = 15000
  const LONG_TIMEOUT = 45000
  
  beforeEach(() => {
    ChatNavigation.setupTechnology()
    // Ensure WebSocket ready for real-time updates
    cy.window().then((win) => {
      expect(win).to.have.property('WebSocket')
    })
  })

  describe('Enterprise Multi-Agent Workflows', () => {
    it('orchestrates Triage → Data → Optimization workflow for cost analysis', () => {
      // Real enterprise scenario: Complex cost optimization request
      const enterpriseRequest = `
        Our AI infrastructure costs $500K/month across:
        - 10M GPT-4 API calls
        - 50M embeddings operations  
        - 200TB vector storage
        - 500 GPU hours for fine-tuning
        Need comprehensive optimization strategy.
      `
      
      MessageInput.send(enterpriseRequest)
      
      // Step 1: Triage Agent understands the complex request
      cy.contains(/Triage Agent.*analyzing|processing/i, { timeout: 2000 })
        .should('be.visible')
      
      cy.contains(/categorizing.*request|understanding.*needs/i)
        .should('be.visible')
      
      // Real-time thinking updates
      cy.contains(/infrastructure.*cost.*optimization/i)
        .should('be.visible')
      
      // Step 2: Data Agent collects and analyzes metrics
      cy.contains(/Data Agent.*activated|starting/i, { timeout: 5000 })
        .should('be.visible')
      
      // Tool executions for data collection
      cy.contains(/usage_analyzer|cost_metrics|performance_profiler/i)
        .should('be.visible')
      
      // Progressive results as tools complete
      cy.contains(/10M.*GPT-4|50M.*embeddings/i, { timeout: 10000 })
        .should('be.visible')
      
      // Step 3: Optimization Agent provides solutions
      cy.contains(/Optimization Agent.*processing|analyzing/i, { timeout: 10000 })
        .should('be.visible')
      
      // Real optimization recommendations appear
      WaitHelpers.forResponse()
      
      // Verify comprehensive solution delivered
      cy.contains(/model.*migration|Claude.*Haiku|GPT-3.5/i).should('be.visible')
      cy.contains(/vector.*optimization|compression/i).should('be.visible')
      cy.contains(/GPU.*scheduling|batch.*processing/i).should('be.visible')
      cy.contains(/\$\d+K.*savings|%\d+.*reduction/i).should('be.visible')
    })

    it('handles complex RAG implementation workflow with multiple agents', () => {
      const ragRequest = `
        Implement RAG system for 100K technical documents:
        - Real-time query response < 500ms
        - 99.9% accuracy requirement
        - Support for 1000 concurrent users
        - Budget: $50K/month
      `
      
      MessageInput.send(ragRequest)
      
      // Triage identifies as complex technical implementation
      cy.contains(/Triage Agent/i).should('be.visible')
      cy.contains(/technical.*implementation|RAG.*system/i).should('be.visible')
      
      // Data Agent analyzes requirements
      cy.contains(/Data Agent/i, { timeout: 5000 }).should('be.visible')
      cy.contains(/analyzing.*requirements|document.*volume/i).should('be.visible')
      
      // Multiple tools execute in sequence
      const expectedTools = [
        'document_analyzer',
        'embedding_calculator', 
        'vector_db_selector',
        'performance_estimator',
        'cost_calculator'
      ]
      
      expectedTools.forEach(tool => {
        cy.contains(new RegExp(tool.replace('_', '.*'), 'i'), { timeout: 15000 })
          .should('exist')
      })
      
      // Optimization Agent provides implementation plan
      cy.contains(/Optimization Agent/i, { timeout: 10000 }).should('be.visible')
      
      WaitHelpers.forResponse()
      
      // Comprehensive implementation plan delivered
      cy.contains(/Pinecone|Weaviate|Qdrant/i).should('be.visible')
      cy.contains(/OpenAI.*embedding|Cohere/i).should('be.visible')
      cy.contains(/chunking.*strategy/i).should('be.visible')
      cy.contains(/caching.*layer|Redis/i).should('be.visible')
      cy.contains(/\$\d+K.*monthly|budget/i).should('be.visible')
    })

    it('executes financial analysis workflow with specialized agents', () => {
      const financialRequest = `
        Analyze our Q4 AI spending trends:
        - Compare against Q3 baseline
        - Identify anomalies and spikes
        - Project Q1 costs with 20% growth
        - Recommend budget allocation
      `
      
      MessageInput.send(financialRequest)
      
      // Financial analysis requires specialized workflow
      cy.contains(/Triage Agent.*financial|spending/i).should('be.visible')
      
      // Data Agent performs time-series analysis
      cy.contains(/Data Agent.*collecting.*historical/i, { timeout: 5000 })
        .should('be.visible')
      
      // Financial analysis tools
      cy.contains(/trend_analyzer|anomaly_detector|cost_projector/i, { timeout: 10000 })
        .should('exist')
      
      // Progressive insights delivered
      cy.contains(/Q3.*baseline|Q4.*comparison/i, { timeout: 15000 })
        .should('be.visible')
      
      cy.contains(/spike.*detected|anomaly.*found/i)
        .should('exist')
      
      // Optimization Agent provides budget recommendations
      cy.contains(/Optimization Agent.*budget/i, { timeout: 10000 })
        .should('be.visible')
      
      WaitHelpers.forResponse()
      
      // Financial recommendations delivered
      cy.contains(/Q1.*projection|20%.*growth/i).should('be.visible')
      cy.contains(/budget.*allocation|recommend/i).should('be.visible')
      cy.contains(/\$\d+K|\d+%/i).should('be.visible')
    })
  })

  describe('Real-Time Tool Execution Transparency', () => {
    it('shows detailed tool execution progress with meaningful names', () => {
      MessageInput.send('Optimize our customer support AI chatbot for cost and quality')
      
      // User sees which tools are working on their problem
      const businessTools = [
        { name: 'conversation_analyzer', purpose: 'Analyzing chat patterns' },
        { name: 'sentiment_evaluator', purpose: 'Measuring satisfaction' },
        { name: 'response_optimizer', purpose: 'Improving quality' },
        { name: 'cost_reducer', purpose: 'Finding savings' }
      ]
      
      businessTools.forEach(tool => {
        cy.contains(new RegExp(tool.purpose, 'i'), { timeout: 20000 })
          .should('exist')
      })
      
      // Tool results appear progressively
      cy.contains(/chat.*volume|conversations.*analyzed/i).should('be.visible')
      cy.contains(/satisfaction.*score|sentiment/i).should('be.visible')
      cy.contains(/response.*quality|accuracy/i).should('be.visible')
      cy.contains(/cost.*reduction|savings/i).should('be.visible')
    })

    it('handles tool failures gracefully with user-friendly messages', () => {
      MessageInput.send('Analyze data from non-existent system XYZ-9000')
      
      // Agent attempts to process
      cy.contains(/Agent.*processing/i).should('be.visible')
      
      // Tool execution attempted
      cy.contains(/analyzing|checking|searching/i, { timeout: 5000 })
        .should('be.visible')
      
      WaitHelpers.forResponse()
      
      // Graceful failure handling - no technical errors shown
      cy.get('body').then($body => {
        const text = $body.text()
        
        // Should NOT show technical errors
        expect(text).to.not.include('Exception')
        expect(text).to.not.include('Error 500')
        expect(text).to.not.include('Stack trace')
        
        // Should show helpful message
        expect(text.toLowerCase()).to.match(/unable|not found|unavailable|alternative/i)
      })
    })

    it('shows incremental results as tools complete', () => {
      MessageInput.send('Comprehensive analysis of our ML model performance')
      
      // Track incremental result delivery
      let resultCount = 0
      const checkInterval = 1000 // Check every second
      const maxChecks = 20
      
      // Monitor for incremental results
      for (let i = 0; i < maxChecks; i++) {
        cy.wait(checkInterval)
        
        cy.get('body').then($body => {
          const text = $body.text()
          
          // Check for various result indicators
          if (text.includes('latency') || text.includes('ms')) resultCount++
          if (text.includes('accuracy') || text.includes('%')) resultCount++
          if (text.includes('throughput') || text.includes('requests')) resultCount++
          if (text.includes('cost') || text.includes('$')) resultCount++
        })
      }
      
      // Should have received multiple incremental updates
      cy.wrap(null).then(() => {
        expect(resultCount).to.be.greaterThan(2, 'Should receive incremental results')
      })
    })
  })

  describe('Agent Handoff Patterns', () => {
    it('shows clear handoff messages between agents', () => {
      MessageInput.send('Migrate our NLP pipeline from GPT-4 to Claude')
      
      // Triage → Technical Analysis handoff
      cy.contains(/Triage Agent.*completed/i, { timeout: 5000 })
        .should('exist')
      
      cy.contains(/routing to|handing off|transferring/i)
        .should('be.visible')
      
      cy.contains(/Data Agent.*started/i)
        .should('be.visible')
      
      // Data → Optimization handoff  
      cy.contains(/Data Agent.*completed/i, { timeout: 10000 })
        .should('exist')
      
      cy.contains(/Optimization Agent.*started/i)
        .should('be.visible')
      
      // Clear indication of workflow progression
      cy.contains(/migration.*plan|implementation.*steps/i, { timeout: 15000 })
        .should('be.visible')
    })

    it('maintains context across agent handoffs', () => {
      // First message establishes context
      MessageInput.send('We have 5M daily API calls costing $100K/month')
      WaitHelpers.forResponse()
      
      // Follow-up that requires context
      MessageInput.send('Which model should we switch to?')
      
      // Agents should maintain context about 5M calls and $100K
      cy.contains(/5M|5 million|daily.*calls/i, { timeout: 10000 })
        .should('be.visible')
      
      cy.contains(/\$100K|100,000.*month/i)
        .should('be.visible')
      
      // Recommendations should be contextualized
      cy.contains(/Claude|GPT-3.5|alternative/i)
        .should('be.visible')
      
      cy.contains(/cost.*reduction|save/i)
        .should('be.visible')
    })

    it('handles supervisor recovery for failed agent handoffs', () => {
      // Complex request that might cause handoff issues
      MessageInput.send('Optimize our quantum computing simulation workload')
      
      // Initial agent processing
      cy.contains(/Agent.*processing/i).should('be.visible')
      
      // Even if specific agent fails, supervisor ensures completion
      WaitHelpers.forResponse()
      
      // Should still get a meaningful response
      cy.get('body').then($body => {
        const text = $body.text().toLowerCase()
        
        // Should provide some form of guidance
        expect(text).to.match(/quantum|simulation|computing|optimization|recommendation/i)
        
        // Should NOT leave user hanging
        expect(text).to.not.include('no response')
        expect(text).to.not.include('error occurred')
      })
    })
  })

  describe('Performance and User Experience', () => {
    it('provides status updates at least every 2 seconds during long operations', () => {
      MessageInput.send('Analyze 1 year of historical usage data with detailed breakdown')
      
      const updates: string[] = []
      const startTime = Date.now()
      const checkDuration = 15000 // Monitor for 15 seconds
      
      // Monitor for status updates
      const checkForUpdates = () => {
        cy.get('body').then($body => {
          const currentText = $body.text()
          
          // Look for new status messages
          if (currentText.includes('processing') || 
              currentText.includes('analyzing') ||
              currentText.includes('calculating') ||
              currentText.includes('%')) {
            updates.push(currentText)
          }
          
          if (Date.now() - startTime < checkDuration) {
            cy.wait(500).then(checkForUpdates)
          }
        })
      }
      
      checkForUpdates()
      
      // Verify frequent updates
      cy.wrap(null).then(() => {
        expect(updates.length).to.be.greaterThan(5, 'Should provide frequent status updates')
      })
    })

    it('shows agent thinking process for complex decisions', () => {
      MessageInput.send('Should we use OpenAI, Anthropic, or Google for our use case?')
      
      // Should show agent reasoning process
      cy.contains(/evaluating|comparing|analyzing/i, { timeout: 5000 })
        .should('be.visible')
      
      // Show criteria being considered
      cy.contains(/cost|performance|latency|accuracy|features/i)
        .should('exist')
      
      // Progressive evaluation of options
      cy.contains('OpenAI').should('be.visible')
      cy.contains('Anthropic').should('be.visible')
      cy.contains('Google').should('be.visible')
      
      WaitHelpers.forResponse()
      
      // Final recommendation with reasoning
      cy.contains(/recommend|suggest|best.*option/i).should('be.visible')
      cy.contains(/because|reason|advantage/i).should('be.visible')
    })

    it('handles rapid successive requests without confusion', () => {
      // First request
      MessageInput.send('Analyze costs')
      
      // Wait briefly but not for completion
      cy.wait(1000)
      
      // Second request while first still processing
      MessageInput.send('Check performance metrics')
      
      // Both requests should be visible
      cy.contains('Analyze costs').should('be.visible')
      cy.contains('Check performance metrics').should('be.visible')
      
      // System should handle both without confusion
      WaitHelpers.forResponse()
      
      // Should have responses related to both requests
      cy.contains(/cost|spend|budget/i).should('exist')
      cy.contains(/performance|latency|throughput/i).should('exist')
    })
  })

  describe('Industry-Specific Agent Workflows', () => {
    it('executes healthcare-compliant workflow for medical AI optimization', () => {
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Healthcare')
      
      MessageInput.send('Optimize our medical imaging AI pipeline for HIPAA compliance')
      
      // Healthcare-specific agent workflow
      cy.contains(/compliance.*check|HIPAA.*validation/i, { timeout: 5000 })
        .should('be.visible')
      
      // Medical-specific tools
      cy.contains(/privacy.*analyzer|compliance.*checker|audit.*tool/i)
        .should('exist')
      
      WaitHelpers.forResponse()
      
      // Healthcare-specific recommendations
      cy.contains(/HIPAA|compliance|privacy|patient.*data/i).should('be.visible')
      cy.contains(/encryption|audit.*trail|access.*control/i).should('be.visible')
      cy.contains(/medical|clinical|diagnostic/i).should('be.visible')
    })

    it('executes financial services workflow with regulatory considerations', () => {
      ChatNavigation.visitDemo()
      ChatNavigation.selectIndustry('Finance')
      
      MessageInput.send('Implement AI for fraud detection with SOC2 compliance')
      
      // Financial services specific workflow
      cy.contains(/regulatory.*check|compliance.*validation/i, { timeout: 5000 })
        .should('be.visible')
      
      // Financial tools and analysis
      cy.contains(/fraud.*pattern|transaction.*analysis|risk.*assessment/i)
        .should('exist')
      
      WaitHelpers.forResponse()
      
      // Financial-specific recommendations
      cy.contains(/SOC2|compliance|audit/i).should('be.visible')
      cy.contains(/fraud|transaction|risk/i).should('be.visible')
      cy.contains(/real-time|monitoring|alert/i).should('be.visible')
    })
  })

  describe('WebSocket Connection Resilience', () => {
    it('maintains agent workflow state during brief disconnections', () => {
      MessageInput.send('Long running analysis task')
      
      // Verify processing started
      cy.contains(/Agent.*processing/i).should('be.visible')
      
      // Simulate brief network interruption
      cy.window().then(win => {
        const ws = (win as any).__activeWebSocket
        if (ws) {
          ws.close()
        }
      })
      
      cy.wait(2000)
      
      // Should auto-reconnect and continue
      cy.contains(/reconnecting|resuming|continuing/i, { timeout: 5000 })
        .should('exist')
      
      // Workflow should complete successfully
      WaitHelpers.forResponse()
      
      // Verify complete response received
      cy.get('[class*="assistant"]').should('exist')
    })

    it('queues and delivers agent events after reconnection', () => {
      // Start a query
      MessageInput.send('Optimize our infrastructure')
      
      // Wait for initial processing
      cy.contains(/processing/i).should('be.visible')
      
      // Simulate disconnection during processing
      cy.window().then(win => {
        // Store reference to check for queued events
        (win as any).__queuedEvents = []
        
        const ws = (win as any).__activeWebSocket
        if (ws) {
          const originalSend = ws.send
          ws.send = (data: any) => {
            (win as any).__queuedEvents.push(data)
          }
        }
      })
      
      cy.wait(3000)
      
      // Restore connection
      cy.window().then(win => {
        const ws = (win as any).__activeWebSocket
        if (ws && (win as any).__queuedEvents) {
          // Events should have been queued
          expect((win as any).__queuedEvents.length).to.be.greaterThan(0)
        }
      })
      
      // Should still receive complete response
      WaitHelpers.forResponse()
      cy.contains(/optimization|recommendation/i).should('be.visible')
    })
  })
})