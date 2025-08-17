import type { StateCreator } from 'zustand';
import { logger } from '@/lib/logger';
import type { UnifiedWebSocketEvent } from '@/types/unified-chat';
import type { WSEvent } from '@/lib/circular-buffer';
import {
  handleAgentStarted,
  handleToolExecuting,
  handleAgentThinking,
  handlePartialResult,
  type WebSocketHandlerState
} from './websocketHandlers';
import {
  handleAgentCompleted,
  handleFinalReport,
  handleThreadRenamed,
  handleThreadLoaded,
  handleError
} from './websocketHandlersExtended';

export interface WebSocketSliceState {
  handleWebSocketEvent: (event: UnifiedWebSocketEvent) => void;
}

export const createWebSocketSlice: StateCreator<
  WebSocketHandlerState & WebSocketSliceState,
  [],
  [],
  WebSocketSliceState
> = (set, get) => ({
  handleWebSocketEvent: (event: UnifiedWebSocketEvent) => {
    const state = get();
    bufferWebSocketEvent(event, state);
    logWebSocketEvent(event, state);
    routeWebSocketEvent(event, state, set);
  }
});

// Helper functions for WebSocket event handling (≤8 lines each)
const bufferWebSocketEvent = (event: UnifiedWebSocketEvent, state: any): void => {
  const wsEvent: WSEvent = {
    type: event.type,
    payload: event.payload,
    timestamp: Date.now(),
    threadId: state.activeThreadId || undefined,
    runId: (event.payload as any)?.run_id,
    agentName: (event.payload as any)?.agent_id || (event.payload as any)?.agent_type
  };
  state.wsEventBuffer.push(wsEvent);
};

const logWebSocketEvent = (event: UnifiedWebSocketEvent, state: any): void => {
  logger.debug('WebSocket Event received', {
    component: 'UnifiedChatStore',
    action: 'websocket_event',
    metadata: createEventMetadata(event, state)
  });
};

const createEventMetadata = (event: UnifiedWebSocketEvent, state: any) => ({
  event_type: event.type,
  payload: event.payload,
  has_fast_layer: !!state.fastLayerData,
  has_medium_layer: !!state.mediumLayerData,
  has_slow_layer: !!state.slowLayerData
});

const routeWebSocketEvent = (event: UnifiedWebSocketEvent, state: any, set: any): void => {
  if (routeAgentEvents(event, state, set)) return;
  if (routeToolEvents(event, state, set)) return;
  if (routeThreadEvents(event, state, set)) return;
  routeSystemEvents(event, state, set);
};

const routeAgentEvents = (event: UnifiedWebSocketEvent, state: any, set: any): boolean => {
  switch (event.type) {
    case 'agent_started':
      handleAgentStarted(event, state, set);
      return true;
    case 'agent_thinking':
      handleAgentThinking(event, state);
      return true;
    case 'agent_completed':
      handleAgentCompleted(event, state, set);
      return true;
  }
  return false;
};

const routeToolEvents = (event: UnifiedWebSocketEvent, state: any, set: any): boolean => {
  switch (event.type) {
    case 'tool_executing':
      handleToolExecuting(event, state);
      return true;
  }
  return false;
};

const routeThreadEvents = (event: UnifiedWebSocketEvent, state: any, set: any): boolean => {
  switch (event.type) {
    case 'thread_loading':
      state.setThreadLoading(true);
      return true;
    case 'thread_renamed':
      handleThreadRenamed(event, state, set);
      return true;
    case 'thread_loaded':
      handleThreadLoaded(event, state, set);
      return true;
  }
  return false;
};

const routeSystemEvents = (event: UnifiedWebSocketEvent, state: any, set: any): void => {
  switch (event.type) {
    case 'partial_result':
      handlePartialResult(event, state);
      break;
    case 'final_report':
      handleFinalReport(event, state, set);
      break;
    case 'error':
      handleError(event, state, set);
      break;
  }
};