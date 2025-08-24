/**
 * UNIFIED Agent Types - Single Source of Truth
 * 
 * Consolidates ALL agent-related types from:
 * - types/agent-types.ts
 * - types/shared/enums.ts (AgentStatus)
 * - components/chat/AgentStatusIndicator.tsx
 * - components/chat/agent-status/types.ts
 * - store/chatStore.ts
 * - components/demo/DemoChat.components.tsx
 * 
 * CRITICAL: This file replaces ALL other agent type definitions
 * Use ONLY these types for agent operations
 */

// Re-export ALL agent types from agent-types.ts (the authoritative source)
export type {
  // Core backend-aligned types
  AgentStatus,
  AgentStarted,
  AgentCompleted,
  AgentErrorMessage,
  SubAgentUpdate,
  StopAgent,
  
  // Frontend UI extensions
  AgentMetrics,
  AgentTool,
  FrontendAgentState,
  AgentStatusCardProps,
  AgentCompletionResult,
  
  // Legacy compatibility (deprecated)
  LegacyAgentStatus
} from '../agent-types';

// Re-export utility functions
export {
  // WebSocket message helpers
  isAgentStartedMessage,
  isAgentCompletedMessage,
  isSubAgentUpdateMessage,
  isAgentErrorMessage,
  
  // Legacy compatibility functions
  mapLegacyStatus,
  toLegacyStatus
} from '../agent-types';

// Re-export commonly used backend types
export type {
  WebSocketMessage,
  WebSocketMessageType,
  AgentResult,
  ReferenceItem
} from '../agent-types';