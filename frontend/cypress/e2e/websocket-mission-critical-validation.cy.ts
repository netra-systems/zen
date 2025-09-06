/// <reference types="cypress" />

import {
  WEBSOCKET_CONFIG,
  CRITICAL_WS_EVENTS,
  CriticalWebSocketEvent,
  setupTestEnvironment,
  navigateToChat,
  waitForConnection,
  findWebSocketConnection,
  simulateCriticalWebSocketEvents,
  verifyWebSocketServiceIntegration
} from '../support/websocket-test-helpers';

/**
 * MISSION CRITICAL: WebSocket Event Validation for Chat Business Value
 * 
 * Business Value Focus:
 * These 5 events are MANDATORY for delivering chat value to users:
 * 1. agent_started - Users SEE their request is being processed (not ignored)
 * 2. agent_thinking - Users SEE reasoning/progress (builds trust & engagement)
 * 3. tool_executing - Users SEE what tools are working on their problem
 * 4. tool_completed - Users SEE results as they arrive (incremental value)
 * 5. agent_completed - Users KNOW when they have their complete answer
 * 
 * WITHOUT THESE EVENTS = NO BUSINESS VALUE
 * Users will abandon the product if they don't see real-time progress
 */
describe('Mission Critical: WebSocket Business Value Delivery', () => {
  beforeEach(() => {
    setupTestEnvironment();
    navigateToChat();
  });

  afterEach(() => {
    // Clean up WebSocket connections
    cy.window().then((win) => {
      const ws = findWebSocketConnection(win);
      if (ws && ws.close && ws.readyState === WebSocket.OPEN) {
        ws.close(1000, 'Test cleanup');
      }
    });
  });

  describe('Real-Time User Feedback: All 5 Events Must Work', () => {
    it('CRITICAL: User sees agent_started immediately after sending message', () => {
      waitForConnection().then(() => {
        // User sends a real business problem
        const userProblem = 'Our AI costs are $100K/month, need to optimize';
        cy.get('textarea').type(userProblem);
        cy.get('button[aria-label="Send message"]').click();
        
        // User MUST see agent started within 2 seconds (not 10+ seconds)
        cy.contains(/Triage Agent.*started|processing|analyzing/i, { timeout: 2000 })
          .should('be.visible');
        
        // Validate the event was sent through WebSocket
        cy.window().then((win) => {
          const events = (win as any).__capturedWebSocketEvents || [];
          const startEvent = events.find((e: any) => e.type === 'agent_started');
          expect(startEvent).to.exist;
          expect(startEvent.payload).to.have.property('agent_type');
          expect(startEvent.payload).to.have.property('message');
        });
      });
    });

    it('CRITICAL: User sees agent_thinking with real reasoning steps', () => {
      waitForConnection().then(() => {
        // Simulate agent thinking about a real problem
        cy.window().then((win) => {
          const store = (win as any).useUnifiedChatStore?.getState();
          
          // Realistic thinking sequence for cost optimization
          const thinkingSteps = [
            'Analyzing current usage patterns and spend distribution...',
            'Identifying high-cost API calls and optimization opportunities...',
            'Calculating potential savings from model switching...',
            'Preparing recommendations for immediate implementation...'
          ];
          
          thinkingSteps.forEach((thought, index) => {
            const thinkingEvent = {
              type: 'agent_thinking',
              payload: {
                thought,
                agent_id: 'optimization-agent-001',
                agent_type: 'OptimizationAgent',
                step_number: index + 1,
                total_steps: thinkingSteps.length,
                timestamp: Date.now()
              }
            };
            
            store.handleWebSocketEvent(thinkingEvent);
            
            // User should see the thinking step
            cy.contains(thought, { timeout: 1000 }).should('be.visible');
          });
        });
      });
    });

    it('CRITICAL: User sees tool_executing with meaningful tool names', () => {
      waitForConnection().then(() => {
        cy.window().then((win) => {
          const store = (win as any).useUnifiedChatStore?.getState();
          
          // Business-meaningful tools that users understand
          const businessTools = [
            { name: 'cost_analyzer', description: 'Analyzing your AI spend patterns' },
            { name: 'usage_metrics', description: 'Collecting usage data' },
            { name: 'optimization_engine', description: 'Finding cost savings' },
            { name: 'roi_calculator', description: 'Calculating ROI impact' }
          ];
          
          businessTools.forEach(tool => {
            const toolEvent = {
              type: 'tool_executing',
              payload: {
                tool_name: tool.name,
                tool_description: tool.description,
                agent_id: 'data-agent-001',
                agent_type: 'DataAgent',
                timestamp: Date.now()
              }
            };
            
            store.handleWebSocketEvent(toolEvent);
            
            // User should understand what tool is running
            cy.contains(new RegExp(tool.description, 'i'), { timeout: 1000 })
              .should('be.visible');
          });
        });
      });
    });

    it('CRITICAL: User sees tool_completed with actual results', () => {
      waitForConnection().then(() => {
        cy.window().then((win) => {
          const store = (win as any).useUnifiedChatStore?.getState();
          
          // Real tool results that deliver value
          const toolResults = [
            {
              tool: 'cost_analyzer',
              result: {
                monthly_spend: '$100,000',
                top_cost_driver: 'GPT-4 API calls (65%)',
                optimization_potential: '$35,000/month'
              }
            },
            {
              tool: 'optimization_engine',
              result: {
                recommendations: [
                  'Switch 40% of GPT-4 calls to Claude Haiku',
                  'Implement response caching for repeated queries',
                  'Use batch processing for non-urgent requests'
                ],
                estimated_savings: '$35,000/month'
              }
            }
          ];
          
          toolResults.forEach(({ tool, result }) => {
            const completedEvent = {
              type: 'tool_completed',
              payload: {
                tool_name: tool,
                result: {
                  success: true,
                  data: result,
                  execution_time_ms: 1500
                },
                agent_id: 'optimization-agent-001',
                timestamp: Date.now()
              }
            };
            
            store.handleWebSocketEvent(completedEvent);
            
            // User should see actual results
            if (result.monthly_spend) {
              cy.contains(result.monthly_spend).should('be.visible');
            }
            if (result.estimated_savings) {
              cy.contains(result.estimated_savings).should('be.visible');
            }
          });
        });
      });
    });

    it('CRITICAL: User sees agent_completed with final recommendations', () => {
      waitForConnection().then(() => {
        cy.window().then((win) => {
          const store = (win as any).useUnifiedChatStore?.getState();
          
          // Complete agent response with business value
          const completedEvent = {
            type: 'agent_completed',
            payload: {
              agent_id: 'optimization-agent-001',
              agent_type: 'OptimizationAgent',
              duration_ms: 12500,
              result: {
                status: 'success',
                message: 'Optimization analysis complete',
                summary: 'Found $35K/month in potential savings',
                recommendations: [
                  {
                    action: 'Model Migration',
                    description: 'Switch 40% of GPT-4 to Claude Haiku',
                    savings: '$20,000/month',
                    implementation: 'Update API routing logic'
                  },
                  {
                    action: 'Response Caching',
                    description: 'Cache frequent queries',
                    savings: '$10,000/month',
                    implementation: 'Deploy Redis cache layer'
                  },
                  {
                    action: 'Batch Processing',
                    description: 'Batch non-urgent requests',
                    savings: '$5,000/month',
                    implementation: 'Implement queue system'
                  }
                ]
              },
              metrics: {
                tools_used: 4,
                data_points_analyzed: 50000,
                confidence_score: 0.92
              }
            }
          };
          
          store.handleWebSocketEvent(completedEvent);
          
          // User should see complete, actionable results
          cy.contains('$35K/month').should('be.visible');
          cy.contains('Model Migration').should('be.visible');
          cy.contains('Response Caching').should('be.visible');
          cy.contains('Batch Processing').should('be.visible');
          
          // User knows processing is complete
          cy.get('textarea').should('not.be.disabled');
          cy.get('button[aria-label="Send message"]').should('not.be.disabled');
        });
      });
    });
  });

  describe('Complete Agent Workflow: End-to-End Business Value', () => {
    it('delivers complete optimization workflow with all 5 events in sequence', () => {
      waitForConnection().then(() => {
        cy.window().then((win) => {
          const store = (win as any).useUnifiedChatStore?.getState();
          const agentId = `opt-agent-${Date.now()}`;
          const runId = `run-${Date.now()}`;
          
          // 1. Agent Started - User sees processing began
          store.handleWebSocketEvent({
            type: 'agent_started',
            payload: {
              agent_id: agentId,
              agent_type: 'TriageAgent',
              run_id: runId,
              message: 'Analyzing your optimization request...',
              timestamp: Date.now()
            }
          });
          
          cy.contains('Analyzing your optimization request').should('be.visible');
          cy.wait(500);
          
          // 2. Agent Thinking - User sees reasoning
          store.handleWebSocketEvent({
            type: 'agent_thinking',
            payload: {
              agent_id: agentId,
              thought: 'Identified cost optimization as primary goal. Routing to Data Agent for metrics collection.',
              step_number: 1,
              total_steps: 3
            }
          });
          
          cy.contains('cost optimization').should('be.visible');
          cy.wait(500);
          
          // 3. Tool Executing - User sees tools working
          store.handleWebSocketEvent({
            type: 'tool_executing',
            payload: {
              agent_id: agentId,
              tool_name: 'usage_analyzer',
              tool_description: 'Analyzing your AI usage patterns...'
            }
          });
          
          cy.contains('usage patterns').should('be.visible');
          cy.wait(1000);
          
          // 4. Tool Completed - User sees results arriving
          store.handleWebSocketEvent({
            type: 'tool_completed',
            payload: {
              agent_id: agentId,
              tool_name: 'usage_analyzer',
              result: {
                success: true,
                data: {
                  total_requests: '2.5M/month',
                  peak_usage: '150K requests/day',
                  cost_breakdown: {
                    'GPT-4': '$65,000',
                    'GPT-3.5': '$25,000',
                    'Embeddings': '$10,000'
                  }
                }
              }
            }
          });
          
          cy.contains('GPT-4').should('be.visible');
          cy.contains('$65,000').should('be.visible');
          cy.wait(500);
          
          // 5. Agent Completed - User gets final answer
          store.handleWebSocketEvent({
            type: 'agent_completed',
            payload: {
              agent_id: agentId,
              agent_type: 'OptimizationAgent',
              duration_ms: 8500,
              result: {
                status: 'success',
                message: 'Analysis complete. Here are your optimization opportunities:',
                savings_potential: '$35,000/month',
                quick_wins: [
                  'Switch classification tasks to Claude Haiku: Save $15K/month',
                  'Implement caching for repeated queries: Save $10K/month',
                  'Use GPT-3.5 for simple tasks: Save $10K/month'
                ]
              }
            }
          });
          
          // User sees complete value proposition
          cy.contains('$35,000/month').should('be.visible');
          cy.contains('Claude Haiku').should('be.visible');
          cy.contains('caching').should('be.visible');
          
          // User can continue conversation
          cy.get('textarea').should('not.be.disabled');
        });
      });
    });

    it('handles multi-agent handoffs with continuous user feedback', () => {
      waitForConnection().then(() => {
        cy.window().then((win) => {
          const store = (win as any).useUnifiedChatStore?.getState();
          
          // Triage → Data → Optimization workflow
          const agents = [
            { id: 'triage-001', type: 'TriageAgent', task: 'Understanding request' },
            { id: 'data-002', type: 'DataAgent', task: 'Collecting metrics' },
            { id: 'opt-003', type: 'OptimizationAgent', task: 'Finding savings' }
          ];
          
          agents.forEach((agent, index) => {
            // Start agent
            store.handleWebSocketEvent({
              type: 'agent_started',
              payload: {
                agent_id: agent.id,
                agent_type: agent.type,
                message: `${agent.type} is ${agent.task}...`
              }
            });
            
            cy.contains(agent.task).should('be.visible');
            cy.wait(1000);
            
            // Complete agent
            store.handleWebSocketEvent({
              type: 'agent_completed',
              payload: {
                agent_id: agent.id,
                agent_type: agent.type,
                result: {
                  status: 'success',
                  handoff_to: index < agents.length - 1 ? agents[index + 1].type : null
                }
              }
            });
            
            cy.wait(500);
          });
          
          // Final result visible
          cy.contains('Finding savings').should('be.visible');
        });
      });
    });
  });

  describe('Error Recovery: Maintaining User Trust', () => {
    it('shows user-friendly messages during connection issues', () => {
      // Simulate connection loss
      cy.window().then((win) => {
        const ws = findWebSocketConnection(win);
        if (ws) {
          ws.close(1006, 'Network error simulation');
        }
      });
      
      // User should see helpful message, not technical error
      cy.contains(/reconnecting|connection interrupted|trying again/i, { timeout: 5000 })
        .should('be.visible');
      
      // Should not show scary technical errors
      cy.contains('WebSocket error').should('not.exist');
      cy.contains('Connection failed').should('not.exist');
      
      // Wait for auto-reconnect
      cy.wait(WEBSOCKET_CONFIG.RETRY_DELAY * 2);
      
      // Should reconnect automatically
      waitForConnection().then(() => {
        cy.contains(/connected|ready/i).should('be.visible');
      });
    });

    it('queues messages during connection loss and sends when reconnected', () => {
      waitForConnection().then(() => {
        // Send first message successfully
        const firstMessage = 'Analyze our costs';
        cy.get('textarea').type(firstMessage);
        cy.get('button[aria-label="Send message"]').click();
        cy.contains(firstMessage).should('be.visible');
        
        // Simulate connection loss
        cy.window().then((win) => {
          const ws = findWebSocketConnection(win);
          if (ws) ws.close();
        });
        
        // Try to send during disconnection
        const queuedMessage = 'What about performance optimization?';
        cy.get('textarea').type(queuedMessage);
        cy.get('button[aria-label="Send message"]').click();
        
        // Message should appear but show pending state
        cy.contains(queuedMessage).should('be.visible');
        cy.contains(/sending|pending|queued/i).should('be.visible');
        
        // Wait for reconnection
        cy.wait(WEBSOCKET_CONFIG.RETRY_DELAY * 3);
        
        // Message should be sent after reconnection
        waitForConnection().then(() => {
          cy.contains(/sending|pending|queued/i).should('not.exist');
          cy.contains(queuedMessage).should('be.visible');
        });
      });
    });
  });

  describe('Performance: User Experience Metrics', () => {
    it('shows agent_started within 500ms of user action', () => {
      waitForConnection().then(() => {
        const startTime = Date.now();
        
        // User sends message
        cy.get('textarea').type('Optimize our infrastructure');
        cy.get('button[aria-label="Send message"]').click();
        
        // Agent should start almost immediately
        cy.contains(/agent.*started|processing/i).should('be.visible').then(() => {
          const responseTime = Date.now() - startTime;
          expect(responseTime).to.be.lessThan(500, 'Agent must start within 500ms');
        });
      });
    });

    it('provides updates at least every 3 seconds during processing', () => {
      waitForConnection().then(() => {
        cy.window().then((win) => {
          const store = (win as any).useUnifiedChatStore?.getState();
          const updates: number[] = [];
          let lastUpdate = Date.now();
          
          // Start long-running agent
          store.handleWebSocketEvent({
            type: 'agent_started',
            payload: {
              agent_id: 'long-running-001',
              agent_type: 'DataAgent',
              message: 'Starting comprehensive analysis...'
            }
          });
          
          // Simulate periodic updates
          const interval = setInterval(() => {
            const now = Date.now();
            updates.push(now - lastUpdate);
            lastUpdate = now;
            
            store.handleWebSocketEvent({
              type: 'agent_thinking',
              payload: {
                agent_id: 'long-running-001',
                thought: `Processing... ${updates.length * 20}% complete`
              }
            });
          }, 2500);
          
          // Run for 10 seconds
          cy.wait(10000).then(() => {
            clearInterval(interval);
            
            // Verify updates were frequent enough
            updates.forEach(gap => {
              expect(gap).to.be.lessThan(3500, 'Updates must come at least every 3.5 seconds');
            });
          });
        });
      });
    });
  });

  describe('Multi-User Isolation: No Data Leakage', () => {
    it('ensures WebSocket events are user-isolated', () => {
      waitForConnection().then(() => {
        cy.window().then((win) => {
          // Capture current user's session ID
          const ws = findWebSocketConnection(win);
          expect(ws).to.exist;
          
          // Current user should only see their own events
          const store = (win as any).useUnifiedChatStore?.getState();
          
          // Simulate event for different user (should be filtered)
          const otherUserEvent = {
            type: 'agent_started',
            payload: {
              agent_id: 'other-user-agent',
              user_id: 'different-user-123',
              message: 'OTHER USER DATA - SHOULD NOT BE VISIBLE'
            }
          };
          
          // This should be filtered/ignored
          store.handleWebSocketEvent(otherUserEvent);
          
          // Should NOT see other user's data
          cy.contains('OTHER USER DATA').should('not.exist');
          
          // Current user's events should work normally
          const currentUserEvent = {
            type: 'agent_started',
            payload: {
              agent_id: 'current-user-agent',
              message: 'Processing your request...'
            }
          };
          
          store.handleWebSocketEvent(currentUserEvent);
          cy.contains('Processing your request').should('be.visible');
        });
      });
    });
  });
});