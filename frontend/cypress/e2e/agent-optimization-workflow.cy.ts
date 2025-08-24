import { Message, WebSocketMessage } from '@/types/unified';

describe('Full Agent Optimization Workflow', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('authToken', 'test-token');
    });
    
    // Mock user endpoint
    cy.intercept('GET', '/api/me', {
      statusCode: 200,
      body: {
        id: 1,
        email: 'test@netrasystems.ai',
        full_name: 'Test User'
      }
    }).as('userRequest');

    cy.visit('/chat');
    cy.wait('@userRequest');
  });

  it('should complete full optimization request from user input to final report', () => {
    // User submits an optimization request
    const optimizationRequest = 'Optimize my LLM inference pipeline for cost and latency';
    cy.get('textarea[aria-label="Message input"]').type(optimizationRequest);
    cy.get('button').contains('Send').click();

    // Verify user message is displayed
    cy.contains(optimizationRequest).should('be.visible');

    // Simulate WebSocket messages for complete agent workflow
    cy.window().then((win) => {
      // 1. Triage Agent starts
      const triageStart: WebSocketMessage = {
        type: 'sub_agent_update',
        payload: {
          subAgentName: 'TriageSubAgent',
          subAgentStatus: {
            status: 'running',
            tools: ['analyze_request', 'categorize_optimization']
          }
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(triageStart) });

      // 2. Triage Agent message
      const triageMessage: WebSocketMessage = {
        type: 'message',
        payload: {
          id: 'triage-1',
          created_at: new Date().toISOString(),
          content: 'Analyzing optimization request for LLM inference pipeline...',
          type: 'agent',
          sub_agent_name: 'TriageSubAgent',
          displayed_to_user: true
        } as Message
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(triageMessage) });

      // 3. Data Agent starts
      const dataStart: WebSocketMessage = {
        type: 'sub_agent_update',
        payload: {
          subAgentName: 'DataSubAgent',
          subAgentStatus: {
            status: 'running',
            tools: ['collect_metrics', 'analyze_workload']
          }
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(dataStart) });

      // 4. Data Agent message
      const dataMessage: WebSocketMessage = {
        type: 'message',
        payload: {
          id: 'data-1',
          created_at: new Date().toISOString(),
          content: 'Collecting current performance metrics and workload characteristics...',
          type: 'agent',
          sub_agent_name: 'DataSubAgent',
          displayed_to_user: true,
          raw_data: {
            current_latency_p50: 120,
            current_latency_p99: 450,
            current_cost_per_1k_tokens: 0.002,
            daily_request_volume: 50000
          }
        } as Message
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(dataMessage) });

      // 5. Optimization Core Agent starts
      const optimizationStart: WebSocketMessage = {
        type: 'sub_agent_update',
        payload: {
          subAgentName: 'OptimizationsCoreSubAgent',
          subAgentStatus: {
            status: 'running',
            tools: ['simulate_optimization', 'cost_analysis', 'latency_bottleneck_identifier']
          }
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(optimizationStart) });

      // 6. Optimization Agent message with recommendations
      const optimizationMessage: WebSocketMessage = {
        type: 'message',
        payload: {
          id: 'opt-1',
          created_at: new Date().toISOString(),
          content: `## Optimization Recommendations

### 1. Enable KV Cache Optimization
- **Impact**: 35% latency reduction
- **Cost Savings**: $1,200/month
- **Implementation**: Configure dynamic KV cache with adaptive sizing

### 2. Implement Request Batching
- **Impact**: 25% throughput increase
- **Cost Savings**: $800/month
- **Implementation**: Enable dynamic batching with 50ms window

### 3. Switch to Quantized Model
- **Impact**: 40% cost reduction
- **Trade-off**: 2% accuracy loss (acceptable for your use case)
- **Implementation**: Deploy INT8 quantized version`,
          type: 'agent',
          sub_agent_name: 'OptimizationsCoreSubAgent',
          displayed_to_user: true
        } as Message
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(optimizationMessage) });

      // 7. Actions Agent starts
      const actionsStart: WebSocketMessage = {
        type: 'sub_agent_update',
        payload: {
          subAgentName: 'ActionsToMeetGoalsSubAgent',
          subAgentStatus: {
            status: 'running',
            tools: ['create_action_plan', 'prioritize_actions']
          }
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(actionsStart) });

      // 8. Actions Agent message
      const actionsMessage: WebSocketMessage = {
        type: 'message',
        payload: {
          id: 'actions-1',
          created_at: new Date().toISOString(),
          content: `## Implementation Action Plan

1. **Phase 1 (Week 1)**: Deploy KV cache optimization
2. **Phase 2 (Week 2)**: Implement request batching
3. **Phase 3 (Week 3)**: Test and deploy quantized model
4. **Monitoring**: Set up performance dashboards`,
          type: 'agent',
          sub_agent_name: 'ActionsToMeetGoalsSubAgent',
          displayed_to_user: true
        } as Message
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(actionsMessage) });

      // 9. Reporting Agent final report
      const reportingStart: WebSocketMessage = {
        type: 'sub_agent_update',
        payload: {
          subAgentName: 'ReportingSubAgent',
          subAgentStatus: {
            status: 'running',
            tools: ['generate_report', 'create_visualizations']
          }
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(reportingStart) });

      const finalReport: WebSocketMessage = {
        type: 'message',
        payload: {
          id: 'report-1',
          created_at: new Date().toISOString(),
          content: `# Optimization Report - LLM Inference Pipeline

## Executive Summary
Your LLM inference pipeline can achieve **35% latency reduction** and **$2,800/month cost savings** through three key optimizations.

## Current State
- P50 Latency: 120ms
- P99 Latency: 450ms
- Monthly Cost: $8,000
- Daily Requests: 50,000

## Optimized State (Projected)
- P50 Latency: 78ms (-35%)
- P99 Latency: 292ms (-35%)
- Monthly Cost: $5,200 (-35%)
- Throughput: +25%

## ROI Analysis
- Total Investment: $5,000 (one-time)
- Monthly Savings: $2,800
- Payback Period: 1.8 months
- Annual ROI: 572%

## Next Steps
1. Review implementation plan
2. Allocate engineering resources
3. Begin Phase 1 deployment

*Report generated by Netra AI Optimization Platform*`,
          type: 'agent',
          sub_agent_name: 'ReportingSubAgent',
          displayed_to_user: true
        } as Message
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(finalReport) });

      // 10. Complete status
      const completeStatus: WebSocketMessage = {
        type: 'sub_agent_update',
        payload: {
          subAgentName: 'ReportingSubAgent',
          subAgentStatus: {
            status: 'completed',
            tools: []
          }
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(completeStatus) });
    });

    // Verify all agents ran in sequence
    cy.contains('TriageSubAgent').should('be.visible');
    cy.contains('DataSubAgent').should('be.visible');
    cy.contains('OptimizationsCoreSubAgent').should('be.visible');
    cy.contains('ActionsToMeetGoalsSubAgent').should('be.visible');
    cy.contains('ReportingSubAgent').should('be.visible');

    // Verify optimization recommendations are displayed
    cy.contains('Enable KV Cache Optimization').should('be.visible');
    cy.contains('35% latency reduction').should('be.visible');
    cy.contains('$1,200/month').should('be.visible');

    // Verify final report is displayed
    cy.contains('Optimization Report - LLM Inference Pipeline').should('be.visible');
    cy.contains('Executive Summary').should('be.visible');
    cy.contains('ROI Analysis').should('be.visible');
    cy.contains('572%').should('be.visible');

    // Test viewing raw data
    cy.get('span').contains('View Raw Data').first().click();
    cy.get('.react-json-view').should('be.visible');
    cy.get('.react-json-view').should('contain', 'current_latency_p50');

    // Verify input is re-enabled after completion
    cy.get('textarea[aria-label="Message input"]').should('not.be.disabled');
    cy.get('button').contains('Send').should('not.be.disabled');
  });

  it('should handle optimization request interruption', () => {
    // Start an optimization request
    cy.get('textarea[aria-label="Message input"]').type('Optimize my model serving');
    cy.get('button').contains('Send').click();

    // Simulate agent starting
    cy.window().then((win) => {
      const agentStart: WebSocketMessage = {
        type: 'sub_agent_update',
        payload: {
          subAgentName: 'TriageSubAgent',
          subAgentStatus: {
            status: 'running',
            tools: ['analyze_request']
          }
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(agentStart) });
    });

    // Stop button should be available
    cy.get('button').contains('Stop Processing').should('not.be.disabled');
    
    // Click stop
    cy.get('button').contains('Stop Processing').click();
    
    // Simulate stop acknowledgment
    cy.window().then((win) => {
      const stopMessage: WebSocketMessage = {
        type: 'message',
        payload: {
          id: 'stop-1',
          created_at: new Date().toISOString(),
          content: 'Processing stopped by user request.',
          type: 'system',
          displayed_to_user: true
        } as Message
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(stopMessage) });
    });

    // Verify stop message
    cy.contains('Processing stopped by user request').should('be.visible');
    
    // Input should be re-enabled
    cy.get('textarea[aria-label="Message input"]').should('not.be.disabled');
  });

  it('should display and update optimization progress indicators', () => {
    const agents = [
      'TriageSubAgent',
      'DataSubAgent', 
      'OptimizationsCoreSubAgent',
      'ActionsToMeetGoalsSubAgent',
      'ReportingSubAgent'
    ];

    // Submit request
    cy.get('textarea[aria-label="Message input"]').type('Analyze my workload');
    cy.get('button').contains('Send').click();

    // Simulate each agent running with progress
    agents.forEach((agent, index) => {
      cy.window().then((win) => {
        const progressUpdate: WebSocketMessage = {
          type: 'sub_agent_update',
          payload: {
            subAgentName: agent,
            subAgentStatus: {
              status: 'running',
              tools: ['tool1', 'tool2'],
              progress: ((index + 1) / agents.length) * 100
            }
          }
        };
        // @ts-ignore
        (win as any).ws.onmessage({ data: JSON.stringify(progressUpdate) });
      });

      // Verify agent name is displayed in header
      cy.get('h1').should('contain', agent);
      cy.get('p').should('contain', 'running');
    });

    // Final completion
    cy.window().then((win) => {
      const complete: WebSocketMessage = {
        type: 'sub_agent_update',
        payload: {
          subAgentName: 'ReportingSubAgent',
          subAgentStatus: {
            status: 'completed',
            tools: [],
            progress: 100
          }
        }
      };
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(complete) });
    });

    cy.get('p').should('contain', 'completed');
  });
});