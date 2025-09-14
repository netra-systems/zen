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

// Re-export base interfaces and utility types - Only verified working exports
export {
  MessageRole,
  MessageStatus,
  TYPE_REGISTRY,
  createBaseEntity,
  createBaseMessage,
  createBaseMetadata,
  createMessageAttachment,
  createMessageReaction,
  createTimestampEntity,
  getTypeFromRegistry,
  hasRequiredMessageFields,
  isValidEntity,
  isValidUser
} from './shared/base';

// ============================================================================
// DOMAIN MODULES - Specialized type collections
// ============================================================================

// Authentication domain - Only verified working functions
export {
  createGuestUser,
  hasValidToken,
  isActiveUser,
  isAdminUser,
  sanitizeUserForClient
} from './domains/auth';

// Message domain - Only verified working functions
export {
  createChatMessage,
  createMessage
} from './domains/messages';

// Thread domain - Only verified working functions
// NOTE: createThreadState and setActiveThread moved to @shared/types/frontend_types
export {
  createThread,
  createThreadWithTitle,
  filterActiveThreads,
  filterThreadsByTag,
  getThreadStatus,
  getThreadTitle,
  hasMessages,
  hasMetadata,
  hasParticipants,
  hasTags,
  isBookmarked,
  isThreadActive,
  isValidThread,
  searchThreads,
  sortThreadsByDate
} from './domains/threads';

// Thread state management - use canonical source
export {
  createThreadState,
  updateThreadState
} from '@shared/types/frontend_types';

// Thread state types
export type {
  ThreadState,
  BaseThreadState,
  StoreThreadState
} from '@shared/types/frontend_types';

// WebSocket domain - Type-only exports for interfaces, runtime exports for functions
export type {
  // Payload interface types
  AgentCompletedPayload,
  AgentStartedPayload,
  AgentUpdatePayload,
  AuthMessage,
  CreateThreadPayload,
  DeleteThreadPayload,
  SwitchThreadPayload,
  StopAgentPayload,
  UserMessagePayload,
  StartAgentPayload,
  SubAgentUpdatePayload,
  ToolCallPayload,
  ToolResultPayload,
  StreamChunkPayload,
  StreamCompletePayload,
  ErrorPayload,
  WebSocketMessage,
  WebSocketError,
  PingMessage,
  PongMessage,
  // Base types
  BaseWebSocketPayload
} from './domains/websocket';

// WebSocket runtime functions
export {
  createWebSocketError,
  createWebSocketMessage,
  isAgentCompletedMessage,
  isAgentStartedMessage,
  isAgentUpdateMessage,
  isErrorMessage,
  isSubAgentUpdateMessage,
  isToolCallMessage,
  isUserMessagePayload,
  isWebSocketMessage
} from './domains/websocket';

// Agent domain - Only verified working functions
export {
  createAgentMetadata,
  getAgentDuration,
  hasAgentError,
  isAgentActive,
  isAgentCompleted,
  isValidAgentState,
  isValidSubAgentLifecycle,
  updateAgentMetadata
} from './domains/agents';

// Tools domain - Only verified working functions
export {
  createToolCallPayload,
  createToolInput,
  createToolResult,
  createToolResultPayload,
  isToolCallPayload,
  isToolComplete,
  isToolInProgress,
  isToolResultPayload,
  isToolSuccessful,
  isValidToolStatus
} from './domains/tools';

// ============================================================================
// ESSENTIAL TYPE RE-EXPORTS - Direct from verified sources
// ============================================================================

// Direct type imports for essential interfaces that components need
export type { 
  User,
  AuthEndpoints,
  AuthConfigResponse,
  BaseEntity,
  BaseTimestampEntity,
  BaseMetadata,
  BaseMessage,
  BaseWebSocketPayload,
  MessageAttachment,
  MessageReaction,
  MessageMetadata,
  ID,
  Timestamp,
  OptionalFields,
  RequiredFields,
  Nullable,
  Optional,
  OperationStatus,
  ConnectionStatus
} from './shared/base';

// Additional WebSocket types that need to be available as types
export type {
  AgentResult
} from './domains/websocket';

// ============================================================================
// COMPATIBILITY ALIASES - Maintain exact backward compatibility
// ============================================================================

// Export additional type aliases from base to maintain compatibility
export type RegisteredTypeName = keyof typeof TYPE_REGISTRY;

// ============================================================================
// NO DEFAULT EXPORT - Prevents module initialization issues
// All exports are available as named exports above
// ============================================================================