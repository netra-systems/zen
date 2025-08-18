/**
 * Thread Error Recovery Strategies
 * 
 * Implements specialized recovery strategies for different types of thread errors.
 * Provides automated and manual recovery options for thread loading failures.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed error recovery
 */

import type { 
  ThreadError, 
  ThreadErrorRecovery, 
  ThreadErrorRecoveryOptions,
  ThreadErrorCategory 
} from '@/types/thread-error-types';
import { executeWithRetry } from '@/lib/retry-manager';
import { globalCleanupManager } from '@/lib/operation-cleanup';

/**
 * Recovery strategy result
 */
export interface RecoveryResult {
  readonly success: boolean;
  readonly action: string;
  readonly nextRetryDelay?: number;
  readonly shouldRetry: boolean;
  readonly fallbackUsed: boolean;
}

/**
 * Recovery strategy function type
 */
export type RecoveryStrategy = (
  error: ThreadError,
  options: ThreadErrorRecoveryOptions
) => Promise<RecoveryResult>;

/**
 * Recovers from network errors
 */
const recoverFromNetworkError = async (
  error: ThreadError,
  options: ThreadErrorRecoveryOptions
): Promise<RecoveryResult> => {
  if (options.autoRetry && error.retryable) {
    await waitForRetryDelay(options.retryDelay);
    return createRetryRecoveryResult();
  }
  return createManualRetryResult(options.retryDelay * 2);
};

/**
 * Recovers from timeout errors
 */
const recoverFromTimeoutError = async (
  error: ThreadError,
  options: ThreadErrorRecoveryOptions
): Promise<RecoveryResult> => {
  await globalCleanupManager.cleanupThread(error.threadId);
  if (options.autoRetry) {
    const extendedDelay = Math.min(options.retryDelay * 3, 15000);
    await waitForRetryDelay(extendedDelay);
    return createRetryRecoveryResult(extendedDelay);
  }
  return createManualRetryResult(options.retryDelay * 3);
};

/**
 * Recovers from abort errors
 */
const recoverFromAbortError = async (
  error: ThreadError,
  options: ThreadErrorRecoveryOptions
): Promise<RecoveryResult> => {
  await globalCleanupManager.cleanupThread(error.threadId);
  return {
    success: true,
    action: 'Operation cancelled, cleanup completed',
    shouldRetry: false,
    fallbackUsed: false
  };
};

/**
 * Recovers from permission errors
 */
const recoverFromPermissionError = async (
  error: ThreadError,
  options: ThreadErrorRecoveryOptions
): Promise<RecoveryResult> => {
  return {
    success: false,
    action: 'Authentication required - please sign in again',
    shouldRetry: false,
    fallbackUsed: options.fallbackAction !== undefined
  };
};

/**
 * Recovers from validation errors
 */
const recoverFromValidationError = async (
  error: ThreadError,
  options: ThreadErrorRecoveryOptions
): Promise<RecoveryResult> => {
  return {
    success: false,
    action: 'Invalid request - please refresh and try again',
    shouldRetry: false,
    fallbackUsed: options.fallbackAction !== undefined
  };
};

/**
 * Recovers from server errors
 */
const recoverFromServerError = async (
  error: ThreadError,
  options: ThreadErrorRecoveryOptions
): Promise<RecoveryResult> => {
  if (options.autoRetry && error.retryable) {
    const backoffDelay = calculateExponentialBackoff(options.retryDelay);
    await waitForRetryDelay(backoffDelay);
    return createRetryRecoveryResult(backoffDelay);
  }
  return createManualRetryResult(options.retryDelay * 4);
};

/**
 * Recovers from unknown errors
 */
const recoverFromUnknownError = async (
  error: ThreadError,
  options: ThreadErrorRecoveryOptions
): Promise<RecoveryResult> => {
  await globalCleanupManager.cleanupThread(error.threadId);
  return {
    success: false,
    action: 'Unknown error occurred - please refresh the page',
    shouldRetry: false,
    fallbackUsed: options.fallbackAction !== undefined
  };
};

/**
 * Recovery strategy registry
 */
const RECOVERY_STRATEGIES: Record<ThreadErrorCategory, RecoveryStrategy> = {
  network: recoverFromNetworkError,
  timeout: recoverFromTimeoutError,
  abort: recoverFromAbortError,
  permission: recoverFromPermissionError,
  validation: recoverFromValidationError,
  server: recoverFromServerError,
  unknown: recoverFromUnknownError
};

/**
 * Executes recovery strategy for thread error
 */
export const recoverFromThreadError = async (
  error: ThreadError,
  options: ThreadErrorRecoveryOptions
): Promise<RecoveryResult> => {
  const strategy = RECOVERY_STRATEGIES[error.category];
  try {
    return await strategy(error, options);
  } catch (recoveryError) {
    return createFailedRecoveryResult(error, recoveryError);
  }
};

/**
 * Waits for retry delay
 */
const waitForRetryDelay = async (delayMs: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, delayMs));
};

/**
 * Calculates exponential backoff delay
 */
const calculateExponentialBackoff = (baseDelay: number): number => {
  const jitter = Math.random() * 0.1; // 10% jitter
  return Math.min(baseDelay * 2 * (1 + jitter), 30000); // Max 30 seconds
};

/**
 * Creates retry recovery result
 */
const createRetryRecoveryResult = (nextDelay?: number): RecoveryResult => {
  return {
    success: true,
    action: 'Automatic retry initiated',
    nextRetryDelay: nextDelay,
    shouldRetry: true,
    fallbackUsed: false
  };
};

/**
 * Creates manual retry result
 */
const createManualRetryResult = (suggestedDelay: number): RecoveryResult => {
  return {
    success: false,
    action: 'Manual retry suggested',
    nextRetryDelay: suggestedDelay,
    shouldRetry: true,
    fallbackUsed: false
  };
};

/**
 * Creates failed recovery result
 */
const createFailedRecoveryResult = (
  error: ThreadError,
  recoveryError: unknown
): RecoveryResult => {
  return {
    success: false,
    action: `Recovery failed: ${recoveryError}`,
    shouldRetry: false,
    fallbackUsed: false
  };
};

/**
 * Thread error recovery manager
 */
export class ThreadErrorRecoveryManager {
  private readonly defaultOptions: ThreadErrorRecoveryOptions;

  constructor(options: Partial<ThreadErrorRecoveryOptions> = {}) {
    this.defaultOptions = {
      retryDelay: 2000,
      maxRetries: 3,
      exponentialBackoff: true,
      autoRetry: false,
      ...options
    };
  }

  /**
   * Recovers from thread error with default options
   */
  async recover(
    error: ThreadError,
    options?: Partial<ThreadErrorRecoveryOptions>
  ): Promise<RecoveryResult> {
    const fullOptions = { ...this.defaultOptions, ...options };
    return await recoverFromThreadError(error, fullOptions);
  }

  /**
   * Checks if error is recoverable
   */
  isRecoverable(error: ThreadError): boolean {
    return error.retryable && error.category !== 'abort';
  }

  /**
   * Gets suggested recovery action
   */
  getSuggestedAction(error: ThreadError): string {
    switch (error.category) {
      case 'network':
        return 'Check your internet connection and try again';
      case 'timeout':
        return 'The request timed out. Please try again';
      case 'permission':
        return 'Please sign in and try again';
      case 'server':
        return 'Server error occurred. Please try again later';
      default:
        return 'An error occurred. Please refresh and try again';
    }
  }
}

/**
 * Default recovery manager instance
 */
export const defaultRecoveryManager = new ThreadErrorRecoveryManager();