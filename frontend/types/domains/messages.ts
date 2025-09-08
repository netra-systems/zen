/**
 * Message Domain Types - Extracted from Type Registry
 * 
 * This module contains all message-related type definitions, interfaces, and utilities
 * for the Netra frontend application. It serves as the single source of truth for
 * message handling across the system.
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - All functions ≤8 lines (MANDATORY)
 * - Module ≤300 lines total
 * - Strong type safety with comprehensive interfaces
 * - Backward compatibility maintained
 * 
 * Usage:
 *   import { Message, MessageRole, createMessage } from '@/types/domains/messages';
 */

import { MessageType } from '../shared/enums';
import type { BaseMessage } from '../shared/base';

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
  
  // Formatting metadata for consistent rendering
  formattingMetadata?: {
    preserveWhitespace: boolean;
    renderMarkdown: boolean;
    parseLinks: boolean;
    highlightCode: boolean;
    contentType: 'plain_text' | 'markdown' | 'code' | 'json' | 'error' | 'system';
    formatVersion: string;
  };
  
  [key: string]: unknown;
}

/**
 * Message roles - consolidated from all definitions
 * Supports user, assistant, and system messages for complete chat functionality
 */
export type MessageRole = 'user' | 'assistant' | 'system';

// BaseMessage is now imported from shared/base.ts as the single source of truth

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
// MESSAGE CREATION UTILITIES
// ============================================================================

/**
 * Create a message with the specified role, content, and optional properties
 * Generates unique ID and timestamps automatically
 */
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

/**
 * Create a chat message (alias for createMessage)
 * Provides backward compatibility for components expecting this function name
 */
export function createChatMessage(
  role: MessageRole,
  content: string,
  options: Partial<ChatMessage> = {}
): ChatMessage {
  return createMessage(role, content, options);
}

// ============================================================================
// BACKWARDS COMPATIBILITY EXPORTS
// ============================================================================

// Re-export types for components that expect different names
export { Message as ChatMessageType };
// BaseMessage is imported from shared/base.ts and re-exported as BaseChatMessage for compatibility
export { BaseMessage as BaseChatMessage };

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