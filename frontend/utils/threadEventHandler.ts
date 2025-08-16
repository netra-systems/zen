/**
 * Thread Event Handler Utilities
 * 
 * Manages WebSocket events for thread operations to ensure smooth UI transitions.
 * Provides proper loading states and error handling for thread switching.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed event handlers
 */

import type { 
  UnifiedWebSocketEvent,
  ThreadLoadingEvent,
  ThreadLoadedEvent,
  ThreadCreatedEvent,
  ChatMessage
} from '@/types/unified-chat';

/**
 * Thread event handler configuration
 */
export interface ThreadEventConfig {
  readonly timeoutMs: number;
  readonly retryAttempts: number;
  readonly enableLogging: boolean;
}

/**
 * Thread loading context
 */
export interface ThreadLoadingContext {
  readonly threadId: string;
  readonly isLoading: boolean;
  readonly startTime: number;
  readonly timeoutId?: number;
}

/**
 * Default configuration for thread events
 */
const DEFAULT_CONFIG: ThreadEventConfig = {
  timeoutMs: 5000,
  retryAttempts: 2,
  enableLogging: true
};

/**
 * Creates thread loading event
 */
export const createThreadLoadingEvent = (threadId: string): ThreadLoadingEvent => {
  return {
    type: 'thread_loading',
    payload: {
      thread_id: threadId
    }
  };
};

/**
 * Creates thread loaded event
 */
export const createThreadLoadedEvent = (
  threadId: string,
  messages: ChatMessage[]
): ThreadLoadedEvent => {
  return {
    type: 'thread_loaded',
    payload: {
      thread_id: threadId,
      messages,
      metadata: {}
    }
  };
};

/**
 * Creates thread created event
 */
export const createThreadCreatedEvent = (
  threadId: string,
  userId: string
): ThreadCreatedEvent => {
  return {
    type: 'thread_created',
    payload: {
      thread_id: threadId,
      user_id: userId,
      created_at: Date.now()
    }
  };
};

/**
 * Validates thread event payload
 */
export const validateThreadEvent = (event: UnifiedWebSocketEvent): boolean => {
  if (!isThreadEvent(event)) return false;
  if (!hasValidPayload(event)) return false;
  return hasRequiredFields(event);
};

/**
 * Checks if event is thread-related
 */
const isThreadEvent = (event: UnifiedWebSocketEvent): boolean => {
  const threadEventTypes = ['thread_loading', 'thread_loaded', 'thread_created'];
  return threadEventTypes.includes(event.type);
};

/**
 * Validates event has payload
 */
const hasValidPayload = (event: UnifiedWebSocketEvent): boolean => {
  return event.payload && typeof event.payload === 'object';
};

/**
 * Checks required fields in thread events
 */
const hasRequiredFields = (event: UnifiedWebSocketEvent): boolean => {
  const payload = event.payload as any;
  return payload.thread_id && typeof payload.thread_id === 'string';
};

/**
 * Creates loading timeout handler
 */
export const createLoadingTimeout = (
  threadId: string,
  timeoutMs: number,
  onTimeout: (threadId: string) => void
): number => {
  return window.setTimeout(() => {
    onTimeout(threadId);
  }, timeoutMs);
};

/**
 * Clears loading timeout
 */
export const clearLoadingTimeout = (timeoutId: number): void => {
  if (timeoutId) {
    window.clearTimeout(timeoutId);
  }
};

/**
 * Thread event handler factory
 */
export class ThreadEventHandler {
  private readonly config: ThreadEventConfig;
  private readonly loadingContexts: Map<string, ThreadLoadingContext>;

  constructor(config: Partial<ThreadEventConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.loadingContexts = new Map();
  }

  /**
   * Starts thread loading tracking
   */
  startLoading(threadId: string): ThreadLoadingContext {
    const context = this.createLoadingContext(threadId);
    this.loadingContexts.set(threadId, context);
    return context;
  }

  /**
   * Finishes thread loading tracking
   */
  finishLoading(threadId: string): boolean {
    const context = this.loadingContexts.get(threadId);
    if (!context) return false;
    
    this.cleanupLoadingContext(context);
    this.loadingContexts.delete(threadId);
    return true;
  }

  /**
   * Checks if thread is loading
   */
  isLoading(threadId: string): boolean {
    return this.loadingContexts.has(threadId);
  }

  /**
   * Creates loading context
   */
  private createLoadingContext(threadId: string): ThreadLoadingContext {
    return {
      threadId,
      isLoading: true,
      startTime: Date.now()
    };
  }

  /**
   * Cleans up loading context resources
   */
  private cleanupLoadingContext(context: ThreadLoadingContext): void {
    if (context.timeoutId) {
      clearLoadingTimeout(context.timeoutId);
    }
  }
}

/**
 * Default thread event handler instance
 */
export const threadEventHandler = new ThreadEventHandler();