/**
 * Optimization Agent Flow Tests
 * 
 * Tests for the Optimization Agent which handles:
 * - Strategy generation
 * - Cost optimization
 * - Performance optimization
 * - Resource optimization
 * - Trade-off analysis
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { AgentProvider, useAgentContext } from '@/providers/AgentProvider';
import { useChatStore } from '@/store/chatStore';
import type { WebSocketMessage, OptimizationResults } from '@/types/unified';

// Mock WebSocket
const mockWebSocket = {
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN,
};

global.WebSocket = jest.fn(() => mockWebSocket) as any;

describe('Optimization Agent Flow Tests', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let wsEventHandlers: { [key: string]: Function[] } = {};
  let chatStore: ReturnType<typeof useChatStore>;

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
    chatStore.clearMessages();
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

  describe('Cost Optimization Strategies', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should generate comprehensive cost optimization strategies', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'OptimizationAgent',
            status: 'running',
            description: 'Analyzing cost optimization opportunities',
            tools: ['cost_analyzer', 'pricing_calculator', 'resource_optimizer']
          }
        });
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'optimization_complete',
          data: {
            id: 'opt-cost-123',
            status: 'completed',
            created_at: new Date().toISOString(),
            analysis: {
              summary: 'Identified 5 major cost optimization opportunities totaling $45,000/month savings',
              key_findings: [
                'Over-provisioned GPU instances running at 30% utilization',
                'Unused reserved instances costing $8,000/month',
                'Inefficient data transfer patterns causing $5,000/month in egress fees',
                'Redundant storage across multiple regions',
                'Development environments running 24/7 unnecessarily'
              ],
              bottlenecks_identified: [
                'GPU memory underutilization',
                'Network egress patterns',
                'Storage duplication'
              ],
              root_causes: [
                'Initial overestimation of resource needs',
                'Lack of automated shutdown policies',
                'No data lifecycle management'
              ],
              confidence_score: 0.88,
              analysis_timestamp: new Date().toISOString()
            },
            metrics: [
              { name: 'current_monthly_cost', value: 125000, unit: 'USD' },
              { name: 'potential_monthly_savings', value: 45000, unit: 'USD' },
              { name: 'savings_percentage', value: 36, unit: '%' },
              { name: 'implementation_effort', value: 3, unit: 'weeks' }
            ],
            recommendations: [
              {
                id: 'rec-1',
                title: 'Rightsize GPU instances',
                priority: 'high',
                estimated_impact: { value: 20000, unit: 'USD/month' },
                implementation_steps: [
                  'Analyze actual GPU utilization patterns',
                  'Identify instances that can be downsized',
                  'Test performance with smaller instances',
                  'Migrate workloads during maintenance window'
                ],
                prerequisites: ['Performance baseline established', 'Backup strategy in place'],
                risks: ['Potential performance impact if sizing is too aggressive'],
                success_criteria: ['Cost reduced by $20k/month', 'Performance maintained within 5% of baseline'],
                estimated_roi: { months_to_break_even: 0.5, total_savings_year_1: 240000 }
              },
              {
                id: 'rec-2',
                title: 'Implement automated shutdown for dev environments',
                priority: 'high',
                estimated_impact: { value: 8000, unit: 'USD/month' },
                implementation_steps: [
                  'Deploy shutdown scheduler',
                  'Configure shutdown/startup schedules',
                  'Implement override mechanism for critical work',
                  'Monitor and adjust schedules based on usage'
                ],
                prerequisites: ['Environment tagging completed', 'Team schedules documented'],
                risks: ['Developer friction if schedules are too restrictive'],
                success_criteria: ['70% reduction in dev environment runtime', 'No impact on developer productivity']
              }
            ]
          }
        });
      });

      await waitFor(() => {
        const optimizationResults = result.current.optimizationResults;
        expect(optimizationResults).toBeTruthy();
        expect(optimizationResults?.analysis.key_findings).toHaveLength(5);
        expect(optimizationResults?.metrics.find(m => m.name === 'potential_monthly_savings')?.value).toBe(45000);
        expect(optimizationResults?.recommendations[0].estimated_roi).toBeTruthy();
      });
    });

    it('should provide tiered optimization strategies based on risk tolerance', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'optimization_complete',
          data: {
            id: 'opt-tiered',
            analysis: {
              summary: 'Tiered optimization strategies based on risk tolerance',
              key_findings: ['Multiple optimization paths available'],
              bottlenecks_identified: [],
              root_causes: [],
              confidence_score: 0.85,
              analysis_timestamp: new Date().toISOString()
            },
            recommendations: [
              {
                id: 'conservative',
                title: 'Conservative optimization (Low Risk)',
                priority: 'medium',
                estimated_impact: { value: 10000, unit: 'USD/month' },
                metadata: {
                  risk_level: 'low',
                  implementation_time: '1 week',
                  rollback_difficulty: 'easy',
                  performance_impact: 'none'
                }
              },
              {
                id: 'balanced',
                title: 'Balanced optimization (Medium Risk)',
                priority: 'high',
                estimated_impact: { value: 25000, unit: 'USD/month' },
                metadata: {
                  risk_level: 'medium',
                  implementation_time: '2-3 weeks',
                  rollback_difficulty: 'moderate',
                  performance_impact: 'minimal'
                }
              },
              {
                id: 'aggressive',
                title: 'Aggressive optimization (High Risk)',
                priority: 'medium',
                estimated_impact: { value: 45000, unit: 'USD/month' },
                metadata: {
                  risk_level: 'high',
                  implementation_time: '4-6 weeks',
                  rollback_difficulty: 'complex',
                  performance_impact: 'potential 5-10% degradation'
                }
              }
            ]
          }
        });
      });

      await waitFor(() => {
        const recommendations = result.current.optimizationResults?.recommendations;
        expect(recommendations).toHaveLength(3);
        
        const conservative = recommendations?.find(r => r.id === 'conservative');
        const aggressive = recommendations?.find(r => r.id === 'aggressive');
        
        expect(conservative?.metadata?.risk_level).toBe('low');
        expect(aggressive?.metadata?.risk_level).toBe('high');
        expect(aggressive?.estimated_impact.value).toBeGreaterThan(conservative?.estimated_impact.value || 0);
      });
    });
  });

  describe('Performance Optimization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should identify and optimize performance bottlenecks', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'sub_agent_update',
          data: {
            name: 'OptimizationAgent',
            status: 'running',
            description: 'Analyzing performance bottlenecks',
            metadata: {
              analysis_type: 'performance',
              metrics_analyzed: ['latency', 'throughput', 'error_rate', 'cpu_utilization']
            }
          }
        });
      });

      act(() => {
        simulateWebSocketMessage({
          type: 'optimization_complete',
          data: {
            id: 'opt-perf',
            analysis: {
              summary: 'Critical performance bottlenecks identified in data pipeline',
              key_findings: [
                'Database queries taking 3x longer than expected',
                'API gateway adding 200ms unnecessary latency',
                'Inefficient serialization causing CPU spikes'
              ],
              bottlenecks_identified: [
                'Database connection pooling',
                'API gateway configuration',
                'JSON serialization library'
              ],
              root_causes: [
                'Insufficient connection pool size',
                'Synchronous processing in API gateway',
                'Using reflection-based JSON library'
              ],
              confidence_score: 0.92,
              analysis_timestamp: new Date().toISOString()
            },
            metrics: [
              { name: 'current_p99_latency', value: 850, unit: 'ms' },
              { name: 'optimized_p99_latency', value: 250, unit: 'ms' },
              { name: 'latency_reduction', value: 70, unit: '%' },
              { name: 'throughput_increase', value: 3.2, unit: 'x' }
            ],
            recommendations: [
              {
                id: 'db-optimization',
                title: 'Optimize database connection pooling',
                priority: 'critical',
                estimated_impact: { value: 400, unit: 'ms latency reduction' },
                implementation_steps: [
                  'Increase connection pool size from 10 to 50',
                  'Implement connection pooling warmup',
                  'Add connection health checks',
                  'Configure optimal timeout values'
                ],
                code_changes: {
                  files_affected: ['config/database.yaml', 'src/db/connection.py'],
                  lines_of_code: 50,
                  complexity: 'low'
                }
              }
            ]
          }
        });
      });

      await waitFor(() => {
        const results = result.current.optimizationResults;
        expect(results?.analysis.bottlenecks_identified).toContain('Database connection pooling');
        expect(results?.metrics.find(m => m.name === 'latency_reduction')?.value).toBe(70);
        expect(results?.recommendations[0].code_changes).toBeTruthy();
      });
    });

    it('should optimize for different performance goals', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      const performanceGoals = [
        { goal: 'minimize_latency', target: 'p99 < 100ms' },
        { goal: 'maximize_throughput', target: '10000 req/s' },
        { goal: 'minimize_error_rate', target: 'error rate < 0.01%' }
      ];

      act(() => {
        simulateWebSocketMessage({
          type: 'optimization_complete',
          data: {
            id: 'opt-multi-goal',
            analysis: {
              summary: 'Multi-goal performance optimization analysis',
              key_findings: ['Trade-offs required between competing goals'],
              bottlenecks_identified: [],
              root_causes: [],
              confidence_score: 0.87,
              analysis_timestamp: new Date().toISOString()
            },
            recommendations: performanceGoals.map((goal, index) => ({
              id: `opt-${goal.goal}`,
              title: `Optimize for ${goal.goal}`,
              priority: index === 0 ? 'high' : 'medium',
              estimated_impact: { 
                value: goal.target, 
                unit: 'target' 
              },
              trade_offs: {
                latency: goal.goal === 'minimize_latency' ? 'optimized' : 'may increase',
                throughput: goal.goal === 'maximize_throughput' ? 'optimized' : 'may decrease',
                error_rate: goal.goal === 'minimize_error_rate' ? 'optimized' : 'unchanged',
                cost: goal.goal === 'minimize_latency' ? 'increase 20%' : 'increase 10%'
              }
            }))
          }
        });
      });

      await waitFor(() => {
        const recommendations = result.current.optimizationResults?.recommendations;
        expect(recommendations).toHaveLength(3);
        
        const latencyOpt = recommendations?.find(r => r.id === 'opt-minimize_latency');
        expect(latencyOpt?.trade_offs?.latency).toBe('optimized');
        expect(latencyOpt?.trade_offs?.cost).toContain('increase');
      });
    });
  });

  describe('Resource Optimization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should optimize resource allocation and utilization', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'optimization_complete',
          data: {
            id: 'opt-resources',
            analysis: {
              summary: 'Resource utilization optimization analysis complete',
              key_findings: [
                'CPU utilization imbalanced across instances',
                'Memory overprovisioned by 40%',
                'Storage IOPS underutilized'
              ],
              bottlenecks_identified: ['Load balancer configuration', 'Memory allocation strategy'],
              root_causes: ['Static resource allocation', 'No autoscaling policies'],
              confidence_score: 0.91,
              analysis_timestamp: new Date().toISOString()
            },
            metrics: [
              { name: 'avg_cpu_utilization', value: 35, unit: '%' },
              { name: 'peak_cpu_utilization', value: 85, unit: '%' },
              { name: 'memory_waste', value: 40, unit: '%' },
              { name: 'optimal_instance_count', value: 12, unit: 'instances' },
              { name: 'current_instance_count', value: 20, unit: 'instances' }
            ],
            recommendations: [
              {
                id: 'implement-autoscaling',
                title: 'Implement predictive autoscaling',
                priority: 'high',
                estimated_impact: { value: 8, unit: 'instances reduced' },
                scaling_policy: {
                  min_instances: 8,
                  max_instances: 25,
                  target_cpu: 65,
                  scale_up_threshold: 75,
                  scale_down_threshold: 45,
                  predictive_scaling: true,
                  schedule_based_scaling: {
                    peak_hours: '9AM-5PM',
                    off_peak_scale_down: 50
                  }
                }
              }
            ]
          }
        });
      });

      await waitFor(() => {
        const results = result.current.optimizationResults;
        expect(results?.metrics.find(m => m.name === 'memory_waste')?.value).toBe(40);
        expect(results?.recommendations[0].scaling_policy).toBeTruthy();
        expect(results?.recommendations[0].scaling_policy?.predictive_scaling).toBe(true);
      });
    });
  });

  describe('Trade-off Analysis', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should provide comprehensive trade-off analysis', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'optimization_complete',
          data: {
            id: 'opt-tradeoff',
            analysis: {
              summary: 'Trade-off analysis for optimization strategies',
              key_findings: ['Multiple valid optimization paths with different trade-offs'],
              bottlenecks_identified: [],
              root_causes: [],
              confidence_score: 0.83,
              analysis_timestamp: new Date().toISOString()
            },
            trade_off_matrix: {
              options: [
                {
                  id: 'option-1',
                  name: 'Cost-optimized',
                  metrics: {
                    cost_savings: 100,
                    performance_impact: -10,
                    reliability_impact: -5,
                    implementation_complexity: 30
                  }
                },
                {
                  id: 'option-2',
                  name: 'Performance-optimized',
                  metrics: {
                    cost_savings: -20,
                    performance_impact: 100,
                    reliability_impact: 10,
                    implementation_complexity: 70
                  }
                },
                {
                  id: 'option-3',
                  name: 'Balanced',
                  metrics: {
                    cost_savings: 50,
                    performance_impact: 40,
                    reliability_impact: 20,
                    implementation_complexity: 50
                  }
                }
              ],
              pareto_optimal: ['option-2', 'option-3'],
              recommendation: 'option-3',
              rationale: 'Balanced approach provides best overall value with acceptable trade-offs'
            }
          }
        });
      });

      await waitFor(() => {
        const results = result.current.optimizationResults;
        expect(results?.trade_off_matrix).toBeTruthy();
        expect(results?.trade_off_matrix?.options).toHaveLength(3);
        expect(results?.trade_off_matrix?.pareto_optimal).toContain('option-3');
      });
    });
  });

  describe('Optimization Validation', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should validate optimization recommendations are achievable', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'optimization_complete',
          data: {
            id: 'opt-validated',
            analysis: {
              summary: 'Validated optimization recommendations',
              key_findings: ['All recommendations validated against constraints'],
              bottlenecks_identified: [],
              root_causes: [],
              confidence_score: 0.94,
              analysis_timestamp: new Date().toISOString()
            },
            recommendations: [
              {
                id: 'validated-rec-1',
                title: 'Validated optimization strategy',
                priority: 'high',
                estimated_impact: { value: 30000, unit: 'USD/month' },
                validation: {
                  feasibility_score: 0.92,
                  constraint_checks: {
                    budget: { required: 5000, available: 10000, status: 'pass' },
                    time: { required: '2 weeks', available: '4 weeks', status: 'pass' },
                    resources: { required: '2 engineers', available: '3 engineers', status: 'pass' },
                    risk: { level: 'medium', acceptable: 'high', status: 'pass' }
                  },
                  dependencies_met: true,
                  blockers: [],
                  success_probability: 0.87
                }
              }
            ]
          }
        });
      });

      await waitFor(() => {
        const recommendations = result.current.optimizationResults?.recommendations;
        expect(recommendations?.[0].validation).toBeTruthy();
        expect(recommendations?.[0].validation?.feasibility_score).toBeGreaterThan(0.9);
        expect(recommendations?.[0].validation?.constraint_checks?.budget?.status).toBe('pass');
      });
    });
  });

  describe('Progressive Optimization', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should support progressive optimization with milestones', async () => {
      const { result } = renderHook(() => useAgentContext(), { wrapper: createWrapper });

      act(() => {
        simulateWebSocketMessage({
          type: 'optimization_complete',
          data: {
            id: 'opt-progressive',
            analysis: {
              summary: 'Progressive optimization plan with milestones',
              key_findings: ['Phased approach recommended for risk mitigation'],
              bottlenecks_identified: [],
              root_causes: [],
              confidence_score: 0.89,
              analysis_timestamp: new Date().toISOString()
            },
            progressive_plan: {
              total_duration: '3 months',
              phases: [
                {
                  phase: 1,
                  name: 'Quick wins',
                  duration: '2 weeks',
                  expected_savings: 10000,
                  milestones: [
                    { name: 'Remove unused resources', completion: '3 days', savings: 5000 },
                    { name: 'Optimize caching', completion: '1 week', savings: 3000 },
                    { name: 'Fix obvious inefficiencies', completion: '2 weeks', savings: 2000 }
                  ]
                },
                {
                  phase: 2,
                  name: 'Infrastructure optimization',
                  duration: '1 month',
                  expected_savings: 20000,
                  milestones: [
                    { name: 'Rightsize instances', completion: '2 weeks', savings: 12000 },
                    { name: 'Implement autoscaling', completion: '3 weeks', savings: 5000 },
                    { name: 'Optimize data transfer', completion: '1 month', savings: 3000 }
                  ]
                },
                {
                  phase: 3,
                  name: 'Advanced optimization',
                  duration: '1.5 months',
                  expected_savings: 15000,
                  milestones: [
                    { name: 'Implement spot instances', completion: '3 weeks', savings: 8000 },
                    { name: 'Optimize ML pipelines', completion: '1 month', savings: 5000 },
                    { name: 'Archive cold data', completion: '1.5 months', savings: 2000 }
                  ]
                }
              ],
              total_expected_savings: 45000,
              cumulative_savings_curve: [
                { month: 1, savings: 10000 },
                { month: 2, savings: 25000 },
                { month: 3, savings: 45000 }
              ]
            }
          }
        });
      });

      await waitFor(() => {
        const results = result.current.optimizationResults;
        expect(results?.progressive_plan).toBeTruthy();
        expect(results?.progressive_plan?.phases).toHaveLength(3);
        expect(results?.progressive_plan?.total_expected_savings).toBe(45000);
        expect(results?.progressive_plan?.phases[0].milestones).toHaveLength(3);
      });
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});