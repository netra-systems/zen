/* tslint:disable */
/* eslint-disable */
/**
 * DEPRECATED: Agent-related type definitions
 * 
 * This file now re-exports from the consolidated agent-types.ts
 * Use @/types/agent-types instead for new code.
 * 
 * This file exists only for backward compatibility during migration.
 */

import type { ReferenceItem } from './backend_schema_tools';

// Import consolidated types from backend schema
import type {
  BaseMessage,
  SubAgentState,
  SubAgentStatus,
  SubAgentLifecycle
} from './backend_schema_base';

// Import from consolidated agent types (single source of truth)
import type {
  AgentStarted,
  AgentCompleted,
  AgentErrorMessage,
  SubAgentUpdate,
  StopAgent
} from './agent-types';

// Re-export consolidated types for backward compatibility
export type { 
  AgentStarted,
  AgentCompleted,
  AgentErrorMessage,
  SubAgentUpdate,
  StopAgent
};

// Re-export backend schema types
export type { BaseMessage, SubAgentState, SubAgentStatus, SubAgentLifecycle };

// Agent-specific types not covered by consolidated types
export interface AgentMessage {
  text: string;
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

// Re-export canonical type
export type { ReferenceItem };