/**
 * UNIFIED WebSocket Types - Single Source of Truth
 * 
 * Consolidates ALL WebSocket-related types from:
 * - types/domains/websocket.ts
 * - types/backend-sync/websockets.ts
 * - types/websocket-*.ts files
 * - components and other scattered definitions
 * 
 * CRITICAL: This file replaces ALL other WebSocket type definitions
 * Use ONLY these types for WebSocket communication
 */

// Re-export the comprehensive WebSocket types from domains
export type {
  // Core WebSocket message interface
  WebSocketMessage,
  WebSocketPayload,
  MessageTypeLiteral,
  
  // All payload types
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
  PongMessage,
  
  // Base types
  BaseWebSocketPayload
} from '../domains/websocket';

// Re-export all utility functions
export {
  // Type guards
  isWebSocketMessage,
  isAgentStartedMessage,
  isAgentCompletedMessage,
  isSubAgentUpdateMessage,
  isToolCallMessage,
  isErrorMessage,
  isUserMessagePayload,
  isAgentUpdateMessage,
  
  // Utility functions
  createWebSocketMessage,
  createWebSocketError,
  createAgentResult,
  isValidWebSocketMessageType
} from '../domains/websocket';

// Re-export enums
export { MessageType, WebSocketMessageType, AgentStatus } from '../shared/enums';