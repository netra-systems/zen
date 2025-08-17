// Types for FinalReport components
export interface AgentTiming {
  agent_name: string;
  duration: number;
  start_time: string;
  end_time: string;
}

export interface ToolCall {
  tool_name: string;
  count: number;
  avg_duration: number;
}

export interface ExecutionMetrics {
  total_duration: number;
  agent_timings: AgentTiming[];
  tool_calls: ToolCall[];
}

export interface FinalReportData {
  data_result?: Record<string, unknown>;
  optimizations_result?: Record<string, unknown>;
  action_plan_result?: Array<Record<string, unknown>> | Record<string, unknown>;
  report_result?: Record<string, unknown>;
  final_report?: string;
  execution_metrics?: ExecutionMetrics;
}

export interface FinalReportProps {
  reportData: FinalReportData;
}

export interface ExpandedSections {
  summary: boolean;
  data: boolean;
  optimizations: boolean;
  actions: boolean;
  metrics: boolean;
  raw: boolean;
  [key: string]: boolean;
}