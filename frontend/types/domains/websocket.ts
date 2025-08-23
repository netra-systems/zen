/**
 * WebSocket Domain Types - Single Source of Truth
 * 
 * Extracted from registry.ts for modular architecture compliance.
 * All WebSocket message types, payloads, and utilities consolidated here.
 * 
 * CRITICAL: Maximum 300 lines, 8 lines per function
 */

import { WebSocketMessageType, AgentStatus, isValidWebSocketMessageType } from '../shared/enums';
import { BaseWebSocketPayload } from '../shared/base';

// Re-export TYPE-ONLY interfaces from backend-sync for consolidated access
export type {
  AgentResult,
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
  PongMessage
} from '../backend-sync/payloads';

// Re-export RUNTIME utility functions
export {
  createWebSocketError,
  createAgentResult
} from '../backend-sync/payloads';

// Re-export base types
export type { BaseWebSocketPayload } from '../shared/base';

// Re-export enum validation function
export { isValidWebSocketMessageType } from '../shared/enums';

// ============================================================================
// WEBSOCKET MESSAGE TYPE IMPORTS
// ============================================================================

// Import types from backend-sync for use in WebSocketMessage interface
import type {
  AgentResult,
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
  PongMessage
} from '../backend-sync/payloads';

// ============================================================================
// WEBSOCKET MESSAGE INTERFACE - SINGLE SOURCE OF TRUTH
// ============================================================================

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
  timestamp?: string; // ISO datetime string
}


// ============================================================================
// TYPE GUARDS AND VALIDATION
// ============================================================================

export function isWebSocketMessage(obj: unknown): obj is WebSocketMessage {
  return typeof obj === 'object' && 
         obj !== null && 
         'type' in obj && 
         'payload' in obj;
}

export function isAgentStartedMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: AgentStartedPayload } {
  return msg.type === WebSocketMessageType.AGENT_STARTED;
}

export function isAgentCompletedMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: AgentCompletedPayload } {
  return msg.type === WebSocketMessageType.AGENT_COMPLETED;
}

export function isSubAgentUpdateMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: SubAgentUpdatePayload } {
  return msg.type === WebSocketMessageType.SUB_AGENT_UPDATE;
}

export function isToolCallMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: ToolCallPayload } {
  return msg.type === WebSocketMessageType.TOOL_CALL;
}

export function isErrorMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: ErrorPayload } {
  return msg.type === WebSocketMessageType.ERROR;
}

export function isUserMessagePayload(msg: WebSocketMessage): msg is WebSocketMessage & { payload: UserMessagePayload } {
  return msg.type === WebSocketMessageType.USER_MESSAGE || msg.type === WebSocketMessageType.CHAT_MESSAGE;
}

export function isAgentUpdateMessage(msg: WebSocketMessage): msg is WebSocketMessage & { payload: AgentUpdatePayload } {
  return msg.type === WebSocketMessageType.AGENT_UPDATE;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

// Re-export createWebSocketError from backend-sync
// Already exported above

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

// ============================================================================
// UTILITY TYPES
// ============================================================================

export type MessageTypeLiteral = keyof typeof WebSocketMessageType;
export type WebSocketPayload = WebSocketMessage['payload'];
