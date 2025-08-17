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
 * Extracts error message from Error object or unknown value
 */
const extractErrorMessage = (error: Error | unknown): string => {
  return error instanceof Error ? error.message : String(error);
};

/**
 * Creates error details for Error instances
 */
const createErrorDetails = (error: Error | unknown): Record<string, unknown> | undefined => {
  return error instanceof Error ? { stack: error.stack } : undefined;
};

/**
 * Builds ThreadError object with categorized error information
 */
const buildThreadError = (
  threadId: string,
  message: string,
  category: ThreadErrorCategory
): ThreadError => {
  return {
    id: generateErrorId(),
    threadId,
    message,
    category,
    severity: determineSeverity(category),
    timestamp: Date.now(),
    retryable: isRetryableError(category)
  };
};

/**
 * Creates thread error from Error object
 */
export const createThreadError = (
  threadId: string,
  error: Error | unknown,
  category?: ThreadErrorCategory
): ThreadError => {
  const message = extractErrorMessage(error);
  const errorCategory = category || categorizeError(message);
  const threadError = buildThreadError(threadId, message, errorCategory);
  return { ...threadError, details: createErrorDetails(error) };
};

/**
 * Checks timeout error patterns
 */
const isTimeoutError = (message: string): boolean => {
  return message.includes('timeout');
};

/**
 * Checks network error patterns
 */
const isNetworkError = (message: string): boolean => {
  return message.includes('network') || message.includes('fetch');
};

/**
 * Checks abort error patterns
 */
const isAbortError = (message: string): boolean => {
  return message.includes('abort') || message.includes('cancel');
};

/**
 * Checks permission error patterns
 */
const isPermissionError = (message: string): boolean => {
  return message.includes('permission') || message.includes('auth');
};

/**
 * Checks validation error patterns
 */
const isValidationError = (message: string): boolean => {
  return message.includes('validation') || message.includes('invalid');
};

/**
 * Checks server error patterns
 */
const isServerError = (message: string): boolean => {
  return message.includes('server') || message.includes('5');
};

/**
 * Categorizes error based on message
 */
const categorizeError = (message: string): ThreadErrorCategory => {
  const lowerMessage = message.toLowerCase();
  
  if (isTimeoutError(lowerMessage)) return 'timeout';
  if (isNetworkError(lowerMessage)) return 'network';
  if (isAbortError(lowerMessage)) return 'abort';
  if (isPermissionError(lowerMessage)) return 'permission';
  if (isValidationError(lowerMessage)) return 'validation';
  if (isServerError(lowerMessage)) return 'server';
  
  return 'unknown';
};

/**
 * Gets severity for low-level categories
 */
const getLowSeverity = (): ThreadErrorSeverity => {
  return 'low';
};

/**
 * Gets severity for medium-level categories
 */
const getMediumSeverity = (): ThreadErrorSeverity => {
  return 'medium';
};

/**
 * Gets severity for high-level categories
 */
const getHighSeverity = (): ThreadErrorSeverity => {
  return 'high';
};

/**
 * Gets severity for critical-level categories
 */
const getCriticalSeverity = (): ThreadErrorSeverity => {
  return 'critical';
};

/**
 * Determines error severity
 */
const determineSeverity = (category: ThreadErrorCategory): ThreadErrorSeverity => {
  switch (category) {
    case 'abort':
      return getLowSeverity();
    case 'timeout':
    case 'network':
      return getMediumSeverity();
    case 'permission':
    case 'server':
      return getHighSeverity();
    case 'validation':
    case 'unknown':
      return getCriticalSeverity();
    default:
      return getMediumSeverity();
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