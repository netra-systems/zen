// WebSocket MCP event handlers - Modular MCP-specific handlers
// Follows established patterns for tool and agent handlers

import type { UnifiedChatState } from '@/types/store-types';
import type { 
  MCPServerConnectedEvent,
  MCPServerDisconnectedEvent,
  MCPToolStartedEvent,
  MCPToolCompletedEvent,
  MCPToolFailedEvent,
  MCPServerErrorEvent
} from '@/types/websocket-event-types';

// ============================================
// MCP Server Connection Handlers (8 lines max)
// ============================================

export const handleMCPServerConnected = (
  event: MCPServerConnectedEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const mcpState = state.mcpState || createInitialMCPState();
  updateServerConnection(mcpState, event.payload, 'CONNECTED');
  set({ mcpState });
};

export const handleMCPServerDisconnected = (
  event: MCPServerDisconnectedEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const mcpState = state.mcpState || createInitialMCPState();
  updateServerConnection(mcpState, event.payload, 'DISCONNECTED');
  set({ mcpState });
};

// ============================================
// MCP Tool Execution Handlers (8 lines max)
// ============================================

export const handleMCPToolStarted = (
  event: MCPToolStartedEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const mcpState = state.mcpState || createInitialMCPState();
  startToolExecution(mcpState, event.payload);
  set({ mcpState, isProcessing: true });
};

export const handleMCPToolCompleted = (
  event: MCPToolCompletedEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const mcpState = state.mcpState || createInitialMCPState();
  completeToolExecution(mcpState, event.payload, false);
  set({ mcpState });
};

export const handleMCPToolFailed = (
  event: MCPToolFailedEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const mcpState = state.mcpState || createInitialMCPState();
  completeToolExecution(mcpState, event.payload, true);
  set({ mcpState, connectionError: event.payload.error_message });
};

export const handleMCPServerError = (
  event: MCPServerErrorEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const mcpState = state.mcpState || createInitialMCPState();
  recordServerError(mcpState, event.payload);
  set({ mcpState, connectionError: event.payload.error_message });
};

// ============================================
// Helper Functions (8 lines max)
// ============================================

const createInitialMCPState = () => ({
  servers: new Map(),
  connections: new Map(),
  active_executions: new Map(),
  server_metrics: new Map(),
  is_loading: false,
  last_error: undefined
});

const updateServerConnection = (
  mcpState: any,
  payload: any,
  status: string
): void => {
  const serverInfo = mcpState.servers.get(payload.server_name) || {};
  serverInfo.status = status;
  serverInfo.last_health_check = new Date().toISOString();
  mcpState.servers.set(payload.server_name, serverInfo);
};

const startToolExecution = (mcpState: any, payload: any): void => {
  const execution = {
    id: payload.execution_id,
    tool_name: payload.tool_name,
    server_name: payload.server_name,
    status: 'RUNNING',
    arguments: payload.arguments,
    started_at: new Date().toISOString()
  };
  mcpState.active_executions.set(payload.execution_id, execution);
};

const completeToolExecution = (
  mcpState: any,
  payload: any,
  isError: boolean
): void => {
  const execution = mcpState.active_executions.get(payload.execution_id);
  if (!execution) return;
  
  execution.status = isError ? 'FAILED' : 'COMPLETED';
  execution.completed_at = new Date().toISOString();
  execution.duration_ms = payload.execution_time_ms;
  if (!isError) execution.result = payload.result;
};

const recordServerError = (mcpState: any, payload: any): void => {
  const metrics = mcpState.server_metrics.get(payload.server_name) || 
    createInitialServerMetrics(payload.server_name);
  metrics.error_count += 1;
  metrics.connection_status = 'ERROR';
  mcpState.server_metrics.set(payload.server_name, metrics);
};

const createInitialServerMetrics = (serverName: string) => ({
  server_name: serverName,
  connection_status: 'CONNECTED',
  tools_count: 0,
  resources_count: 0,
  error_count: 0,
  uptime_percentage: 100
});