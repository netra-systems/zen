/**
 * Shared Base Types: Core Interfaces and Common Types
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - Single source of truth for base interfaces
 * - Maximum file size: 300 lines
 * - Functions ≤8 lines each
 */

import { MessageType, AgentStatus, WebSocketMessageType } from './enums';

// CORE ENUMS

export enum MessageRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
  AGENT = 'agent'
}

export enum MessageStatus {
  PENDING = 'pending',
  SENDING = 'sending',
  SENT = 'sent',
  DELIVERED = 'delivered',
  READ = 'read',
  FAILED = 'failed',
  RETRYING = 'retrying'
}

// BASE INTERFACES

export interface BaseEntity {
  id: string;
  created_at?: string;
  updated_at?: string;
}

export interface BaseTimestampEntity extends BaseEntity {
  created_at: string;
  updated_at: string;
  version?: number;
}

export interface BaseMetadata {
  version?: string;
  source?: string;
  tags?: string[];
  custom_fields?: Record<string, unknown>;
  [key: string]: unknown;
}
export interface BaseMessage extends BaseEntity {
  id: string;
  content: string;
  role?: MessageRole;
  type?: MessageType;
  created_at?: string;
  timestamp?: number | Date;
  displayed_to_user?: boolean;
  error?: string;
  thread_id?: string | null;
}

export interface BaseWebSocketPayload {
  timestamp?: string;
  correlation_id?: string;
  message_id?: string;
}

// SHARED METADATA INTERFACES

export interface MessageAttachment {
  id: string;
  filename: string;
  mimeType: string;
  size: number;
  url?: string;
  thumbnailUrl?: string;
  type?: 'image' | 'file' | 'link' | 'code' | 'data';
  name?: string;
  mime_type?: string;
  preview?: string;
}

export interface MessageReaction {
  emoji: string;
  count: number;
  users: string[];
  timestamp: string;
  userId?: string;
}

export interface MessageMetadata {
  sub_agent?: string;
  tool_name?: string;
  execution_time_ms?: number;
  agent_name?: string;
  token_count?: number;
  model_used?: string;
  confidence_score?: number;
  source?: string;
  references?: string[];
  attachments?: MessageAttachment[];
  is_streaming?: boolean;
  chunk_index?: number;
  model?: string;
  tokens_used?: number;
  processing_time?: number;
  run_id?: string;
  step_id?: string;
  tool_calls?: Array<Record<string, unknown>>;
  custom_fields?: Record<string, string | number | boolean>;
  editedAt?: string;
  processingTime?: number;
  tokensUsed?: number;
  costSaved?: number;
  optimizationType?: string;
  [key: string]: unknown;
}

// USER AND AUTH TYPES - Use unified auth types instead
// These types are now re-exported from @/types/unified/auth.types
// which provides the canonical definitions from types/domains/auth.ts

// COMMON TYPE ALIASES & UTILITY TYPES

export type ID = string;
export type Timestamp = string | number | Date;
export type OptionalFields<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;
export type Nullable<T> = T | null;
export type Optional<T> = T | undefined;

// Generic status types
export type OperationStatus = 'idle' | 'loading' | 'success' | 'error';
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';
// TYPE REGISTRY - Runtime type information

export const TYPE_REGISTRY = {
  BASE_ENTITY: 'BaseEntity',
  BASE_TIMESTAMP_ENTITY: 'BaseTimestampEntity', 
  BASE_MESSAGE: 'BaseMessage',
  BASE_METADATA: 'BaseMetadata',
  MESSAGE_ATTACHMENT: 'MessageAttachment',
  MESSAGE_REACTION: 'MessageReaction',
  MESSAGE_METADATA: 'MessageMetadata',
  BASE_WEBSOCKET_PAYLOAD: 'BaseWebSocketPayload'
} as const;

export type TypeRegistryKey = keyof typeof TYPE_REGISTRY;
export type TypeRegistryValue = typeof TYPE_REGISTRY[TypeRegistryKey];
// UTILITY HELPER FUNCTIONS - Each ≤8 lines

export function createBaseMessage(
  role: MessageRole,
  content: string,
  options: Partial<BaseMessage> = {}
): BaseMessage {
  const timestamp = options.timestamp || Date.now();
  const created_at = options.created_at || new Date().toISOString();
  const id = options.id || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  return {
    id,
    role,
    content,
    timestamp,
    created_at,
    ...options
  };
}

export function createMessageAttachment(
  filename: string,
  mimeType: string,
  size: number,
  options: Partial<MessageAttachment> = {}
): MessageAttachment {
  const id = options.id || `att_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  return {
    id,
    filename,
    mimeType,
    size,
    ...options
  };
}

export function createMessageReaction(
  emoji: string,
  user: string,
  timestamp?: string
): MessageReaction {
  return {
    emoji,
    count: 1,
    users: [user],
    timestamp: timestamp || new Date().toISOString()
  };
}

// isValidUser function moved to @/types/unified/auth.types

export function hasRequiredMessageFields(obj: unknown): obj is BaseMessage {
  if (typeof obj !== 'object' || obj === null) return false;
  const msg = obj as BaseMessage;
  return typeof msg.id === 'string' && typeof msg.content === 'string';
}

export function createBaseEntity(id?: string): BaseEntity {
  const timestamp = new Date().toISOString();
  return {
    id: id || `entity_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    created_at: timestamp,
    updated_at: timestamp
  };
}

export function createTimestampEntity(id?: string): BaseTimestampEntity {
  const timestamp = new Date().toISOString();
  return {
    id: id || `ts_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    created_at: timestamp,
    updated_at: timestamp,
    version: 1
  };
}

export function createBaseMetadata(source?: string): BaseMetadata {
  return {
    version: '1.0.0',
    source: source || 'system',
    tags: [],
    custom_fields: {}
  };
}

export function getTypeFromRegistry(key: TypeRegistryKey): TypeRegistryValue {
  return TYPE_REGISTRY[key];
}

export function isValidEntity(obj: unknown): obj is BaseEntity {
  if (typeof obj !== 'object' || obj === null) return false;
  const entity = obj as BaseEntity;
  return typeof entity.id === 'string';
}

// DEFAULT EXPORT

// Explicit re-exports for interfaces (TypeScript compiler compatibility)
export type { BaseMessage };
export type { BaseEntity };
export type { BaseTimestampEntity };
export type { BaseMetadata };

export default {
  createBaseMessage,
  createMessageAttachment,
  createMessageReaction,
  createBaseEntity,
  createTimestampEntity,
  createBaseMetadata,
  hasRequiredMessageFields,
  isValidEntity,
  getTypeFromRegistry,
  TYPE_REGISTRY,
  MessageRole,
  MessageStatus
};