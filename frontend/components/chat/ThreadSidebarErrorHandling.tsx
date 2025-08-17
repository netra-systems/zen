import type { ThreadError, ThreadErrorCategory } from '@/types/thread-error-types';

/**
 * Generates unique error ID
 */
const generateErrorId = (): string => {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substr(2, 9);
  return `error_${timestamp}_${random}`;
};

/**
 * Extracts error message from unknown error
 */
const extractErrorMessage = (error: unknown): string => {
  return error instanceof Error ? error.message : String(error);
};

/**
 * Creates thread error from generic error (≤8 lines)
 */
export const createThreadErrorFromError = (threadId: string, error: unknown): ThreadError => {
  const message = extractErrorMessage(error);
  
  return {
    id: generateErrorId(),
    threadId,
    message,
    category: categorizeErrorMessage(message),
    severity: 'medium',
    timestamp: Date.now(),
    retryable: isErrorRetryable(message)
  };
};

/**
 * Categorizes error message based on content
 */
export const categorizeErrorMessage = (message: string): ThreadErrorCategory => {
  const lowerMessage = message.toLowerCase();
  
  if (lowerMessage.includes('timeout')) return 'timeout';
  if (lowerMessage.includes('network') || lowerMessage.includes('fetch')) return 'network';
  if (lowerMessage.includes('abort')) return 'abort';
  
  return 'unknown';
};

/**
 * Checks if error is retryable based on message content
 */
export const isErrorRetryable = (message: string): boolean => {
  const lowerMessage = message.toLowerCase();
  return !lowerMessage.includes('abort') && !lowerMessage.includes('permission');
};