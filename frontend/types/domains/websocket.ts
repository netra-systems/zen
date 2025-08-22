/**
 * WebSocket Domain Types - Single Source of Truth
 * 
 * Extracted from registry.ts for modular architecture compliance.
 * All WebSocket message types, payloads, and utilities consolidated here.
 * 
 * CRITICAL: Maximum 300 lines, 8 lines per function
 */

import { WebSocketMessageType, AgentStatus, isValidWebSocketMessageType } from '../shared/enums';
import { AgentResult, WebSocketError } from '../backend-sync/payloads';

// ============================================================================
// CORE WEBSOCKET INTERFACES
// ============================================================================

// WebSocketError imported from canonical source above

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
  // Legacy compatibility
  text?: string;
  references?: string[];
  attachments?: Array<Record<string, unknown>> | null;
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

// AgentResult imported from canonical source above

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
// WEBSOCKET MESSAGE INTERFACE - SINGLE SOURCE OF TRUTH
// ============================================================================

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
// AUTHENTICATION AND SYSTEM MESSAGE TYPES
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
// TYPE GUARDS AND VALIDATION
// ============================================================================

export function isWebSocketMessage(obj: unknown): obj is WebSocketMessage {
  return typeof obj === 'object' && 
         obj !== null && 
         'type' in obj && 
         'payload' in obj;
}

export function isAgentStartedMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: AgentStartedPayload } {
  return msg.type === WebSocketMessageType.AGENT_STARTED;
}

export function isAgentCompletedMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: AgentCompletedPayload } {
  return msg.type === WebSocketMessageType.AGENT_COMPLETED;
}

export function isSubAgentUpdateMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: SubAgentUpdatePayload } {
  return msg.type === WebSocketMessageType.SUB_AGENT_UPDATE;
}

export function isToolCallMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: ToolCallPayload } {
  return msg.type === WebSocketMessageType.TOOL_CALL;
}

export function isErrorMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: ErrorPayload } {
  return msg.type === WebSocketMessageType.ERROR;
}

export function isUserMessagePayload(msg: WebSocketMessage): msg is WebSocketMessage & { payload: UserMessagePayload } {
  return msg.type === WebSocketMessageType.USER_MESSAGE || msg.type === WebSocketMessageType.CHAT_MESSAGE;
}

export function isAgentUpdateMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: AgentUpdatePayload } {
  return msg.type === WebSocketMessageType.AGENT_UPDATE;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

export function createWebSocketError(
  message: string,
  errorType?: string,
  severity: WebSocketError['severity'] = 'medium'
): WebSocketError {
  return {
    message,
    error_type: errorType,
    severity,
    timestamp: new Date().toISOString()
  };
}

export function createWebSocketMessage<T extends WebSocketMessage['payload']>(
  type: WebSocketMessageType,
  payload: T,
  options?: { sender?: string; timestamp?: string }
): WebSocketMessage {
  return {
    type,
    payload,
    sender: options?.sender,
    timestamp: options?.timestamp || new Date().toISOString()
  };
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

export type MessageTypeLiteral = keyof typeof WebSocketMessageType;
export type WebSocketPayload = WebSocketMessage['payload'];export { isValidWebSocketMessageType };
