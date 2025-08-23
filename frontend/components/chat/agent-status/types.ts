/**
 * Agent Status Component Types
 * 
 * This file re-exports consolidated agent types for component-specific use.
 * All types now come from the single source of truth: @/types/unified
 */

import { 
  AgentStatus, 
  AgentStatusCardProps as BaseAgentStatusCardProps,
  AgentTool,
  AgentMetrics
} from '@/types/unified';

// Re-export consolidated types for component use
export type { AgentStatus };
export type AgentStatusCardProps = BaseAgentStatusCardProps;
export type Tool = AgentTool;
export type Metrics = AgentMetrics;

// Component-specific props (not duplicated in consolidated types)
export interface AgentHeaderProps {
  agentName: string;
  status: AgentStatus;
  currentAction?: string;
  progress?: number;
  eta?: number;
  elapsedTime: number;
  isPaused?: boolean;
  isExpanded: boolean;
  onCancel?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onToggleExpand: () => void;
}

export interface ToolExecutionProps {
  tools: Tool[];
}

export interface ResourceMetricsProps {
  metrics: Metrics;
}

export interface ExecutionLogsProps {
  logs: string[];
}