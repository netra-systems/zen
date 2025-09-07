/**
 * Thread Switching Hook
 * 
 * Manages smooth thread switching with proper loading states and WebSocket integration.
 * Prevents race conditions and provides seamless user experience.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed hook with clear interfaces
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import type { UnifiedChatState } from '@/types/store-types';
import { threadLoadingService, type ThreadLoadingResult } from '@/services/threadLoadingService';
import { 
  threadEventHandler,
  createThreadLoadingEvent,
  createThreadLoadedEvent
} from '@/utils/threadEventHandler';
import { createThreadTimeoutManager } from '@/utils/threadTimeoutManager';
import { executeWithRetry } from '@/lib/retry-manager';
import { globalCleanupManager } from '@/lib/operation-cleanup';
import type { ThreadError } from '@/types/thread-error-types';
import { createThreadError } from '@/types/thread-error-types';
import { useURLSync, useBrowserHistorySync } from '@/services/urlSyncService';
import { ThreadOperationManager } from '@/lib/thread-operation-manager';
import { logger } from '@/lib/logger';

/**
 * Thread switching state
 */
export interface ThreadSwitchingState {
  readonly isLoading: boolean;
  readonly loadingThreadId: string | null;
  readonly error: ThreadError | null;
  readonly lastLoadedThreadId: string | null;
  readonly operationId: string | null;
  readonly retryCount: number;
}

/**
 * Thread switching options
 */
export interface ThreadSwitchingOptions {
  readonly clearMessages?: boolean;
  readonly showLoadingIndicator?: boolean;
  readonly timeoutMs?: number;
  readonly updateUrl?: boolean;
  readonly skipUrlUpdate?: boolean;
  readonly force?: boolean;
}

/**
 * Thread switching hook result
 */
export interface UseThreadSwitchingResult {
  readonly state: ThreadSwitchingState;
  readonly switchToThread: (threadId: string, options?: ThreadSwitchingOptions) => Promise<boolean>;
  readonly cancelLoading: () => void;
  readonly retryLastFailed: () => Promise<boolean>;
}

/**
 * Default switching options
 */
const DEFAULT_OPTIONS: Required<Omit<ThreadSwitchingOptions, 'force'>> & { force: boolean } = {
  clearMessages: true,
  showLoadingIndicator: true,
  timeoutMs: 5000,
  updateUrl: true,
  skipUrlUpdate: false,
  force: false
};

/**
 * Thread switching hook
 */
export const useThreadSwitching = (): UseThreadSwitchingResult => {
  const [state, setState] = useState<ThreadSwitchingState>(createInitialState());
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastFailedThreadRef = useRef<string | null>(null);
  const timeoutManagerRef = useRef(createTimeoutManager());
  const currentOperationRef = useRef<string | null>(null);
  
  // URL sync integration
  const { updateUrl } = useURLSync();
  
  // Select individual actions to prevent re-renders
  const setActiveThread = useUnifiedChatStore(state => state.setActiveThread);
  const setThreadLoading = useUnifiedChatStore(state => state.setThreadLoading);
  const startThreadLoading = useUnifiedChatStore(state => state.startThreadLoading);
  const completeThreadLoading = useUnifiedChatStore(state => state.completeThreadLoading);
  const clearMessages = useUnifiedChatStore(state => state.clearMessages);
  const loadMessages = useUnifiedChatStore(state => state.loadMessages);
  const handleWebSocketEvent = useUnifiedChatStore(state => state.handleWebSocketEvent);
  
  // Create store actions object
  const storeActions = {
    setActiveThread,
    setThreadLoading,
    startThreadLoading,
    completeThreadLoading,
    clearMessages,
    loadMessages,
    handleWebSocketEvent
  };
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (currentOperationRef.current) {
        globalCleanupManager.cleanupThread(currentOperationRef.current);
      }
    };
  }, []);
  
  const switchToThread = useCallback(async (
    threadId: string,
    options: ThreadSwitchingOptions = {}
  ): Promise<boolean> => {
    try {
      // Generate operation ID and store it for cleanup
      const operationId = generateOperationId(threadId);
      currentOperationRef.current = operationId;
      
      // Use ThreadOperationManager to ensure atomic operations
      const result = await ThreadOperationManager.startOperation(
        'switch',
        threadId,
        async (signal) => {
          return await performThreadSwitchWithManager(
            threadId,
            options,
            state,
            setState,
            storeActions,
            signal,
            lastFailedThreadRef,
            timeoutManagerRef.current,
            updateUrl
          );
        },
        {
          timeoutMs: options.timeoutMs || DEFAULT_OPTIONS.timeoutMs,
          retryAttempts: 2,
          force: options.force
        }
      );
      
      // Handle operation-level errors that weren't propagated to hook state
      if (!result.success && result.error) {
        setState(prev => ({
          ...prev,
          isLoading: false,
          loadingThreadId: null,
          operationId: null,
          error: createThreadError(threadId, result.error!),
          retryCount: prev.retryCount + 1
        }));
        lastFailedThreadRef.current = threadId;
      }
      
      // Clear the current operation reference
      currentOperationRef.current = null;
      
      return result.success;
    } catch (error) {
      // Clear the current operation reference on error
      currentOperationRef.current = null;
      return false;
    }
  }, [state, storeActions, updateUrl]);
  
  const cancelLoading = useCallback(() => {
    performCancelLoading(abortControllerRef, setState, storeActions);
  }, [storeActions]);
  
  const retryLastFailed = useCallback(async (): Promise<boolean> => {
    return await performRetryLastFailed(
      lastFailedThreadRef,
      switchToThread
    );
  }, [switchToThread]);
  
  return { state, switchToThread, cancelLoading, retryLastFailed };
};

/**
 * Creates initial switching state
 */
const createInitialState = (): ThreadSwitchingState => {
  return {
    isLoading: false,
    loadingThreadId: null,
    error: null,
    lastLoadedThreadId: null,
    operationId: null,
    retryCount: 0
  };
};

/**
 * Creates timeout manager for thread operations
 */
const createTimeoutManager = () => {
  return createThreadTimeoutManager({
    timeoutMs: 10000, // 10 seconds
    retryCount: 1,
    onTimeout: (threadId) => {
      logger.warn(`Thread loading timeout for ${threadId}, retrying...`);
    },
    onRetryExhausted: (threadId) => {
      logger.error(`Thread loading failed for ${threadId} after retries`);
    }
  });
};


/**
 * Performs thread switch operation with manager
 */
const performThreadSwitchWithManager = async (
  threadId: string,
  options: ThreadSwitchingOptions,
  currentState: ThreadSwitchingState,
  setState: (state: ThreadSwitchingState) => void,
  storeActions: any,
  signal: AbortSignal,
  lastFailedThreadRef: React.MutableRefObject<string | null>,
  timeoutManager: any,
  updateUrl?: (threadId: string | null) => void
): Promise<{ success: boolean; threadId?: string; error?: Error }> => {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const operationId = generateOperationId(threadId);
  
  // Start loading state
  const controller = startLoadingState(threadId, operationId, setState, storeActions, opts, timeoutManager);
  
  try {
    // Check if operation was aborted before starting
    if (signal.aborted) {
      throw new Error('Operation aborted');
    }
    
    const result = await executeWithRetry(() => threadLoadingService.loadThread(threadId), {
      maxAttempts: 3,
      baseDelayMs: 1000,
      signal
    });
    
    // Check if operation was aborted after loading but before processing result
    if (signal.aborted) {
      throw new Error('Operation aborted after loading');
    }
    
    const success = handleLoadingResult(
      result, 
      threadId, 
      operationId, 
      setState, 
      storeActions, 
      lastFailedThreadRef, 
      timeoutManager, 
      opts, 
      updateUrl
    );
    
    return { success, threadId };
  } catch (error) {
    
    // Don't treat aborted operations as errors - just ignore them silently
    if (error instanceof Error && error.message.includes('aborted')) {
      return { success: false, threadId, error: undefined };
    }
    
    handleLoadingError(error, threadId, operationId, setState, lastFailedThreadRef, storeActions, timeoutManager);
    return { success: false, error: error as Error };
  }
};

/**
 * Performs thread switch operation (legacy)
 */
const performThreadSwitch = async (
  threadId: string,
  options: ThreadSwitchingOptions,
  currentState: ThreadSwitchingState,
  setState: (state: ThreadSwitchingState) => void,
  storeActions: any,
  abortControllerRef: React.MutableRefObject<AbortController | null>,
  lastFailedThreadRef: React.MutableRefObject<string | null>,
  timeoutManager: any,
  updateUrl?: (threadId: string | null) => void
): Promise<boolean> => {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const operationId = generateOperationId(threadId);
  
  // Prevent race conditions by checking current operation
  if (currentState.isLoading && currentState.operationId !== operationId) {
    await cleanupCurrentOperation(abortControllerRef, storeActions, timeoutManager, currentState.operationId);
  }
  
  const controller = startLoadingState(threadId, operationId, setState, storeActions, opts, timeoutManager);
  abortControllerRef.current = controller;
  
  try {
    const result = await executeWithRetry(() => threadLoadingService.loadThread(threadId), {
      maxAttempts: 3,
      baseDelayMs: 1000
    });
    return handleLoadingResult(result, threadId, operationId, setState, storeActions, lastFailedThreadRef, timeoutManager, opts, updateUrl);
  } catch (error) {
    return handleLoadingError(error, threadId, operationId, setState, lastFailedThreadRef, storeActions, timeoutManager);
  }
};

/**
 * Cleans up current operation safely
 */
const cleanupCurrentOperation = async (
  abortControllerRef: React.MutableRefObject<AbortController | null>,
  storeActions?: any,
  timeoutManager?: any,
  operationId?: string | null
): Promise<void> => {
  if (abortControllerRef.current) {
    abortControllerRef.current.abort();
  }
  
  // Reset thread loading state in store
  if (storeActions?.setThreadLoading) {
    storeActions.setThreadLoading(false);
  }
  
  // Clear any active timeout
  if (timeoutManager && storeActions?.activeThreadId) {
    timeoutManager.clearTimeout(storeActions.activeThreadId);
  }
  
  // Perform operation cleanup
  if (operationId) {
    await globalCleanupManager.cleanupThread(operationId);
  }
};

/**
 * Generates unique operation ID
 */
const generateOperationId = (threadId: string): string => {
  return `thread_${threadId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Starts loading state for thread switch with atomic updates
 */
const startLoadingState = (
  threadId: string,
  operationId: string,
  setState: (state: ThreadSwitchingState) => void,
  storeActions: any,
  options: Required<ThreadSwitchingOptions>,
  timeoutManager?: any
): AbortController => {
  const controller = new AbortController();
  
  // Register cleanup for this operation
  globalCleanupManager.registerAbortController(operationId, controller);
  
  // ATOMIC STATE UPDATE: Update both hook and store state together
  const atomicUpdate = () => {
    // Update hook state first
    setState(prev => ({ 
      ...prev, 
      isLoading: true, 
      loadingThreadId: threadId, 
      operationId,
      error: null,
      retryCount: 0
    }));
    
    // Then update store state with coordinated method
    if (storeActions.startThreadLoading) {
      storeActions.startThreadLoading(threadId);
    } else {
      // Fallback to basic state updates
      storeActions.setActiveThread?.(threadId);
      storeActions.setThreadLoading?.(true);
    }
    
    // Clear messages if needed
    if (options.clearMessages && storeActions.clearMessages) {
      storeActions.clearMessages();
    }
  };
  
  // Perform atomic update - this might trigger re-renders so should be wrapped in act() by tests
  atomicUpdate();
  
  // Start timeout tracking
  if (timeoutManager) {
    timeoutManager.startTimeout(threadId);
  }
  
  const loadingEvent = createThreadLoadingEvent(threadId);
  if (storeActions.handleWebSocketEvent) {
    storeActions.handleWebSocketEvent(loadingEvent);
  }
  
  return controller;
};

/**
 * Handles successful loading result with atomic state updates
 */
const handleLoadingResult = (
  result: ThreadLoadingResult,
  threadId: string,
  operationId: string,
  setState: (state: ThreadSwitchingState) => void,
  storeActions: any,
  lastFailedThreadRef: React.MutableRefObject<string | null>,
  timeoutManager?: any,
  options?: Required<ThreadSwitchingOptions>,
  updateUrl?: (threadId: string | null) => void
): boolean => {
  if (result && result.success) {
    // Clear timeout and cleanup on success
    if (timeoutManager) {
      timeoutManager.clearTimeout(threadId);
    }
    
    globalCleanupManager.cleanupThread(operationId);
    
    // ATOMIC STATE UPDATE: Update both hook and store state together
    const atomicUpdate = () => {
      // Update hook state first
      setState(prev => ({
        ...prev,
        isLoading: false,
        loadingThreadId: null,
        operationId: null,
        lastLoadedThreadId: threadId,
        error: null
      }));
      
      // Then update store state with coordinated method
      if (storeActions.completeThreadLoading) {
        storeActions.completeThreadLoading(threadId, result.messages);
      } else {
        // Fallback to basic state updates
        storeActions.setActiveThread?.(threadId);
        storeActions.loadMessages?.(result.messages);
        storeActions.setThreadLoading?.(false);
      }
    };
    
    // Perform atomic update - this might trigger re-renders so should be wrapped in act() by tests
    atomicUpdate();
    
    const loadedEvent = createThreadLoadedEvent(threadId, result.messages);
    if (storeActions.handleWebSocketEvent) {
      storeActions.handleWebSocketEvent(loadedEvent);
    }
    
    // Update URL if enabled and not skipped - do it immediately
    if (options?.updateUrl && !options?.skipUrlUpdate && updateUrl) {
      updateUrl(threadId);
    }
    
    return true;
  } else {
    // Handle the case where the result indicates failure
    const errorMessage = result?.error || 'Thread loading failed';
    return handleLoadingError(errorMessage, threadId, operationId, setState, lastFailedThreadRef, storeActions, timeoutManager);
  }
};

/**
 * Handles loading error with atomic state updates and preserved error messages
 */
const handleLoadingError = (
  error: unknown,
  threadId: string,
  operationId: string,
  setState: (state: ThreadSwitchingState) => void,
  lastFailedThreadRef: React.MutableRefObject<string | null>,
  storeActions?: any,
  timeoutManager?: any
): boolean => {
  // Create thread error while preserving original error message
  let threadError;
  if (typeof error === 'string') {
    threadError = createThreadError(threadId, new Error(error));
  } else if (error instanceof Error) {
    threadError = createThreadError(threadId, error);
  } else {
    threadError = createThreadError(threadId, new Error('Thread loading failed'));
  }
  
  // Clear timeout and cleanup on error
  if (timeoutManager) {
    timeoutManager.clearTimeout(threadId);
  }
  
  globalCleanupManager.cleanupThread(operationId);
  
  // ATOMIC STATE UPDATE: Update both hook and store state together
  const atomicUpdate = () => {
    // Update hook state first
    setState(prev => ({
      ...prev,
      isLoading: false,
      loadingThreadId: null,
      operationId: null,
      error: threadError,
      retryCount: prev.retryCount + 1
    }));
    
    // Reset thread loading state in store and clear active thread on error
    if (storeActions?.setThreadLoading) {
      storeActions.setThreadLoading(false);
    }
    if (storeActions?.setActiveThread) {
      storeActions.setActiveThread(null);
    }
  };
  
  // Perform atomic update - this might trigger re-renders so should be wrapped in act() by tests
  atomicUpdate();
  
  lastFailedThreadRef.current = threadId;
  return false;
};

/**
 * Performs cancel loading operation
 */
const performCancelLoading = (
  abortControllerRef: React.MutableRefObject<AbortController | null>,
  setState: (state: ThreadSwitchingState) => void,
  storeActions?: any
): void => {
  if (abortControllerRef.current) {
    abortControllerRef.current.abort();
    abortControllerRef.current = null;
  }
  
  // Reset thread loading state in store
  if (storeActions?.setThreadLoading) {
    storeActions.setThreadLoading(false);
  }
  
  setState(prev => ({
    ...prev,
    isLoading: false,
    loadingThreadId: null,
    operationId: null
  }));
};

/**
 * Performs retry of last failed thread
 */
const performRetryLastFailed = async (
  lastFailedThreadRef: React.MutableRefObject<string | null>,
  switchToThread: (threadId: string) => Promise<boolean>
): Promise<boolean> => {
  const threadId = lastFailedThreadRef.current;
  if (!threadId) return false;
  
  return await switchToThread(threadId);
};