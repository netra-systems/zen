// Types for FinalReport components
// Note: ExecutionMetrics, AgentTiming, and ToolCall are now imported from unified/metrics.types.ts
import type { ExecutionMetrics, AgentTiming, ToolCall } from '@/types/unified/metrics.types';

// Re-export for backward compatibility
export type { ExecutionMetrics, AgentTiming, ToolCall };

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