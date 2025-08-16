/**
 * useLoadingState Hook for MainChat Component
 * 
 * Provides clean loading state management with race condition prevention.
 * Encapsulates complex loading logic into simple, predictable state transitions.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed hook with clear interfaces
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useUnifiedChatStore } from '../store/unified-chat';
import { useWebSocket } from './useWebSocket';
import { shallow } from 'zustand/shallow';
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
  
  const storeData = extractStoreData();
  const { status: wsStatus } = useWebSocket();
  
  const context = createContextFromData(storeData, wsStatus, isInitialized);
  const newState = determineLoadingState(context);
  
  useStateTransition(currentState, newState, setCurrentState, previousStateRef);
  useInitializationEffect(wsStatus, isInitialized, setIsInitialized);
  
  const result = createLoadingResult(currentState, context);
  return createHookResult(result, isInitialized);
};

/**
 * Selector for extracting store data with stable reference
 */
const storeSelector = (state: any) => ({
  activeThreadId: state.activeThreadId,
  isThreadLoading: state.isThreadLoading,
  messages: state.messages,
  isProcessing: state.isProcessing,
  currentRunId: state.currentRunId,
  agentName: state.fastLayerData?.agentName || null
});

/**
 * Extracts necessary data from unified store
 */
const extractStoreData = () => {
  return useUnifiedChatStore(storeSelector, shallow);
};

/**
 * Creates chat state context from hook data
 */
const createContextFromData = (
  storeData: any,
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
  const handleTransition = useCallback(() => {
    if (currentState === newState) return;
    
    const transition = validateStateTransition(currentState, newState);
    if (transition.isValid) {
      previousStateRef.current = currentState;
      setCurrentState(newState);
    }
  }, [currentState, newState, setCurrentState, previousStateRef]);
  
  useEffect(() => {
    handleTransition();
  }, [handleTransition]);
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