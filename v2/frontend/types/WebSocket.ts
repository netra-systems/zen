// frontend/types/WebSocket.ts
import { RequestModel } from './Request';
import { StreamEvent } from './StreamEvent';
import { RunComplete } from './Run';
import { SubAgentUpdate, AgentStarted, AgentCompleted, AgentErrorMessage, StopAgent, SubAgentStatus } from './Assistant';
import { UserMessage, AgentMessage, MessageToUser } from './Message';
import { ToolStarted, ToolCompleted } from './Tool';

export interface WebSocketError {
  message: string;
}

export interface AnalysisRequest {
  request_model: RequestModel;
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