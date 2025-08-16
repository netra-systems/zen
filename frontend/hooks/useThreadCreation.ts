/**
 * Thread Creation Hook
 * 
 * Manages new thread creation with WebSocket integration and immediate UI feedback.
 * Provides seamless experience for creating and navigating to new threads.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed hook with clear interfaces
 */

import { useState, useCallback } from 'react';
import { ThreadService } from '@/services/threadService';
import { useThreadSwitching } from './useThreadSwitching';
import { createThreadCreatedEvent } from '@/utils/threadEventHandler';
import { useUnifiedChatStore } from '@/store/unified-chat';

/**
 * Thread creation state
 */
export interface ThreadCreationState {
  readonly isCreating: boolean;
  readonly error: string | null;
  readonly lastCreatedThreadId: string | null;
}

/**
 * Thread creation options
 */
export interface ThreadCreationOptions {
  readonly title?: string;
  readonly metadata?: Record<string, unknown>;
  readonly navigateImmediately?: boolean;
}

/**
 * Thread creation hook result
 */
export interface UseThreadCreationResult {
  readonly state: ThreadCreationState;
  readonly createThread: (options?: ThreadCreationOptions) => Promise<string | null>;
  readonly createAndNavigate: (options?: ThreadCreationOptions) => Promise<boolean>;
}

/**
 * Default creation options
 */
const DEFAULT_OPTIONS: Required<ThreadCreationOptions> = {
  title: 'New Conversation',
  metadata: {},
  navigateImmediately: true
};

/**
 * Thread creation hook
 */
export const useThreadCreation = (): UseThreadCreationResult => {
  const [state, setState] = useState<ThreadCreationState>(createInitialState());
  const { switchToThread } = useThreadSwitching();
  const { handleWebSocketEvent } = useUnifiedChatStore();
  
  const createThread = useCallback(async (
    options: ThreadCreationOptions = {}
  ): Promise<string | null> => {
    return await performThreadCreation(options, state, setState, handleWebSocketEvent);
  }, [state, handleWebSocketEvent]);
  
  const createAndNavigate = useCallback(async (
    options: ThreadCreationOptions = {}
  ): Promise<boolean> => {
    const threadId = await createThread(options);
    if (!threadId) return false;
    
    if (options.navigateImmediately !== false) {
      return await switchToThread(threadId);
    }
    
    return true;
  }, [createThread, switchToThread]);
  
  return { state, createThread, createAndNavigate };
};

/**
 * Creates initial creation state
 */
const createInitialState = (): ThreadCreationState => {
  return {
    isCreating: false,
    error: null,
    lastCreatedThreadId: null
  };
};

/**
 * Performs thread creation operation
 */
const performThreadCreation = async (
  options: ThreadCreationOptions,
  currentState: ThreadCreationState,
  setState: (state: ThreadCreationState) => void,
  handleWebSocketEvent: (event: any) => void
): Promise<string | null> => {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  
  setState(prev => ({ ...prev, isCreating: true, error: null }));
  
  try {
    const thread = await createThreadViaAPI(opts);
    const success = handleCreationSuccess(thread, setState, handleWebSocketEvent);
    
    return success ? thread.id : null;
  } catch (error) {
    handleCreationError(error, setState);
    return null;
  }
};

/**
 * Creates thread via backend API
 */
const createThreadViaAPI = async (options: Required<ThreadCreationOptions>) => {
  return await ThreadService.createThread(options.title, options.metadata);
};

/**
 * Handles successful thread creation
 */
const handleCreationSuccess = (
  thread: any,
  setState: (state: ThreadCreationState) => void,
  handleWebSocketEvent: (event: any) => void
): boolean => {
  try {
    const createdEvent = createThreadCreatedEvent(thread.id, thread.user_id || 'current');
    handleWebSocketEvent(createdEvent);
    
    setState(prev => ({
      ...prev,
      isCreating: false,
      lastCreatedThreadId: thread.id
    }));
    
    return true;
  } catch (error) {
    console.error('Failed to emit thread created event:', error);
    return false;
  }
};

/**
 * Handles thread creation error
 */
const handleCreationError = (
  error: unknown,
  setState: (state: ThreadCreationState) => void
): void => {
  const errorMessage = error instanceof Error ? 
    error.message : 'Failed to create thread';
  
  setState(prev => ({
    ...prev,
    isCreating: false,
    error: errorMessage
  }));
};