// frontend/types/WebSocket.ts

export interface WebSocketError {
  message: string;
}

export interface AnalysisRequest {
  request_model: any; // placeholder
}

export interface StreamEvent {
  event_type: string;
  data: {
    [k: string]: any;
  };
}

export interface RunComplete {
  run_id: string;
  result: any;
}

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

export interface UserMessage {
  text: string;
  references?: string[];
}

export interface AgentMessage {
  text: string;
}

export interface ToolStarted {
  tool_name: string;
}

export interface ToolCompleted {
  tool_name: string;
  result: any;
}

export interface StopAgent {
  run_id: string;
}

export interface SubAgentStatus {
  agent_name: string;
  tools: string[];
  status: string;
}

export interface MessageToUser {
  sender: string;
  content: string;
  references?: string[] | null;
  raw_json?: { [k: string]: any } | null;
  error?: string | null;
}


export interface WebSocketMessage {
  type:
    | "analysis_request"
    | "error"
    | "stream_event"
    | "run_complete"
    | "sub_agent_update"
    | "agent_started"
    | "agent_completed"
    | "agent_error"
    | "user_message"
    | "agent_message"
    | "tool_started"
    | "tool_completed"
    | "stop_agent"
    | "pong"
    | "sub_agent_status";
  payload:
    | AnalysisRequest
    | WebSocketError
    | StreamEvent
    | RunComplete
    | SubAgentUpdate
    | AgentStarted
    | AgentCompleted
    | AgentErrorMessage
    | UserMessage
    | AgentMessage
    | ToolStarted
    | ToolCompleted
    | StopAgent
    | SubAgentStatus
    | MessageToUser
    | null;
}
