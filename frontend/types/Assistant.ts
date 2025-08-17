/**
 * DEPRECATED: Assistant-related type definitions
 * 
 * This file now re-exports from the consolidated agent-types.ts
 * Use @/types/agent-types instead for new code.
 * 
 * This file exists only for backward compatibility during migration.
 */

import type { SubAgentStatus } from './backend_schema_base';

// Import from consolidated agent types (single source of truth)
import type {
  AgentStarted,
  AgentCompleted,
  AgentErrorMessage,
  SubAgentUpdate,
  StopAgent,
  FrontendAgentState,
  AgentCompletionResult
} from './agent-types';

// Re-export consolidated types for backward compatibility
export type { 
  AgentStarted,
  AgentCompleted,
  AgentErrorMessage,
  SubAgentUpdate,
  StopAgent,
  AgentCompletionResult
};

// Frontend UI-specific SubAgent state (now in consolidated types)
export type FrontendSubAgentState = FrontendAgentState;

// Re-export backend type for compatibility
export type { SubAgentStatus };