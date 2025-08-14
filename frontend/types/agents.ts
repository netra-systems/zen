/* tslint:disable */
/* eslint-disable */
/**
 * Agent-related type definitions
 * Auto-generated from pydantic models - do not modify by hand
 */

export type SubAgentLifecycle = "pending" | "running" | "completed" | "failed" | "shutdown";

export interface AgentCompleted {
  run_id: string;
  result: unknown;
}

export interface AgentErrorMessage {
  run_id: string;
  message: string;
}

export interface AgentMessage {
  text: string;
}

export interface AgentStarted {
  run_id: string;
}

export interface AgentState {
  messages: BaseMessage[];
  next_node: string;
  tool_results?:
    | {
        [k: string]: unknown;
      }[]
    | null;
}

export interface StartAgentMessage {
  text: string;
  thread_id?: string | null;
  references?: ReferenceItem[] | null;
}

export interface StartAgentPayload {
  message: StartAgentMessage;
}

export interface StopAgent {
  run_id: string;
}

export interface SubAgentState {
  agent_id: string;
  status: SubAgentLifecycle;
  result?: unknown | null;
  error?: string | null;
}

export interface SubAgentStatus {
  agents: SubAgentState[];
}

export interface SubAgentUpdate {
  agent_id: string;
  status: SubAgentLifecycle;
  result?: unknown | null;
  error?: string | null;
}

// Re-export types needed by agents
export interface BaseMessage {
  content:
    | string
    | (
        | string
        | {
            [k: string]: unknown;
          }
      )[];
  additional_kwargs?: {
    [k: string]: unknown;
  } | null;
  response_metadata?: {
    [k: string]: unknown;
  } | null;
  type: string;
  name?: string | null;
  id?: string | null;
}

export interface ReferenceItem {
  id: string;
  title: string;
  content: string;
  type: string;
  metadata?: {
    [k: string]: unknown;
  } | null;
}