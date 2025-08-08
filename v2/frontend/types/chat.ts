
export type Message = {
  id: string;
  type: 'user' | 'agent' | 'system';
  full_name: string;
  picture?: string;
  message: string;
  payload?: any;
  timestamp: string;
};

export enum SubAgentLifecycle {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  SHUTDOWN = "shutdown",
}

export interface SubAgentState {
  messages: Message[];
  next_node: string;
  tool_results?: Record<string, any>[];
  lifecycle: SubAgentLifecycle;
  start_time?: string;
  end_time?: string;
  error_message?: string;
}

export enum ToolStatus {
  SUCCESS = "success",
  ERROR = "error",
  PARTIAL_SUCCESS = "partial_success",
  IN_PROGRESS = "in_progress",
  COMPLETE = "complete",
}

export interface ToolInput {
  tool_name: string;
  args: any[];
  kwargs: Record<string, any>;
}

export interface ToolResult {
  tool_input: ToolInput;
  status: ToolStatus;
  message: string;
  payload?: any;
  start_time: number;
  end_time?: number;
}

export interface WebSocketMessage {
  type: "analysis_request" | "error" | "stream_event" | "run_complete" | "sub_agent_update" | "agent_started" | "agent_completed" | "agent_error";
  payload: any;
}
