export interface SubAgentUpdate {
    sub_agent_name: string;
    state: any; // placeholder
}

export interface AgentStarted {
    run_id: string;
}

export interface AgentCompleted {
    run_id: string;
    result: any;
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
