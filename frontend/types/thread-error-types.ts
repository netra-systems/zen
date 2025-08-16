/**
 * Thread Error Types
 * 
 * Type definitions for thread loading error handling and recovery.
 * Provides comprehensive error classification and state management.
 * 
 * @compliance conventions.xml - Under 300 lines
 * @compliance type_safety.xml - Strongly typed error states
 */

/**
 * Thread error severity levels
 */
export type ThreadErrorSeverity = 'low' | 'medium' | 'high' | 'critical';

/**
 * Thread error categories
 */
export type ThreadErrorCategory = 
  | 'network'
  | 'timeout'
  | 'abort'
  | 'permission'
  | 'validation'
  | 'server'
  | 'unknown';

/**
 * Thread loading states
 */
export type ThreadLoadingState = 
  | 'idle'
  | 'loading'
  | 'success'
  | 'error'
  | 'retrying'
  | 'timeout'
  | 'aborted';

/**
 * Thread error information
 */
export interface ThreadError {
  readonly id: string;
  readonly threadId: string;
  readonly message: string;
  readonly category: ThreadErrorCategory;
  readonly severity: ThreadErrorSeverity;
  readonly timestamp: number;
  readonly retryable: boolean;
  readonly details?: Record<string, unknown>;
}

/**
 * Thread loading error state
 */
export interface ThreadLoadingErrorState {
  readonly state: ThreadLoadingState;
  readonly error: ThreadError | null;
  readonly retryCount: number;
  readonly maxRetries: number;
  readonly lastRetryAt: number | null;
  readonly canRetry: boolean;
  readonly isRetrying: boolean;
}

/**
 * Thread error recovery options
 */
export interface ThreadErrorRecoveryOptions {
  readonly retryDelay: number;
  readonly maxRetries: number;
  readonly exponentialBackoff: boolean;
  readonly autoRetry: boolean;
  readonly fallbackAction?: () => void;
}

/**
 * Thread error context
 */
export interface ThreadErrorContext {
  readonly threadId: string;
  readonly operation: string;
  readonly userAgent: string;
  readonly timestamp: number;
  readonly additionalData?: Record<string, unknown>;
}

/**
 * Thread error handler function type
 */
export type ThreadErrorHandler = (
  error: ThreadError,
  context: ThreadErrorContext
) => void | Promise<void>;

/**
 * Thread error recovery function type
 */
export type ThreadErrorRecovery = (
  error: ThreadError,
  options: ThreadErrorRecoveryOptions
) => Promise<boolean>;

/**
 * Thread error notification
 */
export interface ThreadErrorNotification {
  readonly id: string;
  readonly error: ThreadError;
  readonly shown: boolean;
  readonly dismissed: boolean;
  readonly timestamp: number;
}

/**
 * Creates thread error from Error object
 */
export const createThreadError = (
  threadId: string,
  error: Error | unknown,
  category?: ThreadErrorCategory
): ThreadError => {
  const message = error instanceof Error ? error.message : String(error);
  const errorCategory = category || categorizeError(message);
  
  return {
    id: generateErrorId(),
    threadId,
    message,
    category: errorCategory,
    severity: determineSeverity(errorCategory),
    timestamp: Date.now(),
    retryable: isRetryableError(errorCategory),
    details: error instanceof Error ? { stack: error.stack } : undefined
  };
};

/**
 * Categorizes error based on message
 */
const categorizeError = (message: string): ThreadErrorCategory => {
  const lowerMessage = message.toLowerCase();
  
  if (lowerMessage.includes('timeout')) return 'timeout';
  if (lowerMessage.includes('network') || lowerMessage.includes('fetch')) return 'network';
  if (lowerMessage.includes('abort') || lowerMessage.includes('cancel')) return 'abort';
  if (lowerMessage.includes('permission') || lowerMessage.includes('auth')) return 'permission';
  if (lowerMessage.includes('validation') || lowerMessage.includes('invalid')) return 'validation';
  if (lowerMessage.includes('server') || lowerMessage.includes('5')) return 'server';
  
  return 'unknown';
};

/**
 * Determines error severity
 */
const determineSeverity = (category: ThreadErrorCategory): ThreadErrorSeverity => {
  switch (category) {
    case 'abort':
      return 'low';
    case 'timeout':
    case 'network':
      return 'medium';
    case 'permission':
    case 'server':
      return 'high';
    case 'validation':
    case 'unknown':
      return 'critical';
    default:
      return 'medium';
  }
};

/**
 * Checks if error is retryable
 */
const isRetryableError = (category: ThreadErrorCategory): boolean => {
  return ['timeout', 'network', 'server'].includes(category);
};

/**
 * Generates unique error ID
 */
const generateErrorId = (): string => {
  return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};