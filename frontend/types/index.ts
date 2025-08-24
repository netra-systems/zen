// frontend/types/index.ts

// Export backend types from canonical modular files
export * from './backend_schema_config';
export * from './backend_schema_auth';
export * from './backend_schema_tools';

// Export core backend schema types (AUTHORITATIVE SOURCE)
export * from './backend_schema_base';

// Export consolidated agent types (SINGLE SOURCE OF TRUTH)
export * from './agent-types';

// Re-export specific items from chat that don't conflict with backend types
export type { 
  Message as ChatMessage,
  ToolInput as ChatToolInput,
  ToolResult as ChatToolResult
} from './chat';

export { 
  ToolStatus as ChatToolStatus
} from './chat';

// Export performance metrics unified types
export * from './performance-metrics';

// Export domain types and utilities
export * from './domains/messages';
export * from './domains/threads';

// Export specific utility functions for backward compatibility
export { createMessage, Message, MessageRole } from './domains/messages';
export { getThreadTitle, createThread, Thread } from './domains/threads';

// Export from canonical sources following SSOT principle
// All types use single source of truth from backend-sync and domains