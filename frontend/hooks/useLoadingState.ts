/**
 * useLoadingState Hook for MainChat Component
 * 
 * Provides clean loading state management with race condition prevention.
 * Encapsulates complex loading logic into simple, predictable state transitions.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed hook with clear interfaces
 */

import { useState, useEffect, useRef } from 'react';
import { useUnifiedChatStore } from '../store/unified-chat';
import { useWebSocket } from './useWebSocket';
import type { UnifiedChatState } from '../types/store-types';
import {
  ChatLoadingState,
  LoadingStateResult,
  ChatStateContext
} from '../types/loading-state';
import {
  createChatStateContext,
  determineLoadingState,
  createLoadingResult,
  validateStateTransition
} from '../utils/loading-state-machine';

/**
 * Loading state hook return interface
 */
export interface UseLoadingStateResult {
  readonly loadingState: ChatLoadingState;
  readonly shouldShowLoading: boolean;
  readonly shouldShowEmptyState: boolean;
  readonly shouldShowExamplePrompts: boolean;
  readonly loadingMessage: string;
  readonly isInitialized: boolean;
}

/**
 * Main loading state hook for MainChat component
 * Provides race-condition-free loading state management
 */
export const useLoadingState = (): UseLoadingStateResult => {
  const [isInitialized, setIsInitialized] = useState(false);
  const [currentState, setCurrentState] = useState<ChatLoadingState>(ChatLoadingState.INITIALIZING);
  const previousStateRef = useRef<ChatLoadingState>(ChatLoadingState.INITIALIZING);
  
  // Select individual properties to avoid creating new objects
  const activeThreadId = useUnifiedChatStore(state => state.activeThreadId);
  const isThreadLoading = useUnifiedChatStore(state => state.isThreadLoading);
  const messages = useUnifiedChatStore(state => state.messages);
  const isProcessing = useUnifiedChatStore(state => state.isProcessing);
  const currentRunId = useUnifiedChatStore(state => state.currentRunId);
  const agentName = useUnifiedChatStore(state => state.fastLayerData?.agentName || null);
  const { status: wsStatus } = useWebSocket();
  
  // Create store data object for context
  const storeData: ExtractedStoreData = {
    activeThreadId,
    isThreadLoading,
    messages,
    isProcessing,
    currentRunId,
    agentName
  };
  
  const context = createContextFromData(storeData, wsStatus, isInitialized);
  const newState = determineLoadingState(context);
  
  // Debug logging
  if (process.env.NODE_ENV === 'development') {
    console.log('[useLoadingState] Debug:', {
      wsStatus,
      isInitialized,
      activeThreadId,
      isThreadLoading,
      messageCount: messages.length,
      currentState,
      newState,
      context
    });
  }
  
  useStateTransition(currentState, newState, setCurrentState, previousStateRef);
  useInitializationEffect(wsStatus, isInitialized, setIsInitialized);
  
  const result = createLoadingResult(currentState, context);
  return createHookResult(result, isInitialized);
};


/**
 * Store data extracted by selector
 */
interface ExtractedStoreData {
  activeThreadId: string | null;
  isThreadLoading: boolean;
  messages: any[];
  isProcessing: boolean;
  currentRunId: string | null;
  agentName: string | null;
}

/**
 * Creates chat state context from hook data
 */
const createContextFromData = (
  storeData: ExtractedStoreData,
  wsStatus: string,
  isInitialized: boolean
): ChatStateContext => {
  return createChatStateContext(
    wsStatus as any,
    storeData.activeThreadId,
    storeData.isThreadLoading,
    storeData.messages,
    storeData.isProcessing,
    storeData.currentRunId,
    storeData.agentName,
    isInitialized
  );
};

/**
 * Handles state transitions with validation
 */
const useStateTransition = (
  currentState: ChatLoadingState,
  newState: ChatLoadingState,
  setCurrentState: (state: ChatLoadingState) => void,
  previousStateRef: React.MutableRefObject<ChatLoadingState>
) => {
  useEffect(() => {
    if (currentState === newState) return;
    
    const transition = validateStateTransition(currentState, newState);
    if (transition.isValid) {
      previousStateRef.current = currentState;
      setCurrentState(newState);
    }
  }, [newState]); // Only depend on newState to avoid loops
};

/**
 * Handles initialization when WebSocket connects
 */
const useInitializationEffect = (
  wsStatus: string,
  isInitialized: boolean,
  setIsInitialized: (value: boolean) => void
) => {
  useEffect(() => {
    if (wsStatus === 'OPEN' && !isInitialized) {
      // Add delay to ensure store is ready
      const timer = setTimeout(() => {
        setIsInitialized(true);
      }, 100);
      
      return () => clearTimeout(timer);
    }
  }, [wsStatus, isInitialized, setIsInitialized]);
};

/**
 * Creates final hook result object
 */
const createHookResult = (
  result: LoadingStateResult,
  isInitialized: boolean
): UseLoadingStateResult => {
  return {
    loadingState: result.state,
    shouldShowLoading: result.shouldShowLoading,
    shouldShowEmptyState: result.shouldShowEmptyState,
    shouldShowExamplePrompts: result.shouldShowExamplePrompts,
    loadingMessage: result.loadingMessage,
    isInitialized
  };
};

/**
 * Debugging hook for loading state transitions
 * Only used in development mode
 */
export const useLoadingStateDebug = (state: ChatLoadingState) => {
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.debug('Loading state changed:', state);
    }
  }, [state]);
};