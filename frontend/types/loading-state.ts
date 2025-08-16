/**
 * Loading State Types for MainChat Component
 * 
 * Provides strongly typed loading states to prevent race conditions
 * and improve state transition clarity in the chat interface.
 * 
 * @compliance type_safety.xml - Single source of truth for loading states
 * @compliance conventions.xml - Under 300 lines, strongly typed
 */

import { WebSocketStatus } from '../services/webSocketService';

/**
 * Comprehensive loading state enum covering all possible UI states
 * Prevents ambiguous state combinations and race conditions
 */
export enum ChatLoadingState {
  /** Initial application loading - no connection attempt yet */
  INITIALIZING = 'initializing',
  
  /** WebSocket connection in progress */
  CONNECTING = 'connecting',
  
  /** WebSocket connection failed or lost */
  CONNECTION_FAILED = 'connection_failed',
  
  /** Connected but no thread selected */
  READY = 'ready',
  
  /** Loading thread messages from server */
  LOADING_THREAD = 'loading_thread',
  
  /** Thread loaded successfully */
  THREAD_READY = 'thread_ready',
  
  /** Processing user request/agent running */
  PROCESSING = 'processing',
  
  /** Error state requiring user intervention */
  ERROR = 'error'
}

/**
 * WebSocket connection states for loading logic
 * Maps WebSocketStatus to simplified boolean checks
 */
export interface WebSocketConnectionState {
  readonly isConnected: boolean;
  readonly isConnecting: boolean;
  readonly isFailed: boolean;
  readonly status: WebSocketStatus;
}

/**
 * Thread loading states for clear state management
 */
export interface ThreadLoadingState {
  readonly isLoading: boolean;
  readonly hasActiveThread: boolean;
  readonly hasMessages: boolean;
  readonly threadId: string | null;
}

/**
 * Processing states for agent/request handling
 */
export interface ProcessingState {
  readonly isProcessing: boolean;
  readonly currentRunId: string | null;
  readonly agentName: string | null;
}

/**
 * Combined state interface for loading state determination
 * Provides all necessary context for state transitions
 */
export interface ChatStateContext {
  readonly webSocket: WebSocketConnectionState;
  readonly thread: ThreadLoadingState;
  readonly processing: ProcessingState;
  readonly isInitialized: boolean;
}

/**
 * Loading state result with display properties
 * Clear separation of state logic from UI concerns
 */
export interface LoadingStateResult {
  readonly state: ChatLoadingState;
  readonly shouldShowLoading: boolean;
  readonly shouldShowEmptyState: boolean;
  readonly shouldShowExamplePrompts: boolean;
  readonly loadingMessage: string;
}

/**
 * State transition validation result
 * Ensures valid state transitions and prevents invalid states
 */
export interface StateTransitionResult {
  readonly isValid: boolean;
  readonly newState: ChatLoadingState;
  readonly reason?: string;
}