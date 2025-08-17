// frontend/types/index.ts

// Export backend auto-generated types from modular files (split from original backend_schema_auto_generated)
export * from './backend_schema_base';
export * from './backend_schema_config';
export * from './backend_schema_auth';
export * from './backend_schema_tools';

// Export consolidated agent types (SINGLE SOURCE OF TRUTH)
export * from './agent-types';

// Re-export specific items from chat that don't conflict with backend types
export type { 
  Message as ChatMessage,
  SubAgentState,
  WebSocketMessage,
  ToolInput as ChatToolInput,
  ToolResult as ChatToolResult
} from './chat';

export { 
  SubAgentLifecycle,
  ToolStatus as ChatToolStatus
} from './chat';

// Export performance metrics unified types
export * from './performance-metrics';

// Only export from other files if they have unique types not in backend_schema_auto_generated
// Most types are already defined in backend_schema_auto_generated