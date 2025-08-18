/**
 * Type Registry: Modular Re-Export Hub
 * 
 * This module serves as the central registry for all type definitions in the Netra frontend,
 * re-exporting from modular domain and shared modules for better maintainability.
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - All type definitions MUST be imported from this registry 
 * - Maintains 100% backward compatibility with existing imports
 * - Module structure: shared/* for base types, domains/* for specific domains
 * - File size: <100 lines (MANDATORY)
 * 
 * MODULAR STRUCTURE:
 * - shared/enums.ts: Core enums (MessageType, AgentStatus, WebSocketMessageType)
 * - shared/base.ts: Base interfaces and common types
 * - domains/auth.ts: Authentication and user types
 * - domains/messages.ts: Message and chat types
 * - domains/threads.ts: Thread management types
 * - domains/websocket.ts: WebSocket communication types
 * - domains/agents.ts: Agent state and workflow types
 * - domains/tools.ts: Tool execution types
 * 
 * Usage:
 *   import { User, Message, AgentState, WebSocketMessage } from '@/types/registry';
 */

// ============================================================================
// SHARED MODULES - Core foundation types
// ============================================================================

// Re-export all enums and validation functions
export {
  MessageType,
  AgentStatus,
  WebSocketMessageType,
  isValidMessageType,
  isValidAgentStatus,
  isValidWebSocketMessageType,
  getMessageTypeValues,
  getAgentStatusValues,
  getWebSocketMessageTypeValues,
  getEnumKey,
  ENUM_REGISTRY
} from './shared/enums';

// Re-export base interfaces and utility types
export {
  MessageRole,
  MessageStatus,
  BaseEntity,
  BaseTimestampEntity,
  BaseMetadata,
  BaseMessage,
  BaseWebSocketPayload,
  MessageAttachment,
  MessageReaction,
  MessageMetadata,
  User,
  AuthEndpoints,
  AuthConfigResponse,
  ID,
  Timestamp,
  OptionalFields,
  RequiredFields,
  Nullable,
  Optional,
  OperationStatus,
  ConnectionStatus,
  TYPE_REGISTRY,
  createBaseMessage,
  createMessageAttachment,
  createMessageReaction,
  createBaseEntity,
  createTimestampEntity,
  createBaseMetadata,
  isValidUser,
  hasRequiredMessageFields,
  isValidEntity,
  getTypeFromRegistry
} from './shared/base';

// ============================================================================
// DOMAIN MODULES - Specialized type collections
// ============================================================================

// Authentication domain
export {
  DevUser,
  GoogleUser,
  Token,
  TokenPayload,
  DevLoginRequest,
  UserBase,
  UserCreate,
  UserCreateOAuth,
  UserUpdate,
  isActiveUser,
  isAdminUser,
  hasValidToken,
  createGuestUser,
  sanitizeUserForClient
} from './domains/auth';

// Message domain
export {
  Message,
  ChatMessage,
  ChatMessageType,
  BaseChatMessage,
  createMessage,
  createChatMessage
} from './domains/messages';

// Thread domain
export {
  ThreadMetadata,
  Thread,
  ThreadState,
  getThreadTitle,
  getThreadStatus,
  isThreadActive,
  createThreadWithTitle,
  createThread,
  isValidThread,
  sortThreadsByDate,
  filterActiveThreads,
  createThreadState,
  setActiveThread
} from './domains/threads';

// WebSocket domain
export {
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
  WebSocketMessage,
  AuthMessage,
  PingMessage,
  PongMessage,
  isWebSocketMessage,
  isAgentStartedMessage,
  isAgentCompletedMessage,
  isSubAgentUpdateMessage,
  isToolCallMessage,
  isErrorMessage,
  isUserMessagePayload,
  isAgentUpdateMessage,
  createWebSocketError,
  createWebSocketMessage,
  MessageTypeLiteral,
  WebSocketPayload
} from './domains/websocket';

// Agent domain
export {
  ToolResultData,
  AgentMetadata,
  AgentResult,
  MessageData,
  ThreadHistoryResponse,
  AgentState,
  SubAgentLifecycle,
  SubAgentState,
  SubAgentStatus,
  isValidAgentState,
  isAgentActive,
  isAgentCompleted,
  hasAgentError,
  getAgentDuration,
  isValidSubAgentLifecycle,
  createAgentMetadata,
  updateAgentMetadata
} from './domains/agents';

// Tools domain
export {
  ToolStatus,
  ToolInput,
  ToolResult,
  ReferenceItem,
  ToolCompleted,
  ToolStarted,
  isValidToolStatus,
  isToolComplete,
  isToolInProgress,
  isToolSuccessful,
  createToolInput,
  createToolResult,
  createToolCallPayload,
  createToolResultPayload,
  isToolCallPayload,
  isToolResultPayload
} from './domains/tools';

// ============================================================================
// COMPATIBILITY ALIASES - Maintain exact backward compatibility
// ============================================================================

// Export additional type aliases from base to maintain compatibility
export type RegisteredTypeName = keyof typeof TYPE_REGISTRY;

// ============================================================================
// DEFAULT EXPORT - Consolidated utilities for convenience
// ============================================================================

export default {
  // Core enums
  MessageType,
  AgentStatus,
  WebSocketMessageType,
  
  // Validation functions
  isValidMessageType,
  isValidAgentStatus,
  isValidWebSocketMessageType,
  
  // WebSocket utilities
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