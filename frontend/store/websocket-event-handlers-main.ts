// Main WebSocket event handlers registry - Modular approach following CLAUDE.md
// Aggregates handlers from modular files to stay under 300-line limit

import { handleWebSocketEvent as coreHandler } from './websocket-event-handlers-core';
import { 
  handleAgentStarted,
  handleAgentCompleted,
  handleAgentThinking
} from './websocket-agent-handlers';
import { 
  handleToolExecutingEnhanced as handleToolExecuting,
  handleToolCompletedEnhanced as handleToolCompleted
} from './websocket-tool-handlers-enhanced';
import { 
  handlePartialResult,
  handleFinalReport
} from './websocket-content-handlers';
import {
  handleMCPServerConnected,
  handleMCPServerDisconnected,
  handleMCPToolStarted,
  handleMCPToolCompleted,
  handleMCPToolFailed,
  handleMCPServerError
} from './websocket-mcp-handlers';
import { handleError } from './websocket-error-handlers';
import type { 
  UnifiedWebSocketEvent
} from '@/types/websocket-event-types';
import type { UnifiedChatState } from '@/types/store-types';

/**
 * Event handler registry - maps event types to handler functions
 */
export const getEventHandlers = () => ({
  'agent_started': handleAgentStarted,
  'agent_completed': handleAgentCompleted,
  'agent_finished': handleAgentCompleted,
  'subagent_completed': handleAgentCompleted,
  'final_report': handleFinalReport,
  'tool_executing': handleToolExecuting,
  'tool_call': handleToolExecuting,
  'tool_completed': handleToolCompleted,
  'tool_result': handleToolCompleted,
  'agent_thinking': handleAgentThinking,
  'partial_result': handlePartialResult,
  'stream_chunk': handlePartialResult,
  // Error event handlers
  'error': handleError,
  // MCP event handlers
  'mcp_server_connected': handleMCPServerConnected,
  'mcp_server_disconnected': handleMCPServerDisconnected,
  'mcp_tool_started': handleMCPToolStarted,
  'mcp_tool_completed': handleMCPToolCompleted,
  'mcp_tool_failed': handleMCPToolFailed,
  'mcp_server_error': handleMCPServerError
});

/**
 * Main WebSocket event handler - entry point for all WebSocket events
 */
export const handleWebSocketEvent = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState
): void => {
  const handlers = getEventHandlers();
  coreHandler(event, state, set, get, handlers);
};