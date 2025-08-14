/**
 * Type Registry: Single Source of Truth for All TypeScript Types
 * 
 * This module serves as the central registry for all type definitions in the Netra frontend,
 * eliminating duplication and ensuring consistency with the backend schema.
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - All type definitions MUST be imported from this registry
 * - NO duplicate type definitions allowed anywhere else in frontend
 * - This file maintains backend-frontend type alignment
 * - Maximum file size: 300 lines (will be split if needed)
 * 
 * Usage:
 *   import { User, Message, AgentState, WebSocketMessage } from '@/types/registry';
 */

// ============================================================================
// CORE DOMAIN ENUMS - Aligned with Python backend
// ============================================================================

export enum MessageType {
  USER = 'user',
  ASSISTANT = 'assistant',
  AGENT = 'agent', 
  SYSTEM = 'system',
  ERROR = 'error',
  TOOL = 'tool'
}

export enum AgentStatus {
  IDLE = 'idle',
  INITIALIZING = 'initializing', 
  ACTIVE = 'active',
  THINKING = 'thinking',
  PLANNING = 'planning',
  EXECUTING = 'executing',
  RUNNING = 'running',
  WAITING = 'waiting',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  FAILED = 'failed',
  ERROR = 'error',
  CANCELLED = 'cancelled',
  SHUTDOWN = 'shutdown'
}

export enum WebSocketMessageType {
  // Client to server
  START_AGENT = 'start_agent',
  USER_MESSAGE = 'user_message', 
  STOP_AGENT = 'stop_agent',
  CREATE_THREAD = 'create_thread',
  SWITCH_THREAD = 'switch_thread',
  DELETE_THREAD = 'delete_thread',
  RENAME_THREAD = 'rename_thread',
  LIST_THREADS = 'list_threads',
  GET_THREAD_HISTORY = 'get_thread_history',
  PING = 'ping',
  
  // Server to client
  AGENT_STARTED = 'agent_started',
  AGENT_COMPLETED = 'agent_completed',
  AGENT_STOPPED = 'agent_stopped',
  AGENT_ERROR = 'agent_error', 
  AGENT_UPDATE = 'agent_update',
  TOOL_STARTED = 'tool_started',
  TOOL_COMPLETED = 'tool_completed',
  SUBAGENT_STARTED = 'subagent_started',
  SUBAGENT_COMPLETED = 'subagent_completed',
  SUB_AGENT_UPDATE = 'sub_agent_update',
  THREAD_HISTORY = 'thread_history',
  ERROR = 'error',
  PONG = 'pong'
}

// ============================================================================
// CORE DOMAIN MODELS - Aligned with Python backend
// ============================================================================

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  picture?: string | null;
  is_active?: boolean;
  is_superuser?: boolean;
  hashed_password?: string | null;
  access_token?: string;
  token_type?: string;
}

export interface MessageMetadata {
  model?: string;
  tokens_used?: number;
  processing_time?: number;
  agent_name?: string;
  run_id?: string;
  step_id?: string;
  tool_calls?: Array<Record<string, unknown>>;
  custom_fields?: Record<string, string | number | boolean>;
}

export interface Message {
  id: string;
  created_at: string; // ISO datetime string
  content: string;
  type: MessageType;
  thread_id?: string | null;
  sub_agent_name?: string | null;
  tool_info?: Record<string, unknown> | null;
  raw_data?: Record<string, unknown> | null;
  displayed_to_user?: boolean;
  metadata?: MessageMetadata | null;
  references?: string[] | null;
  attachments?: Array<Record<string, unknown>> | null;
}

export interface ThreadMetadata {
  tags?: string[];
  priority?: number; // 0-10
  category?: string | null;
  user_id?: string | null;
  custom_fields?: Record<string, string | number | boolean>;
}

export interface Thread {
  id: string;
  name?: string | null;
  created_at: string; // ISO datetime string
  updated_at: string; // ISO datetime string
  metadata?: ThreadMetadata | null;
  message_count?: number;
  is_active?: boolean;
  last_message?: Message | null;
  participants?: string[] | null;
}

// ============================================================================
// AGENT MODELS - Consolidated and aligned
// ============================================================================

export interface ToolResultData {
  tool_name: string;
  status: string;
  output?: string | Record<string, unknown> | Array<unknown> | null;
  error?: string | null;
  execution_time_ms?: number | null;
  metadata?: Record<string, string | number | boolean>;
}

export interface AgentMetadata {
  created_at?: string; // ISO datetime string
  last_updated?: string; // ISO datetime string  
  execution_context?: Record<string, string>;
  custom_fields?: Record<string, string>;
  priority?: number | null; // 0-10
  retry_count?: number;
  parent_agent_id?: string | null;
  tags?: string[];
}

export interface AgentResult {
  success: boolean;
  output?: string | Record<string, unknown> | Array<unknown> | null;
  error?: string | null;
  metrics?: Record<string, number>;
  artifacts?: string[];
  execution_time_ms?: number | null;
}

export interface AgentState {
  user_request: string;
  chat_thread_id?: string | null;
  user_id?: string | null;
  
  // Status and lifecycle
  status?: AgentStatus;
  start_time?: string | null; // ISO datetime string
  end_time?: string | null; // ISO datetime string
  
  // Results from different agent types  
  triage_result?: unknown | null;
  data_result?: unknown | null;
  optimizations_result?: unknown | null;
  action_plan_result?: unknown | null;
  report_result?: unknown | null;
  synthetic_data_result?: unknown | null;
  supply_research_result?: unknown | null;
  
  // Execution tracking
  final_report?: string | null;
  step_count?: number;
  tool_results?: ToolResultData[] | null;
  error_message?: string | null;
  error_details?: Record<string, string | number | Record<string, unknown>> | null;
  performance_metrics?: Record<string, number>;
  
  // Metadata
  metadata?: AgentMetadata;
}

// ============================================================================
// WEBSOCKET MODELS - Consolidated and aligned
// ============================================================================

export interface WebSocketError {
  message: string;
  error_type?: string | null;
  code?: string | null;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  details?: Record<string, unknown> | null;
  trace_id?: string | null;
  timestamp?: string; // ISO datetime string
}

export interface BaseWebSocketPayload {
  timestamp?: string; // ISO datetime string
  correlation_id?: string;
}

export interface UserMessagePayload extends BaseWebSocketPayload {
  text: string;
  references?: string[];
  thread_id?: string | null;
  attachments?: Array<Record<string, unknown>> | null;
}

export interface AgentUpdatePayload extends BaseWebSocketPayload {
  run_id: string;
  agent_id: string;
  status: AgentStatus;
  message?: string | null;
  progress?: number | null; // 0-100
  current_task?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface WebSocketMessage {
  type: WebSocketMessageType;
  payload: Record<string, unknown> | BaseWebSocketPayload | UserMessagePayload | AgentUpdatePayload;
  sender?: string | null;
  timestamp?: string; // ISO datetime string
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

export type MessageRole = MessageType;
export type MessageStatus = 'pending' | 'sent' | 'delivered' | 'read' | 'failed';

export interface MessageAttachment {
  id: string;
  filename: string;
  mimeType: string;
  size: number;
  url?: string;
  thumbnailUrl?: string;
}

export interface MessageReaction {
  emoji: string;
  userId: string;  
  timestamp: Date;
}

// ============================================================================
// TYPE REGISTRY MAP
// ============================================================================

export const TYPE_REGISTRY = {
  // Enums
  MessageType,
  AgentStatus,
  WebSocketMessageType,
  
  // Core types - note: interfaces can't be stored in runtime registry
  // but we document them here for reference
} as const;

export type RegisteredTypeName = keyof typeof TYPE_REGISTRY;

// ============================================================================
// VALIDATION HELPERS
// ============================================================================

export function isValidMessageType(value: string): value is MessageType {
  return Object.values(MessageType).includes(value as MessageType);
}

export function isValidAgentStatus(value: string): value is AgentStatus {
  return Object.values(AgentStatus).includes(value as AgentStatus);
}

export function isValidWebSocketMessageType(value: string): value is WebSocketMessageType {
  return Object.values(WebSocketMessageType).includes(value as WebSocketMessageType);
}

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

// ============================================================================
// EXPORTS - All unified types available from single import
// ============================================================================

export type {
  // Core domain types
  User,
  Message,
  MessageMetadata,
  Thread,
  ThreadMetadata,
  
  // Agent types
  AgentState,
  AgentResult,
  AgentMetadata,
  ToolResultData,
  
  // WebSocket types  
  WebSocketMessage,
  WebSocketError,
  BaseWebSocketPayload,
  UserMessagePayload,
  AgentUpdatePayload,
  
  // Utility types
  MessageAttachment,
  MessageReaction,
  MessageRole,
  MessageStatus,
  RegisteredTypeName
};

// Default export for convenience
export default {
  MessageType,
  AgentStatus, 
  WebSocketMessageType,
  createWebSocketError,
  isValidMessageType,
  isValidAgentStatus,
  isValidWebSocketMessageType
};