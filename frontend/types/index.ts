// frontend/types/index.ts

// Export backend auto-generated types (most types are here)
export * from './backend_schema_auto_generated';

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

// Only export from other files if they have unique types not in backend_schema_auto_generated
// Most types are already defined in backend_schema_auto_generated