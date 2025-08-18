/**
 * Backend Sync: WebSocket Payload Types
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - Single source of truth for payload types
 * - Maximum file size: 300 lines
 * - Functions ≤8 lines each
 */

import { AgentStatus } from '../shared/enums';
import { BaseWebSocketPayload } from '../shared/base';

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
  text?: string; // Legacy compatibility
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

export interface AgentResult {
  success: boolean;
  output?: string | Record<string, unknown> | Array<unknown> | null;
  error?: string | null;
  metrics?: Record<string, number>;
  artifacts?: string[];
  execution_time_ms?: number | null;
  message?: string; // Backend compatibility
  data?: string | Record<string, unknown> | unknown[];
}

export interface AgentUpdatePayload extends BaseWebSocketPayload {
  run_id: string;
  agent_id: string;
  status: AgentStatus;
  message?: string;
  progress?: number;
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
  progress?: number;
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
// SUPPORTING MESSAGE TYPES
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
// WEBSOCKET ERROR TYPES
// ============================================================================

export interface WebSocketError {
  message: string;
  error_type?: string | null;
  code?: string | null;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  details?: Record<string, unknown> | null;
  trace_id?: string | null;
  timestamp?: string;
}

// ============================================================================
// UTILITY FUNCTIONS - Each function ≤8 lines
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

export function createAgentResult(
  success: boolean,
  options: Partial<AgentResult> = {}
): AgentResult {
  return {
    success,
    execution_time_ms: options.execution_time_ms || null,
    ...options
  };
}

// ============================================================================
// DEFAULT EXPORT FOR CONVENIENCE
// ============================================================================

export default {
  createWebSocketError,
  createAgentResult
};