/**
 * Shared Enums: Core System Enumerations
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - Single source of truth for all enums
 * - Maximum file size: 300 lines
 * - Backend-aligned enum values
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
// UTILITY TYPE ALIASES
// ============================================================================

export type MessageRole = 'user' | 'assistant' | 'system';
export type MessageStatus = 'pending' | 'sent' | 'delivered' | 'read' | 'failed';

// ============================================================================
// VALIDATION HELPERS - Each function ≤8 lines
// ============================================================================

export function isValidMessageType(value: string): value is MessageType {
  return Object.values(MessageType).includes(value as MessageType);
}

export function isValidAgentStatus(value: string): value is AgentStatus {
  return Object.values(AgentStatus).includes(value as AgentStatus);
}

export function isValidWebSocketMessageType(
  value: string
): value is WebSocketMessageType {
  return Object.values(WebSocketMessageType).includes(
    value as WebSocketMessageType
  );
}

export function isValidMessageRole(value: string): value is MessageRole {
  return ['user', 'assistant', 'system'].includes(value);
}

export function isValidMessageStatus(value: string): value is MessageStatus {
  const validStatuses = ['pending', 'sent', 'delivered', 'read', 'failed'];
  return validStatuses.includes(value);
}

// ============================================================================
// TYPE REGISTRY MAP
// ============================================================================

export const TYPE_REGISTRY = {
  MessageType,
  AgentStatus,
  WebSocketMessageType,
} as const;

export type RegisteredTypeName = keyof typeof TYPE_REGISTRY;

// ============================================================================
// ENUM UTILITIES - Each function ≤8 lines
// ============================================================================

export function getMessageTypeValues(): MessageType[] {
  return Object.values(MessageType);
}

export function getAgentStatusValues(): AgentStatus[] {
  return Object.values(AgentStatus);
}

export function getWebSocketMessageTypeValues(): WebSocketMessageType[] {
  return Object.values(WebSocketMessageType);
}

export function isActiveAgentStatus(status: AgentStatus): boolean {
  const activeStatuses = [
    AgentStatus.ACTIVE,
    AgentStatus.THINKING,
    AgentStatus.PLANNING,
    AgentStatus.EXECUTING,
    AgentStatus.RUNNING
  ];
  return activeStatuses.includes(status);
}

export function isCompletedAgentStatus(status: AgentStatus): boolean {
  const completedStatuses = [
    AgentStatus.COMPLETED,
    AgentStatus.FAILED,
    AgentStatus.ERROR,
    AgentStatus.CANCELLED
  ];
  return completedStatuses.includes(status);
}

// ============================================================================
// DEFAULT EXPORT FOR CONVENIENCE
// ============================================================================

export default {
  MessageType,
  AgentStatus,
  WebSocketMessageType,
  isValidMessageType,
  isValidAgentStatus,
  isValidWebSocketMessageType,
  isValidMessageRole,
  isValidMessageStatus,
  TYPE_REGISTRY
};