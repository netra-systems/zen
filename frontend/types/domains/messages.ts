/**
 * Messages Domain: Comprehensive Message Types
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - Single source of truth for message types
 * - Maximum file size: 300 lines
 * - Functions ≤8 lines each
 */

import { MessageRole, MessageType } from '../shared/enums';
import { BaseMessage, MessageMetadata, MessageAttachment, MessageReaction } from '../shared/base';

// ============================================================================
// UNIFIED MESSAGE HIERARCHY - Single Source of Truth
// ============================================================================

/**
 * Comprehensive Message interface - consolidated from all sources
 * Combines properties from chat.ts, chat-store.ts, DemoChat.types.ts, and backend schema
 * This is the SINGLE SOURCE OF TRUTH for all message handling
 */
export interface Message extends BaseMessage {
  role: MessageRole; // Make role required for Message (not optional like BaseMessage)
  
  // Threading and context
  threadId?: string;
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
    mimeType?: string;
    preview?: string;
    thumbnailUrl?: string;
  }>;
  
  // Reactions and social features
  reactions?: MessageReaction[];
  
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

// Re-export types for components that expect different names
export { Message as ChatMessageType };
export { BaseMessage as BaseChatMessage };

// ============================================================================
// MESSAGE DATA TRANSFER OBJECTS
// ============================================================================

export interface MessageData {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  timestamp: string;
  metadata?: Record<string, string | number | boolean>;
}

export interface ThreadHistoryResponse {
  thread_id: string;
  messages: MessageData[];
}

// ============================================================================
// MESSAGE CREATION UTILITIES - Each function ≤8 lines
// ============================================================================

export function createMessage(
  role: MessageRole,
  content: string,
  options: Partial<Message> = {}
): Message {
  const id = options.id || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  const timestamp = options.timestamp || Date.now();
  const created_at = options.created_at || new Date().toISOString();
  
  return {
    id,
    role,
    content,
    timestamp,
    created_at,
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

export function createUserMessage(
  content: string,
  options: Partial<Message> = {}
): Message {
  return createMessage('user', content, options);
}

export function createAssistantMessage(
  content: string,
  options: Partial<Message> = {}
): Message {
  return createMessage('assistant', content, options);
}

export function createSystemMessage(
  content: string,
  options: Partial<Message> = {}
): Message {
  return createMessage('system', content, options);
}

// ============================================================================
// MESSAGE VALIDATION - Each function ≤8 lines
// ============================================================================

export function isValidMessage(obj: unknown): obj is Message {
  if (typeof obj !== 'object' || obj === null) return false;
  const msg = obj as Message;
  return (
    typeof msg.id === 'string' &&
    typeof msg.content === 'string' &&
    typeof msg.role === 'string'
  );
}

export function isUserMessage(message: Message): boolean {
  return message.role === 'user';
}

export function isAssistantMessage(message: Message): boolean {
  return message.role === 'assistant';
}

export function isSystemMessage(message: Message): boolean {
  return message.role === 'system';
}

export function hasAttachments(message: Message): boolean {
  return Boolean(message.attachments && message.attachments.length > 0);
}

export function hasReactions(message: Message): boolean {
  return Boolean(message.reactions && message.reactions.length > 0);
}

export function isEdited(message: Message): boolean {
  return Boolean(message.is_edited || message.edited_at);
}

export function hasMetadata(message: Message): boolean {
  return Boolean(message.metadata && Object.keys(message.metadata).length > 0);
}

// ============================================================================
// MESSAGE SORTING AND FILTERING - Each function ≤8 lines
// ============================================================================

export function sortMessagesByTimestamp(messages: Message[]): Message[] {
  return [...messages].sort((a, b) => {
    const aTime = a.timestamp || 0;
    const bTime = b.timestamp || 0;
    const aNum = typeof aTime === 'number' ? aTime : new Date(aTime).getTime();
    const bNum = typeof bTime === 'number' ? bTime : new Date(bTime).getTime();
    return aNum - bNum;
  });
}

export function filterMessagesByRole(
  messages: Message[],
  role: MessageRole
): Message[] {
  return messages.filter(msg => msg.role === role);
}

export function filterMessagesByThread(
  messages: Message[],
  threadId: string
): Message[] {
  return messages.filter(msg => 
    msg.thread_id === threadId || msg.threadId === threadId
  );
}

export function getRecentMessages(
  messages: Message[],
  count: number
): Message[] {
  const sorted = sortMessagesByTimestamp(messages);
  return sorted.slice(-count);
}

// ============================================================================
// MESSAGE TRANSFORMATION - Each function ≤8 lines
// ============================================================================

export function messageToData(message: Message): MessageData {
  return {
    id: message.id,
    role: message.role as "user" | "assistant" | "system" | "tool",
    content: message.content,
    timestamp: message.created_at || new Date().toISOString(),
    metadata: message.metadata as Record<string, string | number | boolean>
  };
}

export function dataToMessage(data: MessageData): Message {
  return {
    id: data.id,
    role: data.role as MessageRole,
    content: data.content,
    created_at: data.timestamp,
    timestamp: new Date(data.timestamp).getTime(),
    metadata: data.metadata
  };
}

// ============================================================================
// DEFAULT EXPORT FOR CONVENIENCE
// ============================================================================

export default {
  createMessage,
  createChatMessage,
  createUserMessage,
  createAssistantMessage,
  createSystemMessage,
  isValidMessage,
  isUserMessage,
  isAssistantMessage,
  isSystemMessage,
  sortMessagesByTimestamp,
  filterMessagesByRole,
  filterMessagesByThread
};