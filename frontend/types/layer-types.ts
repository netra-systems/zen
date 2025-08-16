// Layer-specific types for three-layer response card architecture
// Fast Layer (0-100ms), Medium Layer (100ms-1s), Slow Layer (1s+)

// ============================================
// Fast Layer Types (0-100ms updates)
// ============================================

export interface AgentStartedEvent {
  type: 'agent_started';
  payload: {
    agent_id: string;
    agent_type: string;
    run_id: string;
    timestamp?: string;
    status?: string;
    message?: string;
  };
}

export interface ToolExecutingEvent {
  type: 'tool_executing';
  payload: {
    tool_name: string;
    agent_id?: string;
    agent_type?: string;
    timestamp: number;
  };
}

export interface ToolStatus {
  name: string;
  startTime: number;
  isActive: boolean;
  duration?: number;
}

export interface FastLayerData {
  agentName: string;        // From agent_started event
  activeTools: string[];    // From tool_executing events (legacy)
  toolStatuses: ToolStatus[]; // Enhanced tool tracking with lifecycle
  timestamp: number;        // From backend
  runId: string;           // From backend
}

// ============================================
// Medium Layer Types (100ms-1s updates)
// ============================================

export interface AgentThinkingEvent {
  type: 'agent_thinking';
  payload: {
    thought: string;
    agent_id?: string;
    agent_type?: string;
    step_number: number;
    total_steps: number;
  };
}

export interface PartialResultEvent {
  type: 'partial_result';
  payload: {
    content: string;
    agent_id?: string;
    agent_type?: string;
    is_complete: boolean;
  };
}

export interface MediumLayerData {
  thought: string;          // From agent_thinking event
  partialContent: string;   // From partial_result events (accumulated)
  stepNumber: number;       // From backend
  totalSteps: number;       // From backend
  agentName: string;        // From backend
}

// ============================================
// Slow Layer Types (1s+ updates)
// ============================================

export interface AgentCompletedEvent {
  type: 'agent_completed';
  payload: {
    agent_id?: string;
    agent_type?: string;
    duration_ms: number;
    result: Record<string, unknown>;  // Agent-specific result data
    metrics: Record<string, unknown>; // Performance metrics
  };
}

export interface FinalReportEvent {
  type: 'final_report';
  payload: {
    report: Record<string, unknown>;      // Complete analysis report
    total_duration_ms: number;
    agent_metrics: AgentMetric[];
    recommendations: Recommendation[];
    action_plan: ActionStep[];
    executive_summary?: string;
    cost_analysis?: CostAnalysis;
    performance_comparison?: PerformanceComparison;
    confidence_scores?: ConfidenceScores;
    technical_details?: TechnicalDetails;
  };
}

export interface SlowLayerData {
  completedAgents: AgentResult[];     // From agent_completed events
  finalReport: FinalReport | null;    // From final_report event
  totalDuration: number;               // From backend
  metrics: ExecutionMetrics;          // From backend
}

// ============================================
// Supporting Types
// ============================================

export interface AgentResult {
  agentName: string;
  duration: number;
  result: AgentResultData;  // Agent-specific, from backend
  metrics: AgentMetrics; // Agent-specific, from backend
  iteration?: number; // Iteration count for repeated agents
}

export interface FinalReport {
  report: ReportData;                        // Complete report object
  recommendations: Recommendation[];   // From backend
  actionPlan: ActionStep[];           // From backend
  agentMetrics: AgentMetric[];       // From backend
  executive_summary?: string;
  cost_analysis?: CostAnalysis;
  performance_comparison?: PerformanceComparison;
  confidence_scores?: ConfidenceScores;
  technical_details?: TechnicalDetails;
}

export interface Recommendation {
  id: string;
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  effort: 'high' | 'medium' | 'low';
  category: string;
  metrics?: {
    potential_savings?: number;
    latency_reduction?: number;
    throughput_increase?: number;
  };
}

export interface ActionStep {
  id: string;
  step_number: number;
  description: string;
  command?: string;
  expected_outcome: string;
  dependencies?: string[];
  estimated_duration?: string;
}

export interface AgentMetric {
  agent_id: string;
  agent_type?: string;
  duration_ms: number;
  tokens_used?: number;
  tools_executed?: number;
  cache_hits?: number;
  cache_misses?: number;
}

export interface ExecutionMetrics {
  total_duration_ms: number;
  total_tokens: number;
  total_cost?: number;
  cache_efficiency?: number;
  parallel_executions?: number;
  sequential_executions?: number;
}

// ============================================
// Data Type Definitions
// ============================================

export interface CostAnalysis {
  totalCost: number;
  costBreakdown: {
    [category: string]: number;
  };
  currency: string;
  period?: string;
  savings?: number;
}

export interface PerformanceComparison {
  baseline: {
    latency: number;
    throughput: number;
    errorRate: number;
  };
  optimized: {
    latency: number;
    throughput: number;
    errorRate: number;
  };
  improvements: {
    latencyReduction: number;
    throughputIncrease: number;
    errorReduction: number;
  };
}

export interface ConfidenceScores {
  overall: number;
  recommendations: {
    [recommendationId: string]: number;
  };
  metrics: {
    [metricName: string]: number;
  };
}

export interface TechnicalDetails {
  implementation: {
    [key: string]: unknown;
  };
  configuration: {
    [key: string]: unknown;
  };
  dependencies: string[];
  requirements: string[];
}

export interface AgentResultData {
  output?: string;
  artifacts?: {
    [key: string]: unknown;
  };
  status: 'success' | 'error' | 'partial';
  data?: {
    [key: string]: unknown;
  };
}

export interface AgentMetrics {
  executionTime: number;
  memoryUsage?: number;
  apiCalls?: number;
  errorCount?: number;
  toolsUsed?: string[];
  performance?: {
    [metricName: string]: number;
  };
}

export interface ReportData {
  summary: string;
  findings: {
    [category: string]: unknown[];
  };
  data: {
    [key: string]: unknown;
  };
  metadata: {
    generatedAt: string;
    version: string;
    [key: string]: unknown;
  };
}

// ============================================
// Layer Update Event
// ============================================

export type LayerUpdateEvent = 
  | { layer: 'fast'; data: FastLayerData }
  | { layer: 'medium'; data: MediumLayerData }
  | { layer: 'slow'; data: SlowLayerData };
