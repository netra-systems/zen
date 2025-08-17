// frontend/types/index.ts

// Export backend auto-generated types from modular files (split from original backend_schema_auto_generated)
export * from './backend_schema_config';
export * from './backend_schema_auth';
export * from './backend_schema_tools';

// Export from backend_schema_base but exclude types that conflict with agent-types
export type {
  MessageType,
  SubAgentLifecycle,
  ToolStatus,
  AgentMessage,
  BaseMessage,
  AgentState,
  SubAgentState,
  SubAgentStatus,
  StreamEvent,
  RunComplete,
  Message,
  MessageToUser,
  UserMessage,
  StartAgentMessage,
  StartAgentPayload,
  Settings,
  AnalysisRequest,
  RequestModel,
  Workload,
  DataSource,
  TimeRange,
  AnalysisResult,
  WebSocketError,
  Response,
  UnifiedLogEntry,
  Performance,
  BaselineMetrics,
  EnrichedMetrics,
  CostComparison,
  EventMetadata,
  FinOps,
  TraceContext,
  ModelIdentifier
} from './backend_schema_base';

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

// Only export from other files if they have unique types not in backend_schema_auto_generated
// Most types are already defined in backend_schema_auto_generated