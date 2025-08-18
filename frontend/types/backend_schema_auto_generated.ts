/**
 * Backend Schema Auto-Generated Types
 * 
 * ⚠️ DEPRECATED: This file is being phased out for WebSocket types.
 * 🔄 MIGRATION: Use @/types/registry instead for all WebSocket types.
 * 
 * This file contains TypeScript type definitions that mirror the backend
 * WebSocket message schemas, ensuring type safety across the frontend-backend boundary.
 * 
 * CRITICAL: These types must match the backend schema definitions exactly.
 * Source: app/schemas/websocket_models.py and app/schemas/core_enums.py
 * 
 * MIGRATION PATH:
 * - OLD: import { WebSocketMessage } from '@/types/backend_schema_auto_generated'
 * - NEW: import { WebSocketMessage } from '@/types/registry'
 */

// ============================================================================
// WEBSOCKET MESSAGE TYPES (mirroring backend WebSocketMessageType enum)
// ============================================================================

export type WebSocketMessageType = 
  // Client to server
  | "start_agent"
  | "user_message"
  | "chat_message"
  | "stop_agent"
  | "create_thread"
  | "switch_thread"
  | "delete_thread"
  | "rename_thread"
  | "list_threads"
  | "get_thread_history"
  | "ping"
  | "pong"
  // Server to client
  | "agent_started"
  | "agent_completed"
  | "agent_stopped"
  | "agent_error"
  | "agent_update"
  | "agent_log"
  | "agent_thinking"
  | "agent_fallback"
  | "tool_started"
  | "tool_completed"
  | "tool_call"
  | "tool_result"
  | "tool_executing"
  | "subagent_started"
  | "subagent_completed"
  | "sub_agent_update"
  | "thread_history"
  | "thread_created"
  | "thread_updated"
  | "thread_deleted"
  | "thread_loaded"
  | "thread_renamed"
  | "step_created"
  | "partial_result"
  | "final_report"
  | "error"
  | "connection_established"
  | "stream_chunk"
  | "stream_complete"
  | "generation_progress"
  | "generation_complete"
  | "generation_error"
  | "batch_complete";

// ============================================================================
// AGENT STATUS TYPES (mirroring backend AgentStatus enum)
// ============================================================================

export type AgentStatus = 
  | "idle"
  | "initializing"
  | "active"
  | "thinking"
  | "planning"
  | "executing"
  | "running"
  | "waiting"
  | "paused"
  | "completed"
  | "failed"
  | "error"
  | "cancelled"
  | "shutdown";

// ============================================================================
// BASE WEBSOCKET PAYLOAD (mirroring backend BaseWebSocketPayload)
// ============================================================================

export interface BaseWebSocketPayload {
  timestamp?: string; // ISO datetime string
  correlation_id?: string;
  message_id?: string; // For message deduplication
}

// ============================================================================
// CLIENT TO SERVER PAYLOAD TYPES
// ============================================================================

export interface StartAgentPayload extends BaseWebSocketPayload {
  query: string;
  user_id: string;
  thread_id?: string;
  context?: Record<string, unknown>;
}

export interface UserMessagePayload extends BaseWebSocketPayload {
  content: string;
  thread_id?: string;
  metadata?: Record<string, unknown>;
}

export interface StopAgentPayload extends BaseWebSocketPayload {
  agent_id: string;
  reason?: string;
}

export interface CreateThreadPayload extends BaseWebSocketPayload {
  name?: string;
  metadata?: Record<string, unknown>;
}

export interface SwitchThreadPayload extends BaseWebSocketPayload {
  thread_id: string;
}

export interface DeleteThreadPayload extends BaseWebSocketPayload {
  thread_id: string;
}

// ============================================================================
// SERVER TO CLIENT PAYLOAD TYPES
// ============================================================================

export interface AgentUpdatePayload extends BaseWebSocketPayload {
  run_id: string;
  agent_id: string;
  status: AgentStatus;
  message?: string;
  progress?: number; // 0-100
  current_task?: string;
  metadata?: Record<string, unknown>;
}

export interface AgentStartedPayload extends BaseWebSocketPayload {
  agent_id: string;
  agent_type: string;
  run_id: string;
  status?: AgentStatus;
  message?: string;
}

export interface AgentCompletedPayload extends BaseWebSocketPayload {
  agent_id: string;
  run_id: string;
  result: AgentResult;
  status?: AgentStatus;
  message?: string;
}

export interface SubAgentUpdatePayload extends BaseWebSocketPayload {
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

export interface ToolCallPayload extends BaseWebSocketPayload {
  tool_name: string;
  parameters?: Record<string, unknown>;
  call_id: string;
}

export interface ToolResultPayload extends BaseWebSocketPayload {
  call_id: string;
  result?: string | Record<string, unknown>;
  error?: string;
  execution_time_ms?: number;
}

export interface StreamChunkPayload extends BaseWebSocketPayload {
  chunk_id: string;
  content: string;
  is_final?: boolean;
}

export interface StreamCompletePayload extends BaseWebSocketPayload {
  stream_id: string;
  total_chunks: number;
  metadata?: Record<string, unknown>;
}

export interface ErrorPayload extends BaseWebSocketPayload {
  message: string;
  error_type?: string;
  code?: string;
  severity?: "low" | "medium" | "high" | "critical";
  details?: Record<string, unknown>;
  trace_id?: string;
}

// ============================================================================
// WEBSOCKET MESSAGE STRUCTURE (mirroring backend WebSocketMessage)
// ============================================================================

/**
 * @deprecated Use WebSocketMessage from @/types/registry instead
 * @see {@link @/types/registry#WebSocketMessage} for the canonical type definition
 */
export interface WebSocketMessage {
  type: WebSocketMessageType;
  payload: 
    | Record<string, unknown>
    | BaseWebSocketPayload
    | StartAgentPayload
    | UserMessagePayload
    | StopAgentPayload
    | CreateThreadPayload
    | SwitchThreadPayload
    | DeleteThreadPayload
    | AgentUpdatePayload
    | AgentStartedPayload
    | AgentCompletedPayload
    | SubAgentUpdatePayload
    | ToolCallPayload
    | ToolResultPayload
    | StreamChunkPayload
    | StreamCompletePayload
    | ErrorPayload;
  sender?: string;
  timestamp?: string; // ISO datetime string
}

// ============================================================================
// SUPPORTING DATA TYPES
// ============================================================================

export interface AgentResult {
  success: boolean;
  message: string;
  data?: string | Record<string, unknown> | unknown[];
  metrics?: Record<string, number>;
}

export interface MessageData {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  timestamp: string; // ISO datetime string
  metadata?: Record<string, string | number | boolean>;
}

export interface ThreadHistoryResponse {
  thread_id: string;
  messages: MessageData[];
}

// ============================================================================
// WEBSOCKET ERROR TYPES
// ============================================================================

/**
 * @deprecated Use WebSocketError from @/types/registry instead
 * @see {@link @/types/registry#WebSocketError} for the canonical type definition
 */
export interface WebSocketError {
  message: string;
  error_type?: string;
  code?: string;
  severity?: "low" | "medium" | "high" | "critical";
  details?: Record<string, unknown>;
  trace_id?: string;
  timestamp?: string; // ISO datetime string
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

export type MessageTypeLiteral = WebSocketMessageType;

// Union type for all possible payloads
export type WebSocketPayload = WebSocketMessage['payload'];

// Type guards for specific message types
export function isWebSocketMessage(obj: unknown): obj is WebSocketMessage {
  return typeof obj === 'object' && 
         obj !== null && 
         'type' in obj && 
         'payload' in obj;
}

export function isAgentStartedMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: AgentStartedPayload } {
  return msg.type === 'agent_started';
}

export function isAgentCompletedMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: AgentCompletedPayload } {
  return msg.type === 'agent_completed';
}

export function isSubAgentUpdateMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: SubAgentUpdatePayload } {
  return msg.type === 'sub_agent_update';
}

export function isToolCallMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: ToolCallPayload } {
  return msg.type === 'tool_call';
}

export function isErrorMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: ErrorPayload } {
  return msg.type === 'error';
}

// ============================================================================
// AUTH MESSAGE TYPES (for WebSocket authentication)
// ============================================================================

export interface AuthMessage {
  type: "auth";
  token: string;
}

export interface PingMessage {
  type: "ping";
  timestamp?: number;
}

export interface PongMessage {
  type: "pong";
  timestamp?: number;
}

// ============================================================================
// EXPORTS NOTE
// ============================================================================
// All types are already exported via their individual export statements above.
// No additional export block needed.