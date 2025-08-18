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
// COMPREHENSIVE WEBSOCKET MESSAGE INTERFACE
// ============================================================================

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
  timestamp?: string;
}

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
// WEBSOCKET MESSAGE CREATION - Each function ≤8 lines
// ============================================================================

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

export type MessageTypeLiteral = keyof typeof WebSocketMessageType;
export type WebSocketPayload = WebSocketMessage['payload'];

// ============================================================================
// DEFAULT EXPORT FOR CONVENIENCE
// ============================================================================

export default {
  createWebSocketError,
  createWebSocketMessage,
  isWebSocketMessage,
  isAgentStartedMessage,
  isAgentCompletedMessage,
  isSubAgentUpdateMessage,
  isToolCallMessage,
  isErrorMessage,
  isUserMessagePayload,
  isAgentUpdateMessage
};