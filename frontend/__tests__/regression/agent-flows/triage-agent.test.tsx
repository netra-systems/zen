/**
 * Triage Agent Flow Tests
 * 
 * Tests for the Triage Agent which is the first agent in the orchestration flow.
 * The Triage Agent is responsible for:
 * - Classifying user requests
 * - Determining data sufficiency
 * - Setting workflow path
 * - Prioritizing requests
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { AgentProvider, useAgentContext } from '@/providers/AgentProvider';
import { useUnifiedChatStore } from '@/store/unified-chat';
import type { WebSocketMessage, SubAgentState } from '@/types/unified';

// Mock WebSocket
const mockWebSocket = {
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN,
};

global.WebSocket = jest.fn(() => mockWebSocket) as any;

// Mock stores with getState
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

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: Object.assign(
    jest.fn(() => mockUnifiedStoreState),
    {
      getState: jest.fn(() => mockUnifiedStoreState)
    }
  )
}));

describe('Triage Agent Flow Tests', () => {
  let wsEventHandlers: { [key: string]: Function[] } = {};
  let unifiedStore: ReturnType<typeof useUnifiedChatStore>;

  beforeEach(() => {
    jest.clearAllMocks();
    wsEventHandlers = {};
    
    mockWebSocket.addEventListener.mockImplementation((event: string, handler: Function) => {
      if (!wsEventHandlers[event]) {
        wsEventHandlers[event] = [];
      }
      wsEventHandlers[event].push(handler);
    });

    unifiedStore = useUnifiedChatStore.getState();
    unifiedStore.resetState();
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

  describe('Request Classification', () => {
    it('should classify cost optimization requests correctly', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('How can I reduce my AI infrastructure costs?', 'thread-cost');
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'running',
            description: 'Analyzing request type'
          }
        });
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'completed',
            metadata: {
              classification: 'cost_optimization',
              confidence: 0.95,
              keywords_detected: ['reduce', 'costs', 'infrastructure'],
              suggested_focus: ['resource_utilization', 'pricing_optimization', 'waste_reduction']
            }
          }
        });
      });

      await waitFor(() => {
        const state = mockUnifiedStoreState.fastLayerData?.subAgentStatus;
        expect(state?.metadata?.classification).toBe('cost_optimization');
        expect(state?.metadata?.confidence).toBeGreaterThan(0.9);
      });
    });

    it('should classify performance optimization requests', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('My models are running slowly', 'thread-perf');
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'completed',
            metadata: {
              classification: 'performance_optimization',
              confidence: 0.88,
              keywords_detected: ['slowly', 'models', 'running'],
              performance_areas: ['latency', 'throughput', 'response_time']
            }
          }
        });
      });

      await waitFor(() => {
        const state = mockUnifiedStoreState.fastLayerData?.subAgentStatus;
        expect(state?.metadata?.classification).toBe('performance_optimization');
      });
    });

    it('should classify debugging/troubleshooting requests', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('Why is my agent failing with timeout errors?', 'thread-debug');
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'completed',
            metadata: {
              classification: 'troubleshooting',
              confidence: 0.92,
              error_type_detected: 'timeout',
              requires_logs: true,
              suggested_diagnostics: ['check_timeout_settings', 'analyze_execution_time', 'review_resource_limits']
            }
          }
        });
      });

      await waitFor(() => {
        const state = mockUnifiedStoreState.fastLayerData?.subAgentStatus;
        expect(state?.metadata?.classification).toBe('troubleshooting');
        expect(state?.metadata?.error_type_detected).toBe('timeout');
      });
    });
  });

  describe('Data Sufficiency Evaluation', () => {
    it('should determine sufficient data scenario', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('Analyze costs for thread-123 in corpus-abc', 'thread-sufficient');
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'completed',
            metadata: {
              data_sufficiency: 'sufficient',
              data_available: {
                thread_id: 'thread-123',
                corpus_id: 'corpus-abc',
                metrics_available: true,
                configuration_available: true,
                historical_data: true
              },
              confidence_in_data: 0.95,
              workflow_recommendation: 'full_analysis'
            }
          }
        });
      });

      await waitFor(() => {
        const state = mockUnifiedStoreState.fastLayerData?.subAgentStatus;
        expect(state?.metadata?.data_sufficiency).toBe('sufficient');
        expect(state?.metadata?.workflow_recommendation).toBe('full_analysis');
      });
    });

    it('should identify insufficient data and request specifics', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('Optimize my system', 'thread-insufficient');
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'completed',
            metadata: {
              data_sufficiency: 'insufficient',
              missing_critical_data: [
                {
                  type: 'system_metrics',
                  description: 'No performance metrics available',
                  impact: 'Cannot analyze bottlenecks'
                },
                {
                  type: 'configuration',
                  description: 'System configuration unknown',
                  impact: 'Cannot suggest optimizations'
                }
              ],
              data_collection_required: true,
              workflow_recommendation: 'data_collection_first'
            }
          }
        });
      });

      await waitFor(() => {
        const state = mockUnifiedStoreState.fastLayerData?.subAgentStatus;
        expect(state?.metadata?.data_sufficiency).toBe('insufficient');
        expect(state?.metadata?.missing_critical_data).toHaveLength(2);
        expect(state?.metadata?.workflow_recommendation).toBe('data_collection_first');
      });
    });

    it('should handle partial data scenarios', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('Improve performance for corpus-xyz', 'thread-partial');
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'completed',
            metadata: {
              data_sufficiency: 'partial',
              available_data: ['basic_metrics', 'corpus_info'],
              missing_data: ['detailed_logs', 'trace_data', 'cost_breakdown'],
              analysis_limitations: [
                'Can provide high-level recommendations',
                'Cannot perform deep root cause analysis',
                'Cost optimizations will be estimates'
              ],
              workflow_recommendation: 'limited_analysis_with_caveats'
            }
          }
        });
      });

      await waitFor(() => {
        const state = mockUnifiedStoreState.fastLayerData?.subAgentStatus;
        expect(state?.metadata?.data_sufficiency).toBe('partial');
        expect(state?.metadata?.analysis_limitations).toBeTruthy();
      });
    });
  });

  describe('Priority Assignment', () => {
    it('should assign high priority to production issues', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('Production system is down!', 'thread-urgent');
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'completed',
            metadata: {
              priority: 'critical',
              priority_score: 10,
              priority_factors: [
                'production_environment',
                'system_down',
                'urgent_language'
              ],
              estimated_impact: 'high',
              recommended_response_time: 'immediate'
            }
          }
        });
      });

      await waitFor(() => {
        const state = mockUnifiedStoreState.fastLayerData?.subAgentStatus;
        expect(state?.metadata?.priority).toBe('critical');
        expect(state?.metadata?.priority_score).toBe(10);
      });
    });

    it('should assign appropriate priority based on impact', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      const testCases = [
        {
          request: 'Minor UI improvement suggestion',
          expectedPriority: 'low',
          expectedScore: 2
        },
        {
          request: 'Optimize batch processing performance',
          expectedPriority: 'medium',
          expectedScore: 5
        },
        {
          request: 'Security vulnerability detected',
          expectedPriority: 'high',
          expectedScore: 9
        }
      ];

      for (const testCase of testCases) {
        act(() => {
          result.current.startAgent(testCase.request, `thread-${testCase.expectedPriority}`);
        });

        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: 'TriageAgent',
              status: 'completed',
              metadata: {
                priority: testCase.expectedPriority,
                priority_score: testCase.expectedScore
              }
            }
          });
        });

        await waitFor(() => {
          const state = mockUnifiedStoreState.fastLayerData?.subAgentStatus;
          expect(state?.metadata?.priority).toBe(testCase.expectedPriority);
        });
      }
    });
  });

  describe('Workflow Path Determination', () => {
    it('should route to skip optimization for simple queries', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('What is the status of my system?', 'thread-simple');
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'completed',
            metadata: {
              classification: 'status_check',
              workflow_path: 'skip_optimization',
              skip_agents: ['OptimizationAgent', 'ActionsAgent'],
              direct_to: 'DataAgent',
              reason: 'Simple status query does not require optimization'
            }
          }
        });
      });

      await waitFor(() => {
        const state = mockUnifiedStoreState.fastLayerData?.subAgentStatus;
        expect(state?.metadata?.workflow_path).toBe('skip_optimization');
        expect(state?.metadata?.skip_agents).toContain('OptimizationAgent');
      });
    });

    it('should route complex requests through full workflow', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('Comprehensive analysis and optimization of my AI infrastructure with implementation plan', 'thread-complex');
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'completed',
            metadata: {
              classification: 'comprehensive_analysis',
              workflow_path: 'full_workflow',
              required_agents: ['OptimizationAgent', 'DataAgent', 'ActionsAgent', 'ReportingAgent'],
              estimated_duration: 'extended',
              complexity_score: 9
            }
          }
        });
      });

      await waitFor(() => {
        const state = mockUnifiedStoreState.fastLayerData?.subAgentStatus;
        expect(state?.metadata?.workflow_path).toBe('full_workflow');
        expect(state?.metadata?.required_agents).toHaveLength(4);
      });
    });
  });

  describe('Context Preparation for Next Agents', () => {
    it('should prepare context for optimization agent', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('Reduce costs for GPU workloads', 'thread-context');
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'completed',
            metadata: {
              classification: 'cost_optimization',
              context_for_optimization: {
                focus_area: 'gpu_workloads',
                optimization_goals: ['cost_reduction', 'maintain_performance'],
                constraints: {
                  performance_degradation_limit: '5%',
                  implementation_timeline: '30_days'
                },
                baseline_metrics: {
                  current_cost: 50000,
                  current_utilization: 0.4
                }
              }
            }
          }
        });
      });

      await waitFor(() => {
        const state = mockUnifiedStoreState.fastLayerData?.subAgentStatus;
        expect(state?.metadata?.context_for_optimization).toBeTruthy();
        expect(state?.metadata?.context_for_optimization?.focus_area).toBe('gpu_workloads');
      });
    });
  });

  describe('Error Scenarios', () => {
    it('should handle classification uncertainty', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('asdkfj qwerty xyz', 'thread-unclear');
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'TriageAgent',
            status: 'completed',
            metadata: {
              classification: 'unclear',
              confidence: 0.2,
              fallback_action: 'request_clarification',
              suggested_prompts: [
                'Could you provide more details about what you need help with?',
                'What specific aspect of your system would you like to analyze?'
              ]
            }
          }
        });
      });

      await waitFor(() => {
        const state = mockUnifiedStoreState.fastLayerData?.subAgentStatus;
        expect(state?.metadata?.classification).toBe('unclear');
        expect(state?.metadata?.confidence).toBeLessThan(0.3);
        expect(state?.metadata?.fallback_action).toBe('request_clarification');
      });
    });

    it('should handle triage agent failures gracefully', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        result.current.startAgent('Analyze system', 'thread-fail');
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'agent_error',
          data: {
            error: {
              type: 'execution',
              message: 'Triage agent failed to process request',
              details: 'LLM timeout',
              is_recoverable: true
            },
            sub_agent: 'TriageAgent',
            metadata: {
              fallback_classification: 'general_analysis',
              using_defaults: true
            }
          }
        });
      });

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
        expect(result.current.error?.sub_agent).toBe('TriageAgent');
      });
    });
  });
});