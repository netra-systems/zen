// WebSocket event types for unified chat system
// Comprehensive event definitions for real-time communication

// ============================================
// Error Handling Events
// ============================================

export interface ErrorEvent {
  type: 'error';
  payload: {
    error_message: string;
    error_code: string;
    agent_id?: string;
    agent_type?: string;
    recoverable: boolean;
  };
}

export interface AgentErrorEvent {
  type: 'agent_error';
  payload: {
    agent_id?: string;
    agent_type?: string;
    error_message: string;
    error_code?: string;
    recoverable?: boolean;
    timestamp: number;
  };
}

// ============================================
// Thread Management Events
// ============================================

export interface ThreadCreatedEvent {
  type: 'thread_created';
  payload: {
    thread_id: string;
    user_id: string;
    created_at: number;
  };
}

export interface ThreadLoadingEvent {
  type: 'thread_loading';
  payload: {
    thread_id: string;
  };
}

export interface ThreadLoadedEvent {
  type: 'thread_loaded';
  payload: {
    thread_id: string;
    messages: ChatMessage[];
    metadata: Record<string, unknown>;
  };
}

export interface ThreadRenamedEvent {
  type: 'thread_renamed';
  payload: {
    thread_id: string;
    new_title: string;
  };
}

export interface ThreadHistoryEvent {
  type: 'thread_history';
  payload: {
    thread_id: string;
    messages: ChatMessage[];
    metadata?: Record<string, unknown>;
  };
}

export interface ThreadUpdatedEvent {
  type: 'thread_updated';
  payload: {
    thread_id: string;
    updates: Record<string, unknown>;
    timestamp: number;
  };
}

export interface ThreadDeletedEvent {
  type: 'thread_deleted';
  payload: {
    thread_id: string;
    timestamp: number;
  };
}

export interface ThreadSwitchedEvent {
  type: 'thread_switched';
  payload: {
    from_thread_id?: string;
    to_thread_id: string;
    timestamp: number;
  };
}

// ============================================
// Tool Events
// ============================================

export interface ToolCallEvent {
  type: 'tool_call';
  payload: {
    tool_name: string;
    agent_id?: string;
    agent_type?: string;
    args?: Record<string, any>;
    timestamp: number;
  };
}

export interface ToolCompletedEvent {
  type: 'tool_completed' | 'tool_result';
  payload: {
    tool_name: string;
    name?: string;
    result?: any;
    agent_id?: string;
    agent_type?: string;
    timestamp: number;
  };
}

export interface ToolStartedEvent {
  type: 'tool_started';
  payload: {
    tool_name: string;
    agent_id?: string;
    agent_type?: string;
    args?: Record<string, any>;
    timestamp: number;
  };
}

// ============================================
// Streaming Events
// ============================================

export interface StreamChunkEvent {
  type: 'stream_chunk';
  payload: {
    chunk: string;
    content?: string;
    agent_id?: string;
    agent_type?: string;
    done?: boolean;
    is_complete?: boolean;
  };
}

export interface StreamCompleteEvent {
  type: 'stream_complete';
  payload: {
    agent_id?: string;
    agent_type?: string;
    total_chunks?: number;
    final_content?: string;
    timestamp: number;
  };
}

// ============================================
// Agent Events
// ============================================

export interface AgentUpdateEvent {
  type: 'agent_update' | 'sub_agent_update';
  payload: {
    agent_id?: string;
    agent_type?: string;
    sub_agent_name?: string;
    status?: string;
    state?: Record<string, any>;
    timestamp: number;
  };
}

export interface AgentStoppedEvent {
  type: 'agent_stopped';
  payload: {
    agent_id?: string;
    agent_type?: string;
    reason?: string;
    timestamp: number;
  };
}

export interface AgentLogEvent {
  type: 'agent_log';
  payload: {
    agent_id?: string;
    agent_type?: string;
    sub_agent_name?: string;
    level: 'debug' | 'info' | 'warn' | 'error';
    message: string;
    timestamp: number;
  };
}

export interface SubAgentStartedEvent {
  type: 'subagent_started';
  payload: {
    sub_agent_name: string;
    agent_id?: string;
    agent_type?: string;
    timestamp: number;
  };
}

export interface SubAgentCompletedEvent {
  type: 'subagent_completed';
  payload: {
    sub_agent_name: string;
    agent_id?: string;
    agent_type?: string;
    duration_ms?: number;
    result?: any;
    timestamp: number;
  };
}

// ============================================
// Run and Step Events
// ============================================

export interface RunStartedEvent {
  type: 'agent_started';
  payload: {
    run_id: string;
    thread_id: string;
    assistant_id: string;
    model: string;
  };
}

export interface StepCreatedEvent {
  type: 'step_created';
  payload: {
    step_id: string;
    run_id: string;
    type: 'tool_call' | 'message' | 'function';
    details: Record<string, unknown>;
  };
}

// ============================================
// Connection Events
// ============================================

export interface ConnectionEstablishedEvent {
  type: 'connection_established';
  payload: {
    connection_id?: string;
    timestamp: number;
  };
}

export interface MessageReceivedEvent {
  type: 'message_received';
  payload: {
    message_id: string;
    timestamp: number;
  };
}

// ============================================
// MCP Events
// ============================================

export interface MCPServerConnectedEvent {
  type: 'mcp_server_connected';
  payload: {
    server_name: string;
    transport: string;
    capabilities: Record<string, any>;
    timestamp: number;
  };
}

export interface MCPServerDisconnectedEvent {
  type: 'mcp_server_disconnected';
  payload: {
    server_name: string;
    reason?: string;
    timestamp: number;
  };
}

export interface MCPToolStartedEvent {
  type: 'mcp_tool_started';
  payload: {
    execution_id: string;
    tool_name: string;
    server_name: string;
    arguments: Record<string, any>;
    agent_id?: string;
    timestamp: number;
  };
}

export interface MCPToolCompletedEvent {
  type: 'mcp_tool_completed';
  payload: {
    execution_id: string;
    tool_name: string;
    server_name: string;
    result: Record<string, any>;
    execution_time_ms: number;
    agent_id?: string;
    timestamp: number;
  };
}

export interface MCPToolFailedEvent {
  type: 'mcp_tool_failed';
  payload: {
    execution_id: string;
    tool_name: string;
    server_name: string;
    error_message: string;
    error_code?: string;
    agent_id?: string;
    timestamp: number;
  };
}

export interface MCPServerErrorEvent {
  type: 'mcp_server_error';
  payload: {
    server_name: string;
    error_message: string;
    error_code?: string;
    timestamp: number;
  };
}

// ============================================
// Supporting Types
// ============================================

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  threadId?: string;
  threadTitle?: string;
  metadata?: {
    runId?: string;
    agentName?: string;
    duration?: number;
    mcpExecutions?: Array<{
      execution_id: string;
      tool_name: string;
      server_name: string;
    }>;
  };
}

// ============================================
// Union Type
// ============================================

// Re-export layer events from layer-types module
export type { 
  AgentStartedEvent,
  ToolExecutingEvent,
  AgentThinkingEvent,
  PartialResultEvent,
  AgentCompletedEvent,
  FinalReportEvent
} from './layer-types';

export type UnifiedWebSocketEvent = 
  | AgentStartedEvent
  | AgentCompletedEvent
  | AgentStoppedEvent
  | AgentErrorEvent
  | AgentUpdateEvent
  | AgentThinkingEvent
  | AgentLogEvent
  | ToolExecutingEvent
  | ToolStartedEvent
  | ToolCallEvent
  | ToolCompletedEvent
  | SubAgentStartedEvent
  | SubAgentCompletedEvent
  | PartialResultEvent
  | StreamChunkEvent
  | StreamCompleteEvent
  | FinalReportEvent
  | ErrorEvent
  | ThreadCreatedEvent
  | ThreadLoadingEvent
  | ThreadLoadedEvent
  | ThreadRenamedEvent
  | ThreadHistoryEvent
  | ThreadUpdatedEvent
  | ThreadDeletedEvent
  | ThreadSwitchedEvent
  | RunStartedEvent
  | StepCreatedEvent
  | ConnectionEstablishedEvent
  | MessageReceivedEvent
  | MCPServerConnectedEvent
  | MCPServerDisconnectedEvent
  | MCPToolStartedEvent
  | MCPToolCompletedEvent
  | MCPToolFailedEvent
  | MCPServerErrorEvent;
