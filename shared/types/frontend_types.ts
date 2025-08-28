/**
 * Canonical frontend type definitions - Single Source of Truth
 * 
 * This file contains canonical type definitions for frontend components
 * to prevent SSOT violations across the frontend codebase.
 */

export interface Thread {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  message_count?: number;
}

export interface ChatMessage {
  id: string;
  thread_id: string;
  content: string;
  created_at: string;
  role: 'user' | 'assistant' | 'system';
}

/**
 * Base ThreadState interface - common thread state fields
 */
export interface BaseThreadState {
  activeThreadId: string | null;
  isThreadLoading: boolean;
}

/**
 * Complete ThreadState interface - SSOT for full thread state management
 * 
 * This replaces duplicate ThreadState definitions across the frontend.
 * Use this for components that need complete thread management.
 */
export interface ThreadState extends BaseThreadState {
  // Core thread data
  threads: Thread[];
  currentThread: Thread | null;
  
  // Loading and error states
  isLoading: boolean;
  error: string | null;
  
  // Messages associated with threads
  messages: ChatMessage[];
}

/**
 * Store ThreadState interface - for Zustand stores with actions
 */
export interface StoreThreadState extends BaseThreadState {
  threads: Map<string, unknown>;
  setActiveThread: (threadId: string | null) => void;
  setThreadLoading: (isLoading: boolean) => void;
}

/**
 * Factory function to create initial thread state
 */
export function createThreadState(): ThreadState {
  return {
    threads: [],
    activeThreadId: null,
    currentThread: null,
    isLoading: false,
    isThreadLoading: false,
    error: null,
    messages: []
  };
}

/**
 * Update thread state with partial updates
 */
export function updateThreadState(
  state: ThreadState,
  updates: Partial<ThreadState>
): ThreadState {
  return {
    ...state,
    ...updates
  };
}