/**
 * Shared Base Types: Core Interfaces and Common Types
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - Single source of truth for base interfaces
 * - Maximum file size: 300 lines
 * - Functions ≤8 lines each
 */

import { MessageRole, MessageType } from './enums';

// ============================================================================
// BASE INTERFACES - Foundation Types
// ============================================================================

export interface BaseMessage {
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

// ============================================================================
// SHARED METADATA INTERFACES
// ============================================================================

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

// ============================================================================
// USER AND AUTH TYPES
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
// UTILITY HELPER FUNCTIONS - Each ≤8 lines
// ============================================================================

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

export function isValidUser(obj: unknown): obj is User {
  if (typeof obj !== 'object' || obj === null) return false;
  const user = obj as User;
  return typeof user.id === 'string' && typeof user.email === 'string';
}

export function hasRequiredMessageFields(obj: unknown): obj is BaseMessage {
  if (typeof obj !== 'object' || obj === null) return false;
  const msg = obj as BaseMessage;
  return typeof msg.id === 'string' && typeof msg.content === 'string';
}

// ============================================================================
// DEFAULT EXPORT FOR CONVENIENCE
// ============================================================================

export default {
  createBaseMessage,
  createMessageAttachment,
  createMessageReaction,
  isValidUser,
  hasRequiredMessageFields
};