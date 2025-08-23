// Core WebSocket event handler functions - Modular 25-line functions
// Core routing and logging functions

import { logger } from '@/lib/logger';
import type { UnifiedWebSocketEvent } from '@/types/websocket-event-types';
import type { ChatMessage } from '@/types/unified';
import type { UnifiedChatState } from '@/types/store-types';

/**
 * Logs WebSocket event for debugging
 */
export const logWebSocketEvent = (event: UnifiedWebSocketEvent, state: UnifiedChatState): void => {
  logger.debug('WebSocket Event received', {
    component: 'UnifiedChatStore',
    action: 'websocket_event',
    metadata: { event_type: event.type, payload: event.payload }
  });
};

/**
 * Buffers WebSocket event for replay and debugging
 */
export const bufferWebSocketEvent = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  const wsEvent = createWSEvent(event, state);
  state.wsEventBuffer.push(wsEvent);
  set({ wsEventBufferVersion: state.wsEventBufferVersion + 1 });
};

/**
 * Creates WebSocket event record for buffering
 */
export const createWSEvent = (event: UnifiedWebSocketEvent, state: UnifiedChatState) => ({
  type: event.type,
  payload: event.payload,
  timestamp: Date.now(),
  threadId: state.activeThreadId || undefined,
  runId: (event.payload as any)?.run_id,
  agentName: (event.payload as any)?.agent_id || (event.payload as any)?.agent_type
});

/**
 * Routes event to appropriate handler function
 */
export const routeEventToHandler = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState,
  handlers: Record<string, Function>
): void => {
  const handler = handlers[event.type];
  if (handler) handler(event, state, set, get);
};

/**
 * Parses timestamp from string or number format
 */
export const parseTimestamp = (timestamp: string | number): number => {
  return typeof timestamp === 'string' ? Date.parse(timestamp) : timestamp;
};

/**
 * Main WebSocket event handler - routes all events
 */
export const handleWebSocketEvent = (
  event: UnifiedWebSocketEvent,
  state: UnifiedChatState,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState,
  handlers: Record<string, Function>
): void => {
  logWebSocketEvent(event, state);
  bufferWebSocketEvent(event, state, set);
  routeEventToHandler(event, state, set, get, handlers);
};