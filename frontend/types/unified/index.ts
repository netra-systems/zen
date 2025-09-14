/**
 * UNIFIED TYPES - Central Export Hub
 * 
 * This is the SINGLE SOURCE OF TRUTH for ALL frontend types.
 * All components, hooks, stores, and services should import from here.
 * 
 * CRITICAL RULES:
 * - Import from '@/types/unified' ONLY
 * - Never import scattered type files directly
 * - Each type exists ONCE and ONLY ONCE
 * - Report any duplicate type discoveries immediately
 * 
 * USAGE:
 * ```typescript
 * import { WebSocketMessage, Token, ToolCompleted, AgentStatus } from '@/types/unified';
 * ```
 */

// ============================================================================
// WEBSOCKET TYPES
// ============================================================================
export * from './websocket.types';

// ============================================================================
// AUTHENTICATION TYPES  
// ============================================================================
export * from './auth.types';

// ============================================================================
// TOOL TYPES
// ============================================================================
export * from './tool.types';

// ============================================================================
// METRICS TYPES
// ============================================================================
export * from './metrics.types';

// ============================================================================
// AGENT TYPES
// ============================================================================
export * from './agent.types';

// ============================================================================
// DOMAIN TYPES & UTILITIES  
// ============================================================================
// Import and re-export specific items to avoid conflicts
export type { 
  Message, 
  MessageRole, 
  ChatMessage,
  MessageMetadata,
  BaseMessage
} from '../domains/messages';

export type {
  Thread,
  ThreadMetadata
} from '../domains/threads';

// ThreadState moved to shared types for SSOT compliance
export type {
  ThreadState,
  BaseThreadState,
  StoreThreadState
} from '@shared/types/frontend_types';

// Export utility functions
export { 
  createMessage, 
  createChatMessage 
} from '../domains/messages';

export { 
  getThreadTitle, 
  createThread, 
  createThreadWithTitle,
  isThreadActive,
  getThreadStatus 
} from '../domains/threads';