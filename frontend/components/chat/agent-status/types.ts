export interface AgentStatusCardProps {
  agentName: string;
  status: 'idle' | 'thinking' | 'executing' | 'success' | 'error' | 'cancelled';
  currentAction?: string;
  progress?: number;
  eta?: number;
  tools?: Array<{
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    duration?: number;
  }>;
  metrics?: {
    cpu?: number;
    memory?: number;
    apiCalls?: number;
    tokensUsed?: number;
  };
  logs?: string[];
  onCancel?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  isPaused?: boolean;
}

export interface Tool {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  duration?: number;
}

export interface Metrics {
  cpu?: number;
  memory?: number;
  apiCalls?: number;
  tokensUsed?: number;
}

export type AgentStatus = 'idle' | 'thinking' | 'executing' | 'success' | 'error' | 'cancelled';

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