/**
 * Loading State Machine for MainChat Component
 * 
 * Implements clean state transitions to prevent race conditions
 * and provide predictable loading state behavior.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed state machine
 */

import { WebSocketStatus } from '../services/webSocketService';
import {
  ChatLoadingState,
  WebSocketConnectionState,
  ThreadLoadingState,
  ProcessingState,
  ChatStateContext,
  LoadingStateResult,
  StateTransitionResult
} from '../types/loading-state';

/**
 * Creates WebSocket connection state from status
 */
export const createWebSocketState = (status: WebSocketStatus): WebSocketConnectionState => {
  const isConnected = status === 'OPEN';
  const isConnecting = status === 'CONNECTING';
  const isFailed = status === 'CLOSED' || status === 'CLOSING';
  return { isConnected, isConnecting, isFailed, status };
};

/**
 * Creates thread loading state from store values
 */
export const createThreadState = (
  threadId: string | null,
  isLoading: boolean,
  messages: any[]
): ThreadLoadingState => {
  const hasActiveThread = threadId !== null;
  const hasMessages = messages.length > 0;
  return { isLoading, hasActiveThread, hasMessages, threadId };
};

/**
 * Creates processing state from store values
 */
export const createProcessingState = (
  isProcessing: boolean,
  runId: string | null,
  agentName: string | null
): ProcessingState => {
  return { isProcessing, currentRunId: runId, agentName };
};

/**
 * Determines current loading state from context
 */
export const determineLoadingState = (context: ChatStateContext): ChatLoadingState => {
  if (!context.isInitialized) return ChatLoadingState.INITIALIZING;
  if (context.webSocket.isConnecting) return ChatLoadingState.CONNECTING;
  if (context.webSocket.isFailed) return ChatLoadingState.CONNECTION_FAILED;
  if (context.thread.isLoading) return ChatLoadingState.LOADING_THREAD;
  if (context.processing.isProcessing) return ChatLoadingState.PROCESSING;
  if (!context.thread.hasActiveThread) return ChatLoadingState.READY;
  // Thread is active and not loading - show thread ready state
  return ChatLoadingState.THREAD_READY;
};

/**
 * Validates state transition is legal
 */
export const validateStateTransition = (
  from: ChatLoadingState,
  to: ChatLoadingState
): StateTransitionResult => {
  const validTransitions = getValidTransitions(from);
  const isValid = validTransitions.includes(to);
  const reason = isValid ? undefined : `Invalid transition from ${from} to ${to}`;
  return { isValid, newState: to, reason };
};

/**
 * Gets valid transitions for current state
 */
const getValidTransitions = (state: ChatLoadingState): ChatLoadingState[] => {
  const transitions: Record<ChatLoadingState, ChatLoadingState[]> = {
    [ChatLoadingState.INITIALIZING]: [
      ChatLoadingState.CONNECTING, 
      ChatLoadingState.ERROR,
      ChatLoadingState.READY,  // Allow direct to READY if already connected
      ChatLoadingState.THREAD_READY  // Allow direct to THREAD_READY if thread exists
    ],
    [ChatLoadingState.CONNECTING]: [ChatLoadingState.READY, ChatLoadingState.CONNECTION_FAILED],
    [ChatLoadingState.CONNECTION_FAILED]: [ChatLoadingState.CONNECTING, ChatLoadingState.ERROR],
    [ChatLoadingState.READY]: [ChatLoadingState.LOADING_THREAD, ChatLoadingState.CONNECTION_FAILED],
    [ChatLoadingState.LOADING_THREAD]: [ChatLoadingState.THREAD_READY, ChatLoadingState.ERROR],
    [ChatLoadingState.THREAD_READY]: [ChatLoadingState.PROCESSING, ChatLoadingState.LOADING_THREAD],
    [ChatLoadingState.PROCESSING]: [ChatLoadingState.THREAD_READY, ChatLoadingState.ERROR],
    [ChatLoadingState.ERROR]: [ChatLoadingState.INITIALIZING, ChatLoadingState.CONNECTING]
  };
  return transitions[state] || [];
};

/**
 * Creates loading state result with UI flags
 */
export const createLoadingResult = (
  state: ChatLoadingState,
  context: ChatStateContext
): LoadingStateResult => {
  const shouldShowLoading = isLoadingState(state);
  const shouldShowEmptyState = state === ChatLoadingState.READY;
  const shouldShowExamplePrompts = isReadyForPrompts(state, context);
  const loadingMessage = getLoadingMessage(state, context);
  return { state, shouldShowLoading, shouldShowEmptyState, shouldShowExamplePrompts, loadingMessage };
};

/**
 * Checks if state requires loading indicator
 */
const isLoadingState = (state: ChatLoadingState): boolean => {
  const loadingStates = [
    ChatLoadingState.INITIALIZING,
    ChatLoadingState.CONNECTING,
    ChatLoadingState.LOADING_THREAD
  ];
  // THREAD_READY should NOT show loading - it should show content or example prompts
  return loadingStates.includes(state);
};

/**
 * Checks if ready to show example prompts
 */
const isReadyForPrompts = (state: ChatLoadingState, context: ChatStateContext): boolean => {
  const isThreadReadyState = state === ChatLoadingState.THREAD_READY;
  const hasNoMessages = !context.thread.hasMessages;
  const notProcessing = !context.processing.isProcessing;
  
  // Show example prompts ONLY in THREAD_READY state with no messages (not when no thread selected)
  return isThreadReadyState && hasNoMessages && notProcessing;
};

/**
 * Gets appropriate loading message for state
 */
const getLoadingMessage = (state: ChatLoadingState, context: ChatStateContext): string => {
  const messages: Record<ChatLoadingState, string> = {
    [ChatLoadingState.INITIALIZING]: 'Loading chat...',
    [ChatLoadingState.CONNECTING]: 'Connecting to chat service...',
    [ChatLoadingState.CONNECTION_FAILED]: 'Connection failed. Retrying...',
    [ChatLoadingState.LOADING_THREAD]: 'Loading thread messages...',
    [ChatLoadingState.READY]: 'Ready',
    [ChatLoadingState.THREAD_READY]: 'Thread ready',
    [ChatLoadingState.PROCESSING]: `Processing with ${context.processing.agentName || 'agent'}...`,
    [ChatLoadingState.ERROR]: 'An error occurred'
  };
  return messages[state];
};

/**
 * Combines all context creation into single function
 */
export const createChatStateContext = (
  wsStatus: WebSocketStatus,
  threadId: string | null,
  isThreadLoading: boolean,
  messages: any[],
  isProcessing: boolean,
  runId: string | null,
  agentName: string | null,
  isInitialized: boolean
): ChatStateContext => {
  const webSocket = createWebSocketState(wsStatus);
  const thread = createThreadState(threadId, isThreadLoading, messages);
  const processing = createProcessingState(isProcessing, runId, agentName);
  return { webSocket, thread, processing, isInitialized };
};