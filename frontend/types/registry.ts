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

/**
 * Comprehensive WebSocket Message Types - SINGLE SOURCE OF TRUTH
 * Consolidated from backend_schema_auto_generated.ts and enhanced for all WebSocket operations
 * DO NOT duplicate these types anywhere else in the frontend
 */
export enum WebSocketMessageType {
  // Client to server
  START_AGENT = 'start_agent',
  USER_MESSAGE = 'user_message',
  CHAT_MESSAGE = 'chat_message',
  STOP_AGENT = 'stop_agent',
  CREATE_THREAD = 'create_thread',
  SWITCH_THREAD = 'switch_thread',
  DELETE_THREAD = 'delete_thread',
  RENAME_THREAD = 'rename_thread',
  LIST_THREADS = 'list_threads',
  GET_THREAD_HISTORY = 'get_thread_history',
  PING = 'ping',
  PONG = 'pong',
  
  // Server to client - Agent events
  AGENT_STARTED = 'agent_started',
  AGENT_COMPLETED = 'agent_completed',
  AGENT_STOPPED = 'agent_stopped',
  AGENT_ERROR = 'agent_error',
  AGENT_UPDATE = 'agent_update',
  AGENT_LOG = 'agent_log',
  AGENT_THINKING = 'agent_thinking',
  AGENT_FALLBACK = 'agent_fallback',
  
  // Tool events
  TOOL_STARTED = 'tool_started',
  TOOL_COMPLETED = 'tool_completed',
  TOOL_CALL = 'tool_call',
  TOOL_RESULT = 'tool_result',
  TOOL_EXECUTING = 'tool_executing',
  
  // Sub-agent events
  SUBAGENT_STARTED = 'subagent_started',
  SUBAGENT_COMPLETED = 'subagent_completed',
  SUB_AGENT_UPDATE = 'sub_agent_update',
  
  // Thread events
  THREAD_HISTORY = 'thread_history',
  THREAD_CREATED = 'thread_created',
  THREAD_UPDATED = 'thread_updated',
  THREAD_DELETED = 'thread_deleted',
  THREAD_LOADED = 'thread_loaded',
  THREAD_RENAMED = 'thread_renamed',
  STEP_CREATED = 'step_created',
  
  // Generation and streaming
  PARTIAL_RESULT = 'partial_result',
  FINAL_REPORT = 'final_report',
  STREAM_CHUNK = 'stream_chunk',
  STREAM_COMPLETE = 'stream_complete',
  GENERATION_PROGRESS = 'generation_progress',
  GENERATION_COMPLETE = 'generation_complete',
  GENERATION_ERROR = 'generation_error',
  BATCH_COMPLETE = 'batch_complete',
  
  // System events
  ERROR = 'error',
  CONNECTION_ESTABLISHED = 'connection_established'
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

export interface AuthEndpoints {
  login: string;
  logout: string;
  token: string;
  user: string;
  dev_login: string;
}

export interface AuthConfigResponse {
  google_client_id: string;
  endpoints: AuthEndpoints;
  development_mode: boolean;
  user?: User | null;
  authorized_javascript_origins: string[];
  authorized_redirect_uris: string[];
  google_login_url?: string;
  logout_url?: string;
}

// ============================================================================
// UNIFIED MESSAGE HIERARCHY - Single Source of Truth
// ============================================================================

/**
 * Comprehensive message metadata - merged from all sources
 * Includes properties from chat-store, threadService, and all component definitions
 */
export interface MessageMetadata {
  // Agent and tool information
  sub_agent?: string;
  tool_name?: string;
  execution_time_ms?: number;
  agent_name?: string;
  
  // Content and processing metadata
  token_count?: number;
  model_used?: string;
  confidence_score?: number;
  source?: string;
  
  // References and attachments
  references?: string[];
  attachments?: Array<{
    id: string;
    filename: string;
    mimeType: string;
    size: number;
    url?: string;
    thumbnailUrl?: string;
  }>;
  
  // Streaming and processing state
  is_streaming?: boolean;
  chunk_index?: number;
  
  // Backend compatibility
  model?: string;
  tokens_used?: number;
  processing_time?: number;
  run_id?: string;
  step_id?: string;
  tool_calls?: Array<Record<string, unknown>>;
  custom_fields?: Record<string, string | number | boolean>;
  
  // UI state
  editedAt?: string;
  
  // Demo chat compatibility
  processingTime?: number;
  tokensUsed?: number;
  costSaved?: number;
  optimizationType?: string;
  
  [key: string]: unknown;
}

/**
 * Message roles - consolidated from all definitions
 * Supports user, assistant, and system messages for complete chat functionality
 */
export type MessageRole = 'user' | 'assistant' | 'system';

/**
 * Base message interface with core fields
 * Foundation for all message types across the system
 */
export interface BaseMessage {
  id: string;
  content: string;
  role?: MessageRole;
  type?: MessageType;
  created_at?: string;
  timestamp?: number | Date; // Support both number and Date for compatibility
  displayed_to_user?: boolean;
  error?: string;
  thread_id?: string | null;
}

/**
 * Comprehensive Message interface - consolidated from all sources
 * Combines properties from chat.ts, chat-store.ts, DemoChat.types.ts, and backend schema
 * This is the SINGLE SOURCE OF TRUTH for all message handling
 */
export interface Message extends BaseMessage {
  // Core message properties (ensuring all variations are covered)
  role: MessageRole; // Make role required for Message (not optional like BaseMessage)
  
  // Threading and context
  threadId?: string; // Frontend camelCase version
  threadTitle?: string;
  
  // Metadata and enrichment (comprehensive from all sources)
  metadata?: MessageMetadata;
  references?: string[];
  
  // Attachments (comprehensive format)
  attachments?: Array<{
    id: string;
    type?: 'image' | 'file' | 'link' | 'code' | 'data';
    url?: string;
    name?: string;
    filename?: string;
    size?: number;
    mime_type?: string;
    mimeType?: string; // Support both formats
    preview?: string;
    thumbnailUrl?: string;
  }>;
  
  // Reactions and social features (from chat-store)
  reactions?: Array<{
    emoji: string;
    count: number;
    users: string[];
    timestamp: string;
  }>;
  
  // Edit tracking
  edited_at?: string;
  is_edited?: boolean;
  reply_to?: string;
  mentions?: string[];
  
  // Backend compatibility fields
  sub_agent_name?: string | null;
  tool_info?: Record<string, unknown> | null;
  raw_data?: Record<string, unknown> | null;
  
  // Additional UI state
  updated_at?: string;
  last_updated?: string;
}

/**
 * Type alias for backward compatibility
 * Many components expect 'ChatMessage' but it's the same as Message
 */
export type ChatMessage = Message;

// ============================================================================
// BACKWARDS COMPATIBILITY EXPORTS
// ============================================================================

// Re-export types for components that expect different names
export { Message as ChatMessageType };
export { BaseMessage as BaseChatMessage };

// Export message creation utilities
export function createMessage(
  role: MessageRole,
  content: string,
  options: Partial<Message> = {}
): Message {
  return {
    id: options.id || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    role,
    content,
    timestamp: options.timestamp || Date.now(),
    created_at: options.created_at || new Date().toISOString(),
    ...options
  };
}

export function createChatMessage(
  role: MessageRole,
  content: string,
  options: Partial<ChatMessage> = {}
): ChatMessage {
  return createMessage(role, content, options);
}

/**
 * Unified ThreadMetadata - consolidated from all sources
 * Supports both registry and chat-store patterns
 */
export interface ThreadMetadata {
  // Core metadata (from registry)
  tags?: string[];
  priority?: number; // 0-10 (registry) or 'low'|'medium'|'high' (chat-store)
  category?: string | null;
  user_id?: string | null;
  custom_fields?: Record<string, string | number | boolean>;
  
  // Chat-store specific metadata
  optimization_results_count?: number;
  sub_agents_used?: string[];
  total_processing_time_ms?: number;
  user_rating?: number;
  bookmarked?: boolean;
  
  // Extended metadata for admin/special threads
  admin_type?: 'corpus' | 'synthetic' | 'users';
  title?: string; // Alternative title storage in metadata
  last_message?: string;
}

/**
 * Unified Thread interface - Single Source of Truth
 * 
 * BACKWARD COMPATIBILITY:
 * - Supports both 'name' (registry) and 'title' (chat-store) properties
 * - Includes all properties from both registry and chat-store versions
 * - Use getThreadTitle() helper for consistent title access
 * 
 * PROPERTY MAPPING:
 * - name/title: Both supported, title takes precedence if both exist
 * - status/is_active: Both supported, status takes precedence
 * - message_count: Optional for backward compatibility
 */
export interface Thread {
  // Core identifiers
  id: string;
  
  // Title/Name - Support both patterns for backward compatibility
  name?: string | null;              // Backend/registry pattern
  title?: string;                    // Frontend/chat-store pattern
  
  // Timestamps
  created_at: string; // ISO datetime string
  updated_at: string; // ISO datetime string
  
  // Content info
  message_count?: number;            // Optional for compatibility
  
  // Status - Support both patterns
  is_active?: boolean;               // Registry pattern
  status?: 'active' | 'archived' | 'deleted'; // Chat-store pattern
  
  // Messages
  last_message?: Message | null;     // Registry pattern (full message)
  last_message_preview?: string;     // Chat-store pattern (preview text)
  
  // Relationships
  participants?: string[] | null;
  
  // Metadata
  metadata?: ThreadMetadata | null;
  
  // Direct tags for compatibility (also available in metadata)
  tags?: string[];
}

// ============================================================================
// THREAD UTILITY FUNCTIONS - Backward Compatibility Helpers
// ============================================================================

/**
 * Get thread title with fallback priority:
 * 1. thread.title (chat-store pattern)
 * 2. thread.name (registry pattern)
 * 3. thread.metadata?.title (metadata storage)
 * 4. thread.metadata?.last_message (preview)
 * 5. Generated fallback with date
 */
export function getThreadTitle(thread: Thread): string {
  return thread.title || 
         thread.name || 
         thread.metadata?.title || 
         thread.metadata?.last_message || 
         `Chat ${new Date(thread.created_at).toLocaleDateString()}`;
}

/**
 * Get thread status with fallback:
 * 1. thread.status (chat-store pattern)
 * 2. thread.is_active -> 'active'/'archived' (registry pattern)
 * 3. 'active' (default)
 */
export function getThreadStatus(thread: Thread): 'active' | 'archived' | 'deleted' {
  if (thread.status) return thread.status;
  if (thread.is_active === false) return 'archived';
  if (thread.is_active === true) return 'active';
  return 'active';
}

/**
 * Check if thread is active using either pattern
 */
export function isThreadActive(thread: Thread): boolean {
  if (thread.status) return thread.status === 'active';
  return thread.is_active !== false; // Default to true
}

/**
 * Create Thread with dual property support for backward compatibility
 * Sets both name and title to the same value
 */
export function createThreadWithTitle(data: {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  [key: string]: unknown;
}): Thread {
  return {
    ...data,
    name: data.title,     // Registry compatibility
    title: data.title,    // Chat-store compatibility
  };
}

/**
 * ThreadState for store management - consolidated
 */
export interface ThreadState {
  threads: Thread[];
  activeThreadId: string | null;
  currentThread: Thread | null;
  isLoading: boolean;
  error: string | null;
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
  // Backend compatibility
  message?: string;
  data?: string | Record<string, unknown> | unknown[];
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

/**
 * COMPREHENSIVE WEBSOCKET PAYLOAD TYPES - SINGLE SOURCE OF TRUTH
 * Consolidated from backend_schema_auto_generated.ts with enhanced type safety
 * ALL WebSocket payloads must use these interfaces
 */

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

/**
 * COMPREHENSIVE WEBSOCKET MESSAGE INTERFACE - SINGLE SOURCE OF TRUTH
 * This interface consolidates all possible WebSocket message types and payloads
 * DO NOT create alternative WebSocketMessage interfaces
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
// SUPPORTING MESSAGE TYPES FOR AUTHENTICATION AND SYSTEM
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
// UTILITY TYPES
// ============================================================================

export type MessageStatus = 'pending' | 'sent' | 'delivered' | 'read' | 'failed';

export interface MessageAttachment {
  id: string;
  filename: string;
  mimeType: string;
  size: number;
  url?: string;
  thumbnailUrl?: string;
  // Chat-store compatibility
  type?: 'image' | 'file' | 'link' | 'code' | 'data';
  name?: string;
  mime_type?: string; // Snake case variant
  preview?: string;
}

export interface MessageReaction {
  emoji: string;
  count: number;
  users: string[];
  timestamp: string;
  // Legacy compatibility
  userId?: string;  
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

/**
 * COMPREHENSIVE TYPE GUARDS AND VALIDATION - SINGLE SOURCE OF TRUTH
 * Consolidated from backend_schema_auto_generated.ts for all WebSocket message validation
 */

// Type guard for WebSocket messages
export function isWebSocketMessage(obj: unknown): obj is WebSocketMessage {
  return typeof obj === 'object' && 
         obj !== null && 
         'type' in obj && 
         'payload' in obj;
}

// Specific message type guards
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

// Utility type definitions
export type MessageTypeLiteral = keyof typeof WebSocketMessageType;
export type WebSocketPayload = WebSocketMessage['payload'];

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
// EXPORTS - All unified types available from single import
// ============================================================================

// Note: Types are automatically exported via interface declarations above
// This export statement is removed to avoid conflicts

// Default export for convenience - includes all WebSocket functionality
export default {
  MessageType,
  AgentStatus, 
  WebSocketMessageType,
  createWebSocketError,
  createWebSocketMessage,
  isValidMessageType,
  isValidAgentStatus,
  isValidWebSocketMessageType,
  isWebSocketMessage,
  isAgentStartedMessage,
  isAgentCompletedMessage,
  isSubAgentUpdateMessage,
  isToolCallMessage,
  isErrorMessage,
  isUserMessagePayload,
  isAgentUpdateMessage
};