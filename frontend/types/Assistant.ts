export interface SubAgentUpdate {
    sub_agent_name: string;
    state: SubAgentState;
}

export interface AgentStarted {
    run_id: string;
}

export interface AgentCompleted {
    run_id: string;
    result: AgentCompletionResult;
}

export interface AgentErrorMessage {
    run_id: string;
    message: string;
}

export interface StopAgent {
    run_id: string;
}

export interface SubAgentStatus {
  agent_name: string;
  tools: string[];
  status: string;
}

export interface SubAgentState {
  status: 'idle' | 'thinking' | 'executing' | 'completed' | 'error';
  currentStep?: string;
  progress?: {
    current: number;
    total: number;
  };
  tools?: string[];
  metadata?: {
    [key: string]: unknown;
  };
}

export interface AgentCompletionResult {
  output: string;
  data?: {
    [key: string]: unknown;
  };
  metrics?: {
    executionTime: number;
    tokensUsed?: number;
    toolsExecuted?: number;
  };
  artifacts?: {
    [key: string]: unknown;
  };
}
