// Unified Chat UI/UX Types - Modular type system
// Version 5.0 - Clean modular architecture with focused responsibilities

// Import modular types
export * from './layer-types';
export * from './websocket-event-types';
export * from './component-props';
export * from './store-types';

// Re-export key types for convenience
export type {
  FastLayerData,
  MediumLayerData,
  SlowLayerData,
  LayerUpdateEvent
} from './layer-types';

export type {
  UnifiedWebSocketEvent,
  ChatMessage
} from './websocket-event-types';

export type {
  PersistentResponseCardProps,
  FastLayerProps,
  MediumLayerProps,
  SlowLayerProps,
  UnifiedChatConfig,
  DEFAULT_UNIFIED_CHAT_CONFIG
} from './component-props';

export type {
  UnifiedChatState,
  AgentExecution,
  WebSocketEventBuffer
} from './store-types';