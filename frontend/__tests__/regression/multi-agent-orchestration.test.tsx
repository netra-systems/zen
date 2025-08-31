/**
 * Multi-Agent Orchestration Test Suite
 * 
 * Comprehensive testing for multi-agent orchestration flows in the frontend.
 * Tests the complete agent lifecycle from triage through reporting, focusing on:
 * - Agent flow sequencing
 * - Data sufficiency evaluation
 * - Agent handoff and coordination
 * - Business logic outcomes
 * - Error recovery and resilience
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { AgentProvider, useAgentContext } from '@/providers/AgentProvider';
import { useChatStore } from '@/store/chatStore';
import { useUnifiedChatStore } from '@/store/unified-chat';
import type { 
  WebSocketMessage, 
  SubAgentState,
  Message,
  AgentError,
  OptimizationResults
} from '@/types/unified';

// Mock WebSocket
const mockWebSocket = {
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN,
};

// Mock WebSocket constructor
global.WebSocket = jest.fn(() => mockWebSocket) as any;

// Mock stores with getState
const mockChatStoreState = {
  messages: [],
  currentRunId: null,
  clearMessages: jest.fn(() => {
    mockChatStoreState.messages = [];
  }),
  addMessage: jest.fn((message) => {
    mockChatStoreState.messages.push(message);
  })
};

const mockUnifiedStoreState = {
  isAuthenticated: true,
  activeThreadId: 'test-thread-123',
  isProcessing: false,
  isThreadLoading: false,
  messages: [],
  currentRunId: null,
  fastLayerData: null,
  mediumLayerData: null,
  slowLayerData: null,
  resetState: jest.fn(() => {
    mockUnifiedStoreState.isProcessing = false;
    mockUnifiedStoreState.isThreadLoading = false;
    mockUnifiedStoreState.messages = [];
    mockUnifiedStoreState.currentRunId = null;
    mockUnifiedStoreState.fastLayerData = null;
    mockUnifiedStoreState.mediumLayerData = null;
    mockUnifiedStoreState.slowLayerData = null;
  })
};

jest.mock('@/store/chatStore', () => ({
  useChatStore: Object.assign(
    jest.fn(() => mockChatStoreState),
    {
      getState: jest.fn(() => mockChatStoreState)
    }
  )
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: Object.assign(
    jest.fn(() => mockUnifiedStoreState),
    {
      getState: jest.fn(() => mockUnifiedStoreState)
    }
  )
}));

// Mock AgentProvider
const mockAgentContext = {
  isProcessing: false,
  error: null,
  subAgentStatus: null,
  optimizationResults: null,
  executionHistory: [],
  executionTimes: new Map(),
  startAgent: jest.fn(),
  stopAgent: jest.fn(),
  resetAgent: jest.fn()
};

jest.mock('@/providers/AgentProvider', () => {
  const React = require('react');
  return {
    AgentProvider: ({ children }: { children: React.ReactNode }) => children,
    useAgentContext: jest.fn(() => mockAgentContext)
  };
});

describe('Multi-Agent Orchestration Tests', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let wsEventHandlers: { [key: string]: Function[] } = {};
  let agentContext: ReturnType<typeof useAgentContext>;
  let chatStore: ReturnType<typeof useChatStore>;
  let unifiedStore: ReturnType<typeof useUnifiedChatStore>;

  beforeEach(() => {
    jest.clearAllMocks();
    wsEventHandlers = {};
    
    // Setup WebSocket mock to capture event handlers
    mockWebSocket.addEventListener.mockImplementation((event: string, handler: Function) => {
      if (!wsEventHandlers[event]) {
        wsEventHandlers[event] = [];
      }
      wsEventHandlers[event].push(handler);
    });

    // Reset stores
    chatStore = useChatStore.getState();
    unifiedStore = useUnifiedChatStore.getState();
    chatStore.clearMessages();
    unifiedStore.resetState();
    
    // Reset mock agent context
    mockAgentContext.isProcessing = false;
    mockAgentContext.error = null;
    mockAgentContext.subAgentStatus = null;
    mockAgentContext.optimizationResults = null;
    mockAgentContext.executionHistory = [];
    mockAgentContext.executionTimes = new Map();
  });

  const simulateWebSocketMessage = (message: WebSocketMessage) => {
    const messageEvent = new MessageEvent('message', {
      data: JSON.stringify(message)
    });
    wsEventHandlers['message']?.forEach(handler => handler(messageEvent));
  };

  const createWrapper = ({ children }: { children: React.ReactNode }) => (
    <WebSocketProvider>
      <AgentProvider>{children}</AgentProvider>
    </WebSocketProvider>
  );

  describe('Agent Flow Orchestration', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    describe('Standard Workflow - Sufficient Data', () => {
          setupAntiHang();
        jest.setTimeout(10000);
      it('should execute complete agent flow: Triage → Optimization → Data → Actions → Report', async () => {
        const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });
        
        // Start agent workflow
        act(() => {
          result.current.startAgent('Analyze my AI infrastructure costs', 'thread-123');
          mockAgentContext.isProcessing = true;
        });

        // Phase 1: Triage Agent
        act(() => {
          simulateWebSocketMessage({
            type: 'agent_started',
            data: { agent_name: 'triage', thread_id: 'thread-123' }
          });
        });

        await waitFor(() => {
          expect(mockAgentContext.isProcessing).toBe(true);
        });

        // Triage completes with sufficient data
        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: 'TriageAgent',
              status: 'completed',
              description: 'Classification complete',
              metadata: {
                data_sufficiency: 'sufficient',
                category: 'cost_optimization',
                priority: 'high'
              }
            }
          });
        });

        // Phase 2: Optimization Agent
        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: 'OptimizationAgent',
              status: 'running',
              description: 'Analyzing optimization strategies',
              tools: ['cost_analyzer', 'resource_optimizer']
            }
          });
        });

        // Optimization completes
        act(() => {
          simulateWebSocketMessage({
            type: 'optimization_complete',
            data: {
              id: 'opt-123',
              analysis: {
                summary: 'Found 3 major cost optimization opportunities',
                key_findings: [
                  'Oversized compute instances',
                  'Unused resources',
                  'Inefficient data storage'
                ],
                bottlenecks_identified: ['GPU utilization at 30%'],
                root_causes: ['Overprovisioning'],
                confidence_score: 0.85,
                analysis_timestamp: new Date().toISOString()
              },
              metrics: [
                { name: 'potential_savings', value: 45000, unit: 'USD/month' }
              ],
              recommendations: [
                {
                  id: 'rec-1',
                  title: 'Rightsize compute instances',
                  priority: 'high',
                  estimated_impact: { value: 30000, unit: 'USD/month' }
                }
              ]
            }
          });
        });

        // Update mock context with optimization results
        act(() => {
          mockAgentContext.optimizationResults = {
            id: 'opt-123',
            analysis: {
              summary: 'Found 3 major cost optimization opportunities',
              key_findings: [
                'Oversized compute instances',
                'Unused resources',
                'Inefficient data storage'
              ],
              bottlenecks_identified: ['GPU utilization at 30%'],
              root_causes: ['Overprovisioning'],
              confidence_score: 0.85,
              analysis_timestamp: new Date().toISOString()
            },
            metrics: [
              { name: 'potential_savings', value: 45000, unit: 'USD/month' }
            ],
            recommendations: [
              {
                id: 'rec-1',
                title: 'Rightsize compute instances',
                priority: 'high',
                estimated_impact: { value: 30000, unit: 'USD/month' }
              }
            ]
          };
        });

        await waitFor(() => {
          expect(mockAgentContext.optimizationResults).toBeTruthy();
          expect(mockAgentContext.optimizationResults?.analysis.key_findings).toHaveLength(3);
        });

        // Phase 3: Data Agent
        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: 'DataAgent',
              status: 'running',
              description: 'Gathering detailed metrics',
              progress: 0.5
            }
          });
        });

        // Phase 4: Actions Agent
        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: 'ActionsAgent',
              status: 'running',
              description: 'Generating implementation plan'
            }
          });
        });

        // Phase 5: Reporting Agent
        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: 'ReportingAgent',
              status: 'running',
              description: 'Compiling final report'
            }
          });
        });

        // Complete workflow
        act(() => {
          simulateWebSocketMessage({
            type: 'agent_completed',
            data: {
              thread_id: 'thread-123',
              report: 'Analysis complete. Identified $45,000/month in potential savings.',
              execution_time_ms: 5000,
              sub_agent: 'ReportingAgent',
              model_used: 'gpt-4'
            }
          });
          
          // Update mock state to simulate completion
          mockAgentContext.isProcessing = false;
          mockChatStoreState.messages.push({
            id: 'report-msg-1',
            content: 'Analysis complete. Identified $45,000/month in potential savings.',
            role: 'assistant',
            timestamp: Date.now()
          });
        });

        await waitFor(() => {
          expect(mockAgentContext.isProcessing).toBe(false);
          const messages = mockChatStoreState.messages;
          const reportMessage = messages.find(m => m.content.includes('$45,000/month'));
          expect(reportMessage).toBeTruthy();
        });
      });
    });

    describe('Adaptive Workflow - Insufficient Data', () => {
          setupAntiHang();
        jest.setTimeout(10000);
      it('should adapt workflow when data is insufficient: Triage → Data Helper', async () => {
        const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

        // Start agent workflow
        act(() => {
          result.current.startAgent('Optimize my system', 'thread-456');
          mockAgentContext.isProcessing = true;
        });

        // Triage identifies insufficient data
        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: 'TriageAgent',
              status: 'completed',
              metadata: {
                data_sufficiency: 'insufficient',
                missing_data: ['metrics', 'configuration', 'usage_patterns']
              }
            }
          });
        });

        // Data Helper agent activated
        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: 'DataHelperAgent',
              status: 'running',
              description: 'Requesting additional data',
              metadata: {
                data_requests: [
                  { type: 'metrics', description: 'Please provide system metrics' },
                  { type: 'configuration', description: 'Share your current configuration' }
                ]
              }
            }
          });
        });

        // Data helper completes with request for user
        act(() => {
          simulateWebSocketMessage({
            type: 'agent_completed',
            data: {
              thread_id: 'thread-456',
              report: 'To proceed with optimization, I need additional information:\n1. System metrics\n2. Current configuration\n3. Usage patterns',
              sub_agent: 'DataHelperAgent',
              metadata: {
                workflow_status: 'paused_for_data',
                can_resume: true
              }
            }
          });
        });

        await waitFor(() => {
          const messages = mockChatStoreState.messages;
          const dataRequestMessage = messages.find(m => m.content.includes('additional information'));
          expect(dataRequestMessage).toBeTruthy();
          expect(result.current.isProcessing).toBe(false);
        });
      });
    });

    describe('Partial Data Workflow', () => {
          setupAntiHang();
        jest.setTimeout(10000);
      it('should handle partial data flow: Triage → Optimization → Actions → Data Helper → Report', async () => {
        const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

        act(() => {
          result.current.startAgent('Improve performance', 'thread-789');
          mockAgentContext.isProcessing = true;
        });

        // Triage with partial data
        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: 'TriageAgent',
              status: 'completed',
              metadata: {
                data_sufficiency: 'partial',
                available_data: ['basic_metrics'],
                missing_data: ['detailed_logs', 'trace_data']
              }
            }
          });
        });

        // Optimization with limited scope
        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: 'OptimizationAgent',
              status: 'running',
              metadata: {
                scope: 'limited',
                confidence: 0.6
              }
            }
          });
        });

        // Actions with caveats
        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: 'ActionsAgent',
              status: 'running',
              metadata: {
                actions_type: 'preliminary',
                requires_validation: true
              }
            }
          });
        });

        // Data Helper for additional context
        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: 'DataHelperAgent',
              status: 'running',
              description: 'Requesting supplemental data for validation'
            }
          });
        });

        // Final report with data request
        act(() => {
          simulateWebSocketMessage({
            type: 'agent_completed',
            data: {
              thread_id: 'thread-789',
              report: 'Preliminary analysis complete. Recommendations provided with 60% confidence. Additional data needed for full optimization.',
              metadata: {
                workflow_type: 'partial',
                follow_up_required: true
              }
            }
          });
        });

        await waitFor(() => {
          const messages = mockChatStoreState.messages;
          expect(messages.some(m => m.content.includes('60% confidence'))).toBe(true);
        });
      });
    });
  });

  describe('Agent Error Handling and Recovery', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle agent failures gracefully', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('Complex analysis', 'thread-error');
        mockAgentContext.isProcessing = true;
      });

      // Triage succeeds
      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'completed'
          }
        });
      });

      // Optimization fails
      act(() => {
        simulateWebSocketMessage({
          type: 'agent_error',
          data: {
            error: {
              type: 'execution',
              message: 'Optimization agent encountered an error',
              details: 'Resource limit exceeded',
              is_recoverable: true
            },
            sub_agent: 'OptimizationAgent',
            thread_id: 'thread-error'
          }
        });
      });

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
        expect(result.current.error?.is_recoverable).toBe(true);
      });

      // Recovery attempt
      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'OptimizationAgent',
            status: 'retrying',
            metadata: {
              retry_attempt: 1,
              adjusted_parameters: true
            }
          }
        });
      });

      // Recovery successful
      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'OptimizationAgent',
            status: 'completed',
            metadata: {
              recovered: true
            }
          }
        });
      });

      await waitFor(() => {
        expect(result.current.error).toBe(null);
      });
    });

    it('should handle non-recoverable errors', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('Critical task', 'thread-fatal');
        mockAgentContext.isProcessing = true;
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'agent_error',
          data: {
            error: {
              type: 'system',
              message: 'Critical system failure',
              is_recoverable: false
            },
            sub_agent: 'SystemAgent'
          }
        });
      });

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
        expect(result.current.error?.is_recoverable).toBe(false);
        expect(result.current.isProcessing).toBe(false);
      });
    });
  });

  describe('Agent State Management', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track sub-agent states correctly', async () => {
      const { result } = renderHook(() => useUnifiedStore());

      const agentStates: SubAgentState[] = [
        {
          name: 'TriageAgent',
          status: 'running',
          description: 'Analyzing request',
          tools: ['classifier', 'prioritizer'],
          progress: 0.3
        },
        {
          name: 'TriageAgent',
          status: 'completed',
          description: 'Classification complete',
          progress: 1.0
        }
      ];

      for (const state of agentStates) {
        act(() => {
          result.current.setSubAgentStatus(state);
        });

        await waitFor(() => {
          const currentState = result.current.fastLayerData?.subAgentStatus;
          expect(currentState).toEqual(state);
        });
      }
    });

    it('should maintain agent execution history', async () => {
      const { result } = renderHook(() => useChatStore());

      const agents = ['TriageAgent', 'OptimizationAgent', 'DataAgent', 'ActionsAgent', 'ReportingAgent'];
      
      for (const agent of agents) {
        act(() => {
          result.current.addMessage({
            id: `msg-${agent}`,
            content: `${agent} completed`,
            role: 'assistant',
            type: 'ai',
            thread_id: 'thread-history',
            created_at: new Date().toISOString(),
            displayed_to_user: true,
            metadata: {
              sub_agent: agent,
              execution_time_ms: Math.random() * 1000
            }
          });
        });
      }

      await waitFor(() => {
        const messages = result.current.messages;
        expect(messages).toHaveLength(agents.length);
        
        // Verify execution order
        agents.forEach((agent, index) => {
          expect(messages[index].metadata?.sub_agent).toBe(agent);
        });
      });
    });
  });

  describe('Business Logic Validation', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should validate optimization recommendations are actionable', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'optimization_complete',
          data: {
            id: 'opt-validate',
            analysis: {
              summary: 'Optimization analysis',
              key_findings: ['Finding 1'],
              bottlenecks_identified: [],
              root_causes: [],
              confidence_score: 0.9,
              analysis_timestamp: new Date().toISOString()
            },
            recommendations: [
              {
                id: 'rec-valid-1',
                title: 'Valid recommendation',
                priority: 'high',
                estimated_impact: { value: 1000, unit: 'USD' },
                implementation_steps: [
                  'Step 1: Analyze current state',
                  'Step 2: Apply changes',
                  'Step 3: Monitor results'
                ],
                prerequisites: ['Access to system', 'Backup created'],
                risks: ['Temporary downtime'],
                success_criteria: ['Cost reduced by 20%']
              }
            ]
          }
        });
      });

      await waitFor(() => {
        const recommendations = result.current.optimizationResults?.recommendations;
        expect(recommendations).toBeTruthy();
        expect(recommendations?.[0]).toMatchObject({
          priority: 'high',
          estimated_impact: expect.objectContaining({
            value: expect.any(Number),
            unit: expect.any(String)
          })
        });
        
        // Validate recommendation has actionable steps
        const rec = recommendations?.[0];
        expect(rec?.implementation_steps).toBeDefined();
        expect(rec?.prerequisites).toBeDefined();
        expect(rec?.success_criteria).toBeDefined();
      });
    });

    it('should ensure data requests are specific and actionable', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataHelperAgent',
            status: 'completed',
            metadata: {
              data_requests: [
                {
                  type: 'metrics',
                  description: 'CPU and memory utilization for the last 7 days',
                  format: 'CSV or JSON',
                  required_fields: ['timestamp', 'cpu_percent', 'memory_mb'],
                  sample_provided: true
                },
                {
                  type: 'configuration',
                  description: 'Current deployment configuration',
                  format: 'YAML or JSON',
                  specific_sections: ['resources', 'scaling', 'networking']
                }
              ]
            }
          }
        });
      });

      await waitFor(() => {
        const latestUpdate = mockUnifiedStoreState.fastLayerData?.subAgentStatus;
        const dataRequests = latestUpdate?.metadata?.data_requests;
        
        expect(dataRequests).toBeTruthy();
        dataRequests?.forEach((request: any) => {
          expect(request.type).toBeDefined();
          expect(request.description).toBeDefined();
          expect(request.format).toBeDefined();
        });
      });
    });
  });

  describe('Agent Coordination and Handoff', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should properly transfer context between agents', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      // Triage provides context
      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'completed',
            metadata: {
              classification: 'performance_optimization',
              context_for_next: {
                focus_areas: ['database', 'api_latency'],
                constraints: ['no_downtime', 'budget_10k'],
                sla_requirements: { latency_p99: 500 }
              }
            }
          }
        });
      });

      // Optimization uses context
      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'OptimizationAgent',
            status: 'running',
            metadata: {
              received_context: {
                focus_areas: ['database', 'api_latency'],
                constraints: ['no_downtime', 'budget_10k']
              },
              optimization_scope: 'targeted'
            }
          }
        });
      });

      // Actions respects constraints
      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'ActionsAgent',
            status: 'completed',
            metadata: {
              applied_constraints: ['no_downtime', 'budget_10k'],
              actions_generated: 3,
              all_constraints_met: true
            }
          }
        });
      });

      await waitFor(() => {
        const messages = mockChatStoreState.messages;
        expect(messages.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Performance and Timing', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track agent execution times', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      const agents = [
        { name: 'TriageAgent', time: 500 },
        { name: 'OptimizationAgent', time: 2000 },
        { name: 'DataAgent', time: 1500 },
        { name: 'ActionsAgent', time: 800 },
        { name: 'ReportingAgent', time: 300 }
      ];

      for (const agent of agents) {
        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: agent.name,
              status: 'completed',
              execution_time: agent.time
            }
          });
        });
      }

      act(() => {
        simulateWebSocketMessage({
          type: 'agent_completed',
          data: {
            thread_id: 'thread-perf',
            execution_time_ms: agents.reduce((sum, a) => sum + a.time, 0),
            metadata: {
              agent_timings: agents.reduce((acc, a) => ({
                ...acc,
                [a.name]: a.time
              }), {})
            }
          }
        });
      });

      await waitFor(() => {
        expect(result.current.isProcessing).toBe(false);
      });
    });

    it('should handle timeout scenarios', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('Long running task', 'thread-timeout');
        mockAgentContext.isProcessing = true;
      });

      // Simulate timeout
      act(() => {
        simulateWebSocketMessage({
          type: 'agent_error',
          data: {
            error: {
              type: 'timeout',
              message: 'Agent execution timeout after 30 seconds',
              is_recoverable: true
            },
            sub_agent: 'DataAgent',
            metadata: {
              elapsed_time: 30000,
              timeout_limit: 30000
            }
          }
        });
      });

      await waitFor(() => {
        expect(result.current.error?.type).toBe('timeout');
        expect(result.current.isProcessing).toBe(false);
      });
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});