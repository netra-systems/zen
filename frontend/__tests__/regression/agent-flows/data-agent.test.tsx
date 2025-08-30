/**
 * Data Agent and Data Helper Agent Flow Tests
 * 
 * Tests for Data Agent and Data Helper Agent which handle:
 * - Data collection and aggregation
 * - Metrics gathering
 * - Data validation
 * - Requesting missing data from users
 * - Data transformation and insights
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { AgentProvider, useAgentContext } from '@/providers/AgentProvider';
import { useChatStore } from '@/store/chatStore';
import { useUnifiedChatStore } from '@/store/unified-chat';
import type { WebSocketMessage } from '@/types/unified';

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

describe('Data Agent Flow Tests', () => {
  let wsEventHandlers: { [key: string]: Function[] } = {};
  let chatStore: ReturnType<typeof useChatStore>;
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

    chatStore = useChatStore.getState();
    unifiedStore = useUnifiedChatStore.getState();
    chatStore.clearMessages();
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

  describe('Data Collection and Aggregation', () => {
    it('should collect and aggregate system metrics', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataAgent',
            status: 'running',
            description: 'Collecting system metrics',
            tools: ['metrics_collector', 'database_query', 'log_analyzer'],
            progress: 0.3
          }
        });
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataAgent',
            status: 'running',
            description: 'Aggregating performance data',
            progress: 0.6,
            metadata: {
              data_sources_accessed: ['prometheus', 'cloudwatch', 'application_logs'],
              metrics_collected: 1247,
              time_range: '7_days'
            }
          }
        });
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataAgent',
            status: 'completed',
            metadata: {
              data_summary: {
                total_metrics: 1247,
                aggregated_insights: 15,
                anomalies_detected: 3,
                data_quality_score: 0.92
              },
              key_metrics: {
                avg_cpu_utilization: 0.67,
                avg_memory_usage: 0.82,
                p99_latency: 450,
                error_rate: 0.002
              }
            }
          }
        });
      });

      await waitFor(() => {
        const state = unifiedStore.getState().fastLayerData?.subAgentStatus;
        expect(state?.metadata?.data_summary?.total_metrics).toBe(1247);
        expect(state?.metadata?.key_metrics?.avg_cpu_utilization).toBe(0.67);
      });
    });

    it('should handle multiple data source integration', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      const dataSources = [
        { name: 'database', status: 'connected', records: 50000 },
        { name: 'api_metrics', status: 'connected', records: 12000 },
        { name: 'log_files', status: 'partial', records: 8000 },
        { name: 'config_files', status: 'connected', records: 25 }
      ];

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataAgent',
            status: 'running',
            metadata: {
              phase: 'data_source_connection',
              sources: dataSources
            }
          }
        });
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataAgent',
            status: 'completed',
            metadata: {
              integration_summary: {
                total_sources: 4,
                successful_connections: 3,
                partial_connections: 1,
                total_records_processed: 70025,
                data_completeness: 0.88
              }
            }
          }
        });
      });

      await waitFor(() => {
        const state = unifiedStore.getState().fastLayerData?.subAgentStatus;
        expect(state?.metadata?.integration_summary?.total_records_processed).toBe(70025);
        expect(state?.metadata?.integration_summary?.data_completeness).toBe(0.88);
      });
    });
  });

  describe('Data Helper Agent - Missing Data Scenarios', () => {
    it('should request specific missing data from user', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataHelperAgent',
            status: 'running',
            description: 'Identifying missing data requirements'
          }
        });
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataHelperAgent',
            status: 'completed',
            metadata: {
              data_requests: [
                {
                  id: 'req-1',
                  type: 'metrics',
                  priority: 'high',
                  description: 'CPU and Memory utilization metrics',
                  format: 'CSV or JSON',
                  time_range: 'Last 7-30 days',
                  required_fields: ['timestamp', 'cpu_percent', 'memory_mb', 'instance_id'],
                  sample: {
                    timestamp: '2024-01-15T10:00:00Z',
                    cpu_percent: 75.5,
                    memory_mb: 8192,
                    instance_id: 'i-abc123'
                  }
                },
                {
                  id: 'req-2',
                  type: 'configuration',
                  priority: 'medium',
                  description: 'Current deployment configuration',
                  format: 'YAML or JSON',
                  required_sections: ['resources', 'scaling_policy', 'network_config'],
                  validation_rules: ['Must include memory limits', 'Must specify replica count']
                }
              ],
              instructions_for_user: 'Please provide the requested data to continue with optimization analysis'
            }
          }
        });
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'agent_completed',
          data: {
            thread_id: 'thread-helper',
            report: 'To proceed with the analysis, I need the following data:\n\n1. **System Metrics** (High Priority)\n   - Format: CSV or JSON\n   - Time Range: Last 7-30 days\n   - Required: CPU %, Memory usage, Instance IDs\n\n2. **Configuration Files** (Medium Priority)\n   - Format: YAML or JSON\n   - Sections: Resources, Scaling, Network\n\nPlease upload or paste the data when ready.',
            sub_agent: 'DataHelperAgent'
          }
        });
      });

      await waitFor(() => {
        const messages = chatStore.getState().messages;
        const dataRequest = messages.find(m => m.content.includes('System Metrics'));
        expect(dataRequest).toBeTruthy();
        expect(dataRequest?.content).toContain('High Priority');
      });
    });

    it('should validate user-provided data', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      // User provides data
      act(() => {
        result.current.sendMessage('Here is my metrics data: [CSV data attached]');
      });

      // Data Helper validates
      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataHelperAgent',
            status: 'running',
            description: 'Validating provided data',
            metadata: {
              validation_phase: 'schema_check'
            }
          }
        });
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataHelperAgent',
            status: 'completed',
            metadata: {
              validation_result: {
                status: 'partial_success',
                valid_records: 950,
                invalid_records: 50,
                missing_fields: ['instance_id'],
                data_issues: [
                  {
                    type: 'missing_field',
                    field: 'instance_id',
                    impact: 'Cannot correlate metrics to specific instances',
                    suggestion: 'Add instance_id column or provide instance mapping'
                  },
                  {
                    type: 'data_gap',
                    time_range: '2024-01-10 to 2024-01-12',
                    impact: 'Missing 2 days of data',
                    suggestion: 'Provide missing data or proceed with partial analysis'
                  }
                ],
                usable: true,
                completeness: 0.85
              }
            }
          }
        });
      });

      await waitFor(() => {
        const state = unifiedStore.getState().fastLayerData?.subAgentStatus;
        expect(state?.metadata?.validation_result?.status).toBe('partial_success');
        expect(state?.metadata?.validation_result?.completeness).toBe(0.85);
      });
    });
  });

  describe('Data Insights and Analysis', () => {
    it('should generate insights from collected data', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataAgent',
            status: 'running',
            description: 'Analyzing patterns and trends',
            progress: 0.7
          }
        });
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataAgent',
            status: 'completed',
            metadata: {
              insights: [
                {
                  type: 'pattern',
                  title: 'Daily traffic spike',
                  description: 'Consistent 3x traffic increase between 2-4 PM EST',
                  confidence: 0.95,
                  impact: 'high',
                  recommendation: 'Implement auto-scaling for afternoon peak'
                },
                {
                  type: 'anomaly',
                  title: 'Memory leak detected',
                  description: 'Gradual memory increase without corresponding load',
                  confidence: 0.78,
                  impact: 'medium',
                  affected_services: ['api-gateway', 'worker-pool']
                },
                {
                  type: 'optimization_opportunity',
                  title: 'Underutilized resources during night',
                  description: 'CPU utilization drops to 10% from 11 PM to 6 AM',
                  potential_savings: '$500/month',
                  confidence: 0.92
                }
              ],
              statistical_summary: {
                mean_cpu: 45.2,
                std_dev_cpu: 18.7,
                percentiles: {
                  p50: 42,
                  p95: 78,
                  p99: 92
                }
              }
            }
          }
        });
      });

      await waitFor(() => {
        const state = unifiedStore.getState().fastLayerData?.subAgentStatus;
        expect(state?.metadata?.insights).toHaveLength(3);
        expect(state?.metadata?.insights?.[0].type).toBe('pattern');
        expect(state?.metadata?.statistical_summary?.mean_cpu).toBe(45.2);
      });
    });

    it('should correlate data across multiple dimensions', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataAgent',
            status: 'completed',
            metadata: {
              correlations: [
                {
                  variables: ['request_rate', 'response_time'],
                  correlation_coefficient: 0.87,
                  relationship: 'positive',
                  interpretation: 'Higher request rates correlate with increased response times'
                },
                {
                  variables: ['memory_usage', 'garbage_collection_frequency'],
                  correlation_coefficient: 0.92,
                  relationship: 'positive',
                  interpretation: 'Memory pressure triggers more frequent GC cycles'
                },
                {
                  variables: ['cache_hit_rate', 'database_load'],
                  correlation_coefficient: -0.78,
                  relationship: 'negative',
                  interpretation: 'Better cache performance reduces database load'
                }
              ],
              causality_analysis: {
                primary_bottleneck: 'database_connections',
                cascade_effects: ['api_latency', 'user_experience', 'retry_storms'],
                confidence: 0.82
              }
            }
          }
        });
      });

      await waitFor(() => {
        const state = unifiedStore.getState().fastLayerData?.subAgentStatus;
        expect(state?.metadata?.correlations).toHaveLength(3);
        expect(state?.metadata?.causality_analysis?.primary_bottleneck).toBe('database_connections');
      });
    });
  });

  describe('Real-time Data Streaming', () => {
    it('should handle streaming data updates', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      // Simulate streaming updates
      const updates = [
        { timestamp: '10:00:00', cpu: 45, memory: 60 },
        { timestamp: '10:00:30', cpu: 48, memory: 62 },
        { timestamp: '10:01:00', cpu: 52, memory: 65 },
        { timestamp: '10:01:30', cpu: 78, memory: 75 }, // Spike
        { timestamp: '10:02:00', cpu: 55, memory: 68 }
      ];

      for (const update of updates) {
        act(() => {
          simulateWebSocketMessage({
            type: 'sub_agent_update',
            data: {
              name: 'DataAgent',
              status: 'running',
              description: 'Monitoring real-time metrics',
              metadata: {
                stream_update: update,
                alert: update.cpu > 70 ? {
                  type: 'cpu_spike',
                  severity: 'warning',
                  value: update.cpu,
                  threshold: 70
                } : null
              }
            }
          });
        });

        // Add small delay to simulate real-time
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataAgent',
            status: 'completed',
            metadata: {
              streaming_summary: {
                total_updates: 5,
                alerts_triggered: 1,
                max_cpu: 78,
                avg_cpu: 55.6
              }
            }
          }
        });
      });

      await waitFor(() => {
        const state = unifiedStore.getState().fastLayerData?.subAgentStatus;
        expect(state?.metadata?.streaming_summary?.alerts_triggered).toBe(1);
        expect(state?.metadata?.streaming_summary?.max_cpu).toBe(78);
      });
    });
  });

  describe('Data Export and Formatting', () => {
    it('should format data for different consumption needs', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataAgent',
            status: 'completed',
            metadata: {
              data_exports: {
                summary_report: {
                  format: 'markdown',
                  size_kb: 12,
                  sections: ['executive_summary', 'key_metrics', 'recommendations']
                },
                detailed_metrics: {
                  format: 'csv',
                  size_kb: 450,
                  rows: 10000,
                  columns: ['timestamp', 'cpu', 'memory', 'disk', 'network']
                },
                visualization_data: {
                  format: 'json',
                  size_kb: 85,
                  charts: ['time_series', 'heatmap', 'correlation_matrix']
                }
              },
              export_links: {
                download_csv: '/api/export/metrics.csv',
                download_json: '/api/export/data.json',
                view_dashboard: '/dashboard/analysis/123'
              }
            }
          }
        });
      });

      await waitFor(() => {
        const state = unifiedStore.getState().fastLayerData?.subAgentStatus;
        expect(state?.metadata?.data_exports).toBeTruthy();
        expect(state?.metadata?.data_exports?.detailed_metrics?.rows).toBe(10000);
        expect(state?.metadata?.export_links?.download_csv).toBeTruthy();
      });
    });
  });

  describe('Error Handling in Data Collection', () => {
    it('should handle data source connection failures', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataAgent',
            status: 'running',
            metadata: {
              connection_attempts: [
                { source: 'prometheus', status: 'success' },
                { source: 'elasticsearch', status: 'failed', error: 'Connection timeout' },
                { source: 'cloudwatch', status: 'success' }
              ]
            }
          }
        });
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataAgent',
            status: 'completed',
            metadata: {
              data_collection_status: 'partial',
              successful_sources: 2,
              failed_sources: 1,
              data_coverage: 0.75,
              mitigation: 'Proceeding with available data, estimates used for missing metrics',
              limitations: ['Elasticsearch logs unavailable', 'Error analysis incomplete']
            }
          }
        });
      });

      await waitFor(() => {
        const state = unifiedStore.getState().fastLayerData?.subAgentStatus;
        expect(state?.metadata?.data_collection_status).toBe('partial');
        expect(state?.metadata?.data_coverage).toBe(0.75);
        expect(state?.metadata?.limitations).toContain('Elasticsearch logs unavailable');
      });
    });

    it('should handle data quality issues', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'DataAgent',
            status: 'completed',
            metadata: {
              data_quality_issues: [
                {
                  type: 'missing_values',
                  affected_metrics: ['disk_io'],
                  percentage: 15,
                  impact: 'medium',
                  handling: 'interpolation'
                },
                {
                  type: 'outliers',
                  affected_metrics: ['response_time'],
                  count: 23,
                  impact: 'low',
                  handling: 'flagged_for_review'
                },
                {
                  type: 'inconsistent_units',
                  affected_metrics: ['memory'],
                  description: 'Mixed MB and GB values',
                  impact: 'high',
                  handling: 'normalized_to_MB'
                }
              ],
              overall_quality_score: 0.78,
              fitness_for_analysis: 'acceptable_with_caveats'
            }
          }
        });
      });

      await waitFor(() => {
        const state = unifiedStore.getState().fastLayerData?.subAgentStatus;
        expect(state?.metadata?.data_quality_issues).toHaveLength(3);
        expect(state?.metadata?.overall_quality_score).toBe(0.78);
      });
    });
  });
});