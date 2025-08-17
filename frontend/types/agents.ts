/* tslint:disable */
/* eslint-disable */
/**
 * Agent-related type definitions
 * Auto-generated from pydantic models - do not modify by hand
 */

import type { ReferenceItem } from './backend_schema_tools';

// Import consolidated types from backend schema
import type {
  BaseMessage,
  SubAgentState,
  SubAgentStatus,
  SubAgentLifecycle
} from './backend_schema_base';

// Re-export for backward compatibility
export type { BaseMessage, SubAgentState, SubAgentStatus, SubAgentLifecycle };


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


export interface SubAgentUpdate {
  agent_id: string;
  status: SubAgentLifecycle;
  result?: unknown | null;
  error?: string | null;
}


// Re-export canonical type
export type { ReferenceItem };