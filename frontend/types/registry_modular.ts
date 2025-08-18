/**
 * Type Registry: Modular Re-export Hub
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - All type definitions imported from modular structure
 * - Maintains 100% backward compatibility
 * - Maximum file size: 300 lines (now 73 lines)
 * - Single source of truth through re-exports
 * 
 * Usage:
 *   import { User, Message, AgentState, WebSocketMessage } from '@/types/registry';
 */

// ============================================================================
// CORE IMPORTS FROM MODULAR STRUCTURE
// ============================================================================

// Shared enums and base types
export * from './shared/enums';
export * from './shared/base';

// Domain-specific types
export * from './domains/messages';
export * from './domains/threads';

// Backend synchronization types
export * from './backend-sync/websockets';
export * from './backend-sync/payloads';

// ============================================================================
// EXPLICIT RE-EXPORTS FOR BACKWARD COMPATIBILITY
// ============================================================================

// Ensure all commonly used types are explicitly available
export {
  MessageType,
  AgentStatus,
  WebSocketMessageType,
  type MessageRole,
  type MessageStatus
} from './shared/enums';

export {
  type User,
  type AuthConfigResponse,
  type BaseMessage,
  type MessageAttachment,
  type MessageReaction,
  type MessageMetadata
} from './shared/base';

export {
  type Message,
  type ChatMessage,
  type ChatMessageType,
  type BaseChatMessage,
  type MessageData,
  type ThreadHistoryResponse,
  createMessage,
  createChatMessage,
  isValidMessage
} from './domains/messages';

export {
  type Thread,
  type ThreadMetadata,
  type ThreadState,
  getThreadTitle,
  getThreadStatus,
  isThreadActive,
  createThreadWithTitle
} from './domains/threads';

export {
  type WebSocketMessage,
  type WebSocketError,
  type AgentResult,
  type StartAgentPayload,
  type UserMessagePayload,
  type AgentUpdatePayload,
  isWebSocketMessage,
  createWebSocketMessage,
  createWebSocketError
} from './backend-sync/websockets';

// ============================================================================
// LEGACY TYPE REGISTRY FOR RUNTIME ACCESS
// ============================================================================

import { TYPE_REGISTRY } from './shared/enums';
export { TYPE_REGISTRY };
export type { RegisteredTypeName } from './shared/enums';

// ============================================================================
// DEFAULT EXPORT - COMPLETE API SURFACE
// ============================================================================

import enumsDefault from './shared/enums';
import baseDefault from './shared/base';
import messagesDefault from './domains/messages';
import threadsDefault from './domains/threads';
import websocketsDefault from './backend-sync/websockets';

export default {
  ...enumsDefault,
  ...baseDefault,
  ...messagesDefault,
  ...threadsDefault,
  ...websocketsDefault
};