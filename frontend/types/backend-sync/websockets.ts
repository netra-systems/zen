/**
 * Backend Sync: WebSocket Communication Types
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - Single source of truth for WebSocket types
 * - Maximum file size: 300 lines
 * - Functions ≤8 lines each
 * - Backend-aligned message formats
 */

import { WebSocketMessageType } from '../shared/enums';
import type { WebSocketMessage } from '../domains/websocket';

// Import all payload types from dedicated module
export * from './payloads';
import {
  WebSocketError,
  StartAgentPayload,
  UserMessagePayload,
  StopAgentPayload,
  CreateThreadPayload,
  SwitchThreadPayload,
  DeleteThreadPayload,
  AgentUpdatePayload,
  AgentStartedPayload,
  AgentCompletedPayload,
  SubAgentUpdatePayload,
  ToolCallPayload,
  ToolResultPayload,
  StreamChunkPayload,
  StreamCompletePayload,
  ErrorPayload,
  AuthMessage,
  PingMessage,
  PongMessage,
  createWebSocketError
} from './payloads';

// ============================================================================
// WEBSOCKET MESSAGE INTERFACE - MOVED TO CANONICAL LOCATION
// ============================================================================

/**
 * WebSocketMessage interface moved to domains/websocket.ts for single source of truth.
 * Import from '@/types/domains/websocket' or '@/types/unified' instead.
 * 
 * This file now focuses only on type guards and utility functions.
 */

// ============================================================================
// TYPE GUARDS AND VALIDATION - Each function ≤8 lines
// ============================================================================

export function isWebSocketMessage(obj: unknown): obj is WebSocketMessage {
  return typeof obj === 'object' && 
         obj !== null && 
         'type' in obj && 
         'payload' in obj;
}

export function isAgentStartedMessage(
  msg: WebSocketMessage
): msg is WebSocketMessage & { payload: AgentStartedPayload } {
  return msg.type === WebSocketMessageType.AGENT_STARTED;
}

export function isAgentCompletedMessage(
  msg: WebSocketMessage
): msg is WebSocketMessage & { payload: AgentCompletedPayload } {
  return msg.type === WebSocketMessageType.AGENT_COMPLETED;
}

export function isSubAgentUpdateMessage(
  msg: WebSocketMessage
): msg is WebSocketMessage & { payload: SubAgentUpdatePayload } {
  return msg.type === WebSocketMessageType.SUB_AGENT_UPDATE;
}

export function isToolCallMessage(
  msg: WebSocketMessage
): msg is WebSocketMessage & { payload: ToolCallPayload } {
  return msg.type === WebSocketMessageType.TOOL_CALL;
}

export function isErrorMessage(
  msg: WebSocketMessage
): msg is WebSocketMessage & { payload: ErrorPayload } {
  return msg.type === WebSocketMessageType.ERROR;
}

export function isUserMessagePayload(
  msg: WebSocketMessage
): msg is WebSocketMessage & { payload: UserMessagePayload } {
  const isUserMsg = msg.type === WebSocketMessageType.USER_MESSAGE;
  const isChatMsg = msg.type === WebSocketMessageType.CHAT_MESSAGE;
  return isUserMsg || isChatMsg;
}

export function isAgentUpdateMessage(
  msg: WebSocketMessage
): msg is WebSocketMessage & { payload: AgentUpdatePayload } {
  return msg.type === WebSocketMessageType.AGENT_UPDATE;
}

// ============================================================================
// WEBSOCKET MESSAGE UTILITIES - MOVED TO CANONICAL LOCATION
// ============================================================================

/**
 * createWebSocketMessage function moved to domains/websocket.ts for single source of truth.
 * Import from '@/types/domains/websocket' or '@/types/unified' instead.
 */

// Type aliases for backward compatibility - use canonical versions instead
export type MessageTypeLiteral = keyof typeof WebSocketMessageType;
export type WebSocketPayload = WebSocketMessage['payload'];

// ============================================================================
// DEFAULT EXPORT FOR CONVENIENCE
// ============================================================================

export default {
  createWebSocketError,
  isWebSocketMessage,
  isAgentStartedMessage,
  isAgentCompletedMessage,
  isSubAgentUpdateMessage,
  isToolCallMessage,
  isErrorMessage,
  isUserMessagePayload,
  isAgentUpdateMessage
};