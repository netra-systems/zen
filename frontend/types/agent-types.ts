/**
 * SINGLE SOURCE OF TRUTH: Agent Types
 * 
 * This file consolidates all agent-related types to eliminate duplication and ensure
 * consistent type contracts between frontend and backend components.
 * 
 * BVJ: Enterprise segment - agent reliability critical for AI workload optimization value
 * 
 * Architecture: Uses backend_schema_auto_generated.ts as authoritative source,
 * extending with frontend-specific UI types only where necessary.
 */

// Import authoritative backend schema types
import type {
  AgentStatus as BackendAgentStatus,
  AgentStartedPayload,
  AgentCompletedPayload,
  SubAgentUpdatePayload,
  StopAgentPayload,
  ErrorPayload,
  AgentResult,
  WebSocketMessage,
  WebSocketMessageType
} from './backend_schema_auto_generated';

// Import supporting types
import type { ReferenceItem } from './backend_schema_tools';

// ============================================================================
// CORE AGENT TYPES (Backend Schema Authority)
// ============================================================================

/**
 * Agent execution status - mirrors backend AgentStatus enum exactly
 * Source: backend_schema_auto_generated.ts
 */
export type AgentStatus = BackendAgentStatus;

/**
 * Agent started event payload
 * Standardized across all agent implementations
 */
export interface AgentStarted {
  run_id: string;
  agent_id?: string;
  agent_type?: string;
  status?: AgentStatus;
  message?: string;
}

/**
 * Agent completion event payload
 * Includes execution result and metrics
 */
export interface AgentCompleted {
  run_id: string;
  agent_id?: string;
  result: AgentResult;
  status?: AgentStatus;
  message?: string;
}

/**
 * Agent error event payload
 * Standardized error reporting across all agents
 */
export interface AgentErrorMessage {
  run_id: string;
  agent_id?: string;
  message: string;
  error_type?: string;
  code?: string;
  severity?: "low" | "medium" | "high" | "critical";
  details?: Record<string, unknown>;
}

/**
 * Sub-agent status update payload
 * Real-time progress tracking for nested agent execution
 */
export interface SubAgentUpdate {
  agent_id: string;
  sub_agent_name: string;
  status: AgentStatus;
  message?: string;
  progress?: number; // 0-100
  current_task?: string;
  state?: {
    lifecycle?: string;
    tools?: string[];
    data_result?: unknown;
    optimizations_result?: unknown;
    action_plan_result?: unknown;
    final_report?: unknown;
  };
}

/**
 * Agent stop command payload
 * Graceful agent termination
 */
export interface StopAgent {
  run_id: string;
  agent_id?: string;
  reason?: string;
}

// ============================================================================
// FRONTEND UI-SPECIFIC EXTENSIONS
// ============================================================================

/**
 * UI-specific agent metrics for performance monitoring
 * Enterprise-grade visibility into agent resource usage
 */
export interface AgentMetrics {
  cpu?: number;
  memory?: number;
  apiCalls?: number;
  tokensUsed?: number;
  executionTime?: number;
  toolsExecuted?: number;
}

/**
 * UI tool execution state for agent status display
 */
export interface AgentTool {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  duration?: number;
  startTime?: number;
  endTime?: number;
}

/**
 * Frontend agent state for UI components
 * Extends backend state with UI-specific properties
 */
export interface FrontendAgentState {
  status: AgentStatus;
  currentAction?: string;
  progress?: number; // 0-100
  eta?: number; // seconds
  elapsedTime?: number; // seconds
  isPaused?: boolean;
  tools?: AgentTool[];
  metrics?: AgentMetrics;
  logs?: string[];
  subAgents?: {
    current?: string;
    queue?: string[];
  };
}

/**
 * Agent status card props for UI components
 * Enterprise-grade agent monitoring interface
 */
export interface AgentStatusCardProps {
  agentName: string;
  runId?: string;
  state: FrontendAgentState;
  onCancel?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onToggleExpand?: () => void;
  isExpanded?: boolean;
}

/**
 * Agent completion result with UI-friendly formatting
 * Includes artifacts and metrics for enterprise reporting
 */
export interface AgentCompletionResult {
  output: string;
  data?: Record<string, unknown>;
  metrics?: AgentMetrics;
  artifacts?: Record<string, unknown>;
  recommendations?: string[];
  optimizations?: {
    cost_savings?: number;
    performance_improvements?: string[];
    resource_optimizations?: string[];
  };
}

// ============================================================================
// WEBSOCKET MESSAGE HELPERS
// ============================================================================

/**
 * Type guards for agent-related WebSocket messages
 * Ensures type safety in message handling
 */
export function isAgentStartedMessage(
  msg: WebSocketMessage
): msg is WebSocketMessage & { payload: AgentStartedPayload } {
  return msg.type === 'agent_started';
}

export function isAgentCompletedMessage(
  msg: WebSocketMessage
): msg is WebSocketMessage & { payload: AgentCompletedPayload } {
  return msg.type === 'agent_completed';
}

export function isSubAgentUpdateMessage(
  msg: WebSocketMessage
): msg is WebSocketMessage & { payload: SubAgentUpdatePayload } {
  return msg.type === 'sub_agent_update';
}

export function isAgentErrorMessage(
  msg: WebSocketMessage
): msg is WebSocketMessage & { payload: ErrorPayload } {
  return msg.type === 'agent_error';
}

// ============================================================================
// LEGACY COMPATIBILITY (Deprecated - Use AgentStatus instead)
// ============================================================================

/**
 * @deprecated Use AgentStatus instead
 * Legacy chat store status mapping for backward compatibility
 */
export type LegacyAgentStatus = 'IDLE' | 'RUNNING' | 'COMPLETED' | 'ERROR';

/**
 * Maps legacy status to current AgentStatus
 * @deprecated Remove after chat store migration
 */
export function mapLegacyStatus(legacy: LegacyAgentStatus): AgentStatus {
  const mapping: Record<LegacyAgentStatus, AgentStatus> = {
    'IDLE': 'idle',
    'RUNNING': 'running',
    'COMPLETED': 'completed',
    'ERROR': 'error'
  };
  return mapping[legacy];
}

/**
 * Maps current AgentStatus to legacy format
 * @deprecated Remove after chat store migration
 */
export function toLegacyStatus(status: AgentStatus): LegacyAgentStatus {
  const mapping: Partial<Record<AgentStatus, LegacyAgentStatus>> = {
    'idle': 'IDLE',
    'initializing': 'IDLE',
    'running': 'RUNNING',
    'executing': 'RUNNING',
    'active': 'RUNNING',
    'thinking': 'RUNNING',
    'planning': 'RUNNING',
    'completed': 'COMPLETED',
    'error': 'ERROR',
    'failed': 'ERROR',
    'cancelled': 'ERROR'
  };
  return mapping[status] || 'ERROR';
}

// ============================================================================
// TYPE HIERARCHY DOCUMENTATION
// ============================================================================

/**
 * Agent Type Hierarchy:
 * 
 * 1. Backend Schema Types (authoritative)
 *    - AgentStatus: Core agent execution states
 *    - AgentStartedPayload, AgentCompletedPayload, etc.: WebSocket payloads
 * 
 * 2. Frontend Message Types (derived from backend)
 *    - AgentStarted, AgentCompleted, etc.: Simplified frontend interfaces
 * 
 * 3. UI State Types (frontend-specific)
 *    - FrontendAgentState: UI component state
 *    - AgentStatusCardProps: Component props
 * 
 * 4. Legacy Types (deprecated)
 *    - LegacyAgentStatus: Backward compatibility only
 * 
 * Migration Path:
 * - All components should use types from this file
 * - Backend compatibility maintained through auto-generated schema
 * - Legacy types will be removed in future versions
 */

// Re-export commonly used types for convenience
export type {
  WebSocketMessage,
  WebSocketMessageType,
  AgentResult
} from './backend_schema_auto_generated';

export type { ReferenceItem } from './backend_schema_tools';