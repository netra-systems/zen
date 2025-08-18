/**
 * WebSocket Context Type Definitions
 * Single source of truth for WebSocket provider context types
 * Shared between providers and mocks for consistency
 */

import { WebSocketStatus } from '../services/webSocketService';
import { WebSocketMessage } from './registry';
import { OptimisticMessage, ReconciliationStats } from '../services/reconciliation';

/**
 * Context type for WebSocket provider state and actions
 * Used by both real provider and test mocks
 */
export interface WebSocketContextType {
  /** Current WebSocket connection status */
  status: WebSocketStatus;
  /** Array of received WebSocket messages */
  messages: WebSocketMessage[];
  /** Function to send a message through WebSocket */
  sendMessage: (message: WebSocketMessage) => void;
  /** Function to send optimistic message with automatic reconciliation */
  sendOptimisticMessage: (content: string, type?: 'user' | 'assistant') => OptimisticMessage;
  /** Current reconciliation statistics */
  reconciliationStats: ReconciliationStats;
}

/**
 * Props for WebSocket provider components
 */
export interface WebSocketProviderProps {
  children: React.ReactNode;
}

/**
 * Props for mock WebSocket provider with optional value override
 */
export interface MockWebSocketProviderProps extends WebSocketProviderProps {
  /** Optional partial context value override for testing */
  value?: Partial<WebSocketContextType>;
}