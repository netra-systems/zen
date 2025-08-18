/**
 * Chat Types - Re-exports from Type Registry
 * 
 * This file now serves as a compatibility layer that re-exports all chat-related types
 * from the unified type registry. All types are now consolidated in registry.ts.
 * 
 * BUSINESS VALUE JUSTIFICATION (BVJ):
 * - All segments benefit from consistent chat functionality
 * - Type safety prevents runtime errors that could disrupt user experience
 * - Single source of truth reduces maintenance overhead
 */

// Import all message types from the unified registry
import type { 
  Message,
  BaseMessage,
  ChatMessage,
  MessageRole,
  MessageMetadata,
  createMessage,
  createChatMessage
} from './registry';
import { MessageType } from './registry';

// Import backend compatibility types
import type { SubAgentLifecycle, SubAgentState } from './backend_schema_base';
import type { ToolStatus } from './backend_schema_base';
import type { ToolInput, ToolResult } from './backend_schema_tools';

// ============================================================================
// RE-EXPORTS FROM REGISTRY - Single Source of Truth
// ============================================================================

// Core message types (now from registry)
export type { Message, BaseMessage, ChatMessage, MessageRole, MessageMetadata };
export { MessageType };

// Message creation utilities
export { createMessage, createChatMessage };

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

// Re-export WebSocketMessage from registry for backward compatibility
export { WebSocketMessage, WebSocketError, WebSocketMessageType } from './registry';

// ============================================================================
// UTILITY TYPES AND HELPERS
// ============================================================================

/**
 * Message creation helpers interface
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