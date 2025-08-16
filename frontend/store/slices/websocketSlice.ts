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
    
    // Buffer event for debugging
    const wsEvent: WSEvent = {
      type: event.type,
      payload: event.payload,
      timestamp: Date.now(),
      threadId: state.activeThreadId || undefined,
      runId: (event.payload as any)?.run_id,
      agentName: (event.payload as any)?.agent_id || (event.payload as any)?.agent_type
    };
    state.wsEventBuffer.push(wsEvent);
    
    // Debug logging to track layer updates
    logger.debug('WebSocket Event received', {
      component: 'UnifiedChatStore',
      action: 'websocket_event',
      metadata: {
        event_type: event.type,
        payload: event.payload,
        has_fast_layer: !!state.fastLayerData,
        has_medium_layer: !!state.mediumLayerData,
        has_slow_layer: !!state.slowLayerData
      }
    });
    
    // Route events to appropriate handlers
    switch (event.type) {
      case 'thread_loading':
        state.setThreadLoading(true);
        break;
        
      case 'agent_started':
        handleAgentStarted(event, state, set);
        break;
        
      case 'tool_executing':
        handleToolExecuting(event, state);
        break;
        
      case 'agent_thinking':
        handleAgentThinking(event, state);
        break;
        
      case 'partial_result':
        handlePartialResult(event, state);
        break;
        
      case 'agent_completed':
        handleAgentCompleted(event, state, set);
        break;
        
      case 'thread_renamed':
        handleThreadRenamed(event, state, set);
        break;
        
      case 'thread_loaded':
        handleThreadLoaded(event, state, set);
        break;
        
      case 'final_report':
        handleFinalReport(event, state, set);
        break;
        
      case 'error':
        handleError(event, state, set);
        break;
    }
  }
});