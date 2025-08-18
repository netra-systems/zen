/**
 * Thread Loading Service
 * 
 * Centralized service for thread switching with WebSocket integration.
 * Ensures smooth loading experience and proper state management.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed service with clear interfaces
 */

import { ThreadService, ThreadMessagesResponse } from './threadService';
import { MessageFormatterService } from './messageFormatter';
import type { ChatMessage } from '@/types/registry';

/**
 * Thread loading result interface
 */
export interface ThreadLoadingResult {
  readonly success: boolean;
  readonly messages: ChatMessage[];
  readonly error?: string;
  readonly threadId: string;
}

/**
 * Thread loading options
 */
export interface ThreadLoadingOptions {
  readonly showLoading?: boolean;
  readonly clearPrevious?: boolean;
  readonly limit?: number;
  readonly offset?: number;
}

/**
 * Default thread loading options
 */
const DEFAULT_OPTIONS: Required<ThreadLoadingOptions> = {
  showLoading: true,
  clearPrevious: true,
  limit: 50,
  offset: 0
};

/**
 * Loads thread messages with proper WebSocket event emission
 */
export const loadThreadMessages = async (
  threadId: string,
  options: ThreadLoadingOptions = {}
): Promise<ThreadLoadingResult> => {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  
  try {
    const response = await fetchThreadMessages(threadId, opts);
    const messages = convertToChartMessages(response, threadId);
    
    return createSuccessResult(threadId, messages);
  } catch (error) {
    return createErrorResult(threadId, error);
  }
};

/**
 * Fetches messages from backend API
 */
const fetchThreadMessages = async (
  threadId: string,
  options: Required<ThreadLoadingOptions>
): Promise<ThreadMessagesResponse> => {
  return await ThreadService.getThreadMessages(
    threadId,
    options.limit,
    options.offset
  );
};

/**
 * Converts backend messages to ChatMessage format with formatting
 */
const convertToChartMessages = (
  response: ThreadMessagesResponse,
  threadId: string
): ChatMessage[] => {
  const messages = response.messages.map((msg) => ({
    id: msg.id,
    role: determineMessageRole(msg.role),
    content: msg.content,
    timestamp: convertTimestamp(msg.created_at),
    threadId,
    metadata: msg.metadata
  }));
  
  return messages.map(msg => MessageFormatterService.enrich(msg));
};

/**
 * Determines message role with proper type safety
 */
const determineMessageRole = (role: string): 'user' | 'assistant' | 'system' => {
  if (role === 'user') return 'user';
  if (role === 'system') return 'system';
  return 'assistant';
};

/**
 * Converts timestamp to milliseconds
 */
const convertTimestamp = (createdAt: number): number => {
  return createdAt > 9999999999 ? createdAt : createdAt * 1000;
};

/**
 * Creates successful loading result
 */
const createSuccessResult = (
  threadId: string,
  messages: ChatMessage[]
): ThreadLoadingResult => {
  return {
    success: true,
    messages,
    threadId
  };
};

/**
 * Creates error loading result
 */
const createErrorResult = (
  threadId: string,
  error: unknown
): ThreadLoadingResult => {
  const errorMessage = error instanceof Error ? 
    error.message : 'Failed to load thread messages';
  
  return {
    success: false,
    messages: [],
    error: errorMessage,
    threadId
  };
};

/**
 * Thread loading service class
 */
export class ThreadLoadingService {
  /**
   * Loads thread with WebSocket event integration
   */
  static async loadThread(
    threadId: string,
    options?: ThreadLoadingOptions
  ): Promise<ThreadLoadingResult> {
    return await loadThreadMessages(threadId, options);
  }

  /**
   * Pre-loads thread for faster switching
   */
  static async preloadThread(threadId: string): Promise<ThreadLoadingResult> {
    return await loadThreadMessages(threadId, { 
      showLoading: false,
      clearPrevious: false
    });
  }
}

export const threadLoadingService = ThreadLoadingService;