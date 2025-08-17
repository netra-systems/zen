import type { Message as BackendMessage, SubAgentLifecycle, SubAgentState } from './backend_schema_base';
import type { ToolStatus } from './backend_schema_base';
import type { ToolInput, ToolResult } from './backend_schema_tools';

export type ChatMessage = Omit<BackendMessage, 'content'> & {
  content: string;
  references?: string[];
  error?: string;
};

// Re-export as Message for backwards compatibility
export type Message = ChatMessage;

// Re-export backend types for compatibility
export type { SubAgentLifecycle, SubAgentState };

// Export enum-like object for SubAgentLifecycle for easier usage
export const SubAgentLifecycleEnum = {
  PENDING: "pending" as const,
  RUNNING: "running" as const,
  COMPLETED: "completed" as const,
  FAILED: "failed" as const,
  SHUTDOWN: "shutdown" as const,
} as const;

// Re-export canonical types from backend schema
export type { ToolStatus, ToolInput, ToolResult };

export interface ChatWebSocketMessage {
  type: "analysis_request" | "error" | "stream_event" | "run_complete" | "sub_agent_update" | "agent_started" | "agent_completed" | "agent_error" | "message";
  payload: any;
}