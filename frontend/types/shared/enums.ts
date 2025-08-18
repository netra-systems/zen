/**
 * Core System Enums - Foundation Types
 * 
 * This module contains all fundamental enum definitions used throughout the Netra frontend.
 * These enums serve as the single source of truth for type constants and are aligned
 * with the Python backend for consistency.
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - Maximum file size: 300 lines
 * - All functions: ≤8 lines
 * - Single source of truth for all enum definitions
 * 
 * BVJ: Consistent enums = fewer bugs = better user experience
 */

// ============================================================================
// CORE DOMAIN ENUMS - Aligned with Python backend
// ============================================================================

/**
 * Message types used throughout the chat and communication system.
 * Aligned with backend MessageType enum for consistency.
 */
export enum MessageType {
  USER = 'user',
  ASSISTANT = 'assistant',
  AGENT = 'agent',
  SYSTEM = 'system',
  ERROR = 'error',
  TOOL = 'tool'
}

/**
 * Agent status values representing the complete lifecycle of agent operations.
 * Used for tracking agent state in real-time operations.
 */
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
 * Comprehensive WebSocket message types for all real-time communication.
 * This enum defines every possible WebSocket message type in the system.
 * DO NOT duplicate these types elsewhere in the frontend.
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
// VALIDATION HELPERS - All functions ≤8 lines
// ============================================================================

/**
 * Validates if a string is a valid MessageType enum value.
 * @param value - The string to validate
 * @returns True if valid MessageType, false otherwise
 */
export function isValidMessageType(value: string): value is MessageType {
  return Object.values(MessageType).includes(value as MessageType);
}

/**
 * Validates if a string is a valid AgentStatus enum value.
 * @param value - The string to validate
 * @returns True if valid AgentStatus, false otherwise
 */
export function isValidAgentStatus(value: string): value is AgentStatus {
  return Object.values(AgentStatus).includes(value as AgentStatus);
}

/**
 * Validates if a string is a valid WebSocketMessageType enum value.
 * @param value - The string to validate
 * @returns True if valid WebSocketMessageType, false otherwise
 */
export function isValidWebSocketMessageType(value: string): value is WebSocketMessageType {
  return Object.values(WebSocketMessageType).includes(value as WebSocketMessageType);
}

/**
 * Gets all values of the MessageType enum.
 * @returns Array of all MessageType values
 */
export function getMessageTypeValues(): MessageType[] {
  return Object.values(MessageType);
}

/**
 * Gets all values of the AgentStatus enum.
 * @returns Array of all AgentStatus values
 */
export function getAgentStatusValues(): AgentStatus[] {
  return Object.values(AgentStatus);
}

/**
 * Gets all values of the WebSocketMessageType enum.
 * @returns Array of all WebSocketMessageType values
 */
export function getWebSocketMessageTypeValues(): WebSocketMessageType[] {
  return Object.values(WebSocketMessageType);
}

/**
 * Generic enum key extraction utility.
 * @param enumObj - The enum object
 * @param value - The enum value
 * @returns The key name or undefined
 */
export function getEnumKey<T extends Record<string, string>>(
  enumObj: T,
  value: string
): keyof T | undefined {
  const entries = Object.entries(enumObj);
  const entry = entries.find(([_, v]) => v === value);
  return entry?.[0] as keyof T | undefined;
}

// ============================================================================
// ENUM REGISTRY - Runtime reflection support
// ============================================================================

/**
 * Registry of all enums for runtime access.
 * Note: TypeScript enums are runtime objects, so this works.
 */
export const ENUM_REGISTRY = {
  MessageType,
  AgentStatus,
  WebSocketMessageType
} as const;

/**
 * Type definition for registered enum names.
 */
export type RegisteredEnumName = keyof typeof ENUM_REGISTRY;

// ============================================================================
// DEFAULT EXPORT - All enums and utilities
// ============================================================================

export default {
  // Enums
  MessageType,
  AgentStatus,
  WebSocketMessageType,
  
  // Validation functions
  isValidMessageType,
  isValidAgentStatus,
  isValidWebSocketMessageType,
  
  // Utility functions
  getMessageTypeValues,
  getAgentStatusValues,
  getWebSocketMessageTypeValues,
  getEnumKey,
  
  // Registry
  ENUM_REGISTRY
};