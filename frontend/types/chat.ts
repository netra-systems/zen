/**
 * Consolidated Chat Types - Single Source of Truth
 * 
 * This file consolidates all chat-related types from across the frontend codebase
 * to eliminate duplication and ensure consistency. All imports should use this file.
 * 
 * BUSINESS VALUE JUSTIFICATION (BVJ):
 * - All segments benefit from consistent chat functionality
 * - Type safety prevents runtime errors that could disrupt user experience
 * - Single source of truth reduces maintenance overhead
 */

import type { Message as BackendMessage, SubAgentLifecycle, SubAgentState } from './backend_schema_base';
import type { ToolStatus } from './backend_schema_base';
import type { ToolInput, ToolResult } from './backend_schema_tools';

// ============================================================================
// CORE MESSAGE TYPES - Consolidated from all sources
// ============================================================================

/**
 * Message roles - consolidated from all definitions
 * Supports user, assistant, and system messages for complete chat functionality
 */
export type MessageRole = 'user' | 'assistant' | 'system';

/**
 * Comprehensive message metadata - merged from all sources
 * Includes properties from chat-store, threadService, and registry definitions
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
  [key: string]: unknown;
}

/**
 * Comprehensive ChatMessage interface - consolidated from all sources
 * Combines the best features from components/chat/types, websocket-event-types, and backend schema
 */
export interface ChatMessage {
  // Core message properties
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  
  // Thread and context
  threadId?: string;
  threadTitle?: string;
  thread_id?: string; // Backend compatibility
  
  // Metadata and enrichment
  metadata?: MessageMetadata;
  references?: string[];
  error?: string;
  
  // Backend compatibility
  created_at?: string;
  displayed_to_user?: boolean;
  sub_agent_name?: string | null;
  tool_info?: Record<string, unknown> | null;
  raw_data?: Record<string, unknown> | null;
  attachments?: Array<Record<string, unknown>> | null;
}

// Re-export as Message for backwards compatibility
export type Message = ChatMessage;

// ============================================================================
// BACKEND COMPATIBILITY EXPORTS
// ============================================================================

// Re-export backend types for compatibility
export type { SubAgentLifecycle, SubAgentState };
export type { ToolStatus, ToolInput, ToolResult };

// Export enum-like object for SubAgentLifecycle for easier usage
export const SubAgentLifecycleEnum = {
  PENDING: "pending" as const,
  RUNNING: "running" as const,
  COMPLETED: "completed" as const,
  FAILED: "failed" as const,
  SHUTDOWN: "shutdown" as const,
} as const;

// ============================================================================
// WEBSOCKET COMPATIBILITY
// ============================================================================

export interface ChatWebSocketMessage {
  type: "analysis_request" | "error" | "stream_event" | "run_complete" | "sub_agent_update" | "agent_started" | "agent_completed" | "agent_error" | "message";
  payload: any;
}

// ============================================================================
// UTILITY TYPES AND HELPERS
// ============================================================================

/**
 * Message type enumeration for better type safety
 */
export type MessageType = 'user' | 'ai' | 'error' | 'system' | 'tool_call' | 'tool_result' | 'thinking';

/**
 * Message creation helpers
 */
export interface MessageBuilder {
  user: (content: string, options?: Partial<ChatMessage>) => ChatMessage;
  assistant: (content: string, options?: Partial<ChatMessage>) => ChatMessage;
  system: (content: string, options?: Partial<ChatMessage>) => ChatMessage;
  error: (error: string, options?: Partial<ChatMessage>) => ChatMessage;
}

/**
 * Message validation helpers
 */
export function isValidMessageRole(role: string): role is MessageRole {
  return ['user', 'assistant', 'system'].includes(role);
}

export function createChatMessage(
  role: MessageRole,
  content: string,
  options: Partial<ChatMessage> = {}
): ChatMessage {
  return {
    id: options.id || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    role,
    content,
    timestamp: options.timestamp || Date.now(),
    ...options
  };
}