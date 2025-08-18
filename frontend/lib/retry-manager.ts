/**
 * Retry Manager
 * 
 * Implements exponential backoff retry logic for thread operations.
 * Prevents overwhelming the system with failed requests.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed retry management
 */

import { logger } from '@/utils/debug-logger';

/**
 * Frontend retry configuration options
 */
export interface FrontendFrontendRetryConfig {
  readonly maxAttempts: number;
  readonly baseDelayMs: number;
  readonly maxDelayMs: number;
  readonly multiplier: number;
  readonly jitter: boolean;
}

/**
 * Retry attempt result
 */
export interface RetryAttempt {
  readonly attempt: number;
  readonly delay: number;
  readonly totalElapsed: number;
  readonly success: boolean;
}

/**
 * Retry operation function type
 */
export type RetryOperation<T> = () => Promise<T>;

/**
 * Default retry configuration
 */
const DEFAULT_CONFIG: FrontendRetryConfig = {
  maxAttempts: 3,
  baseDelayMs: 1000,
  maxDelayMs: 10000,
  multiplier: 2,
  jitter: true
};

/**
 * Executes operation with exponential backoff retry
 */
export const executeWithRetry = async <T>(
  operation: RetryOperation<T>,
  config: Partial<FrontendRetryConfig> = {}
): Promise<T> => {
  const fullConfig = { ...DEFAULT_CONFIG, ...config };
  const startTime = Date.now();
  
  for (let attempt = 1; attempt <= fullConfig.maxAttempts; attempt++) {
    try {
      const result = await operation();
      logRetrySuccess(attempt, startTime);
      return result;
    } catch (error) {
      const shouldRetry = determineShouldRetry(attempt, fullConfig, error);
      
      if (!shouldRetry) {
        logRetryFailure(attempt, fullConfig.maxAttempts, error);
        throw error;
      }
      
      const delay = calculateDelay(attempt, fullConfig);
      await waitForDelay(delay);
    }
  }
  
  throw new Error('All retry attempts exhausted');
};

/**
 * Determines if operation should be retried
 */
const determineShouldRetry = (
  attempt: number,
  config: FrontendRetryConfig,
  error: unknown
): boolean => {
  if (attempt >= config.maxAttempts) return false;
  
  if (isNonRetryableError(error)) return false;
  
  return true;
};

/**
 * Checks if error should not be retried
 */
const isNonRetryableError = (error: unknown): boolean => {
  if (error instanceof Error) {
    return error.message.includes('abort') || 
           error.message.includes('cancelled');
  }
  return false;
};

/**
 * Calculates delay for retry attempt
 */
const calculateDelay = (attempt: number, config: FrontendRetryConfig): number => {
  const exponentialDelay = config.baseDelayMs * Math.pow(config.multiplier, attempt - 1);
  const cappedDelay = Math.min(exponentialDelay, config.maxDelayMs);
  
  return config.jitter ? addJitter(cappedDelay) : cappedDelay;
};

/**
 * Adds random jitter to delay
 */
const addJitter = (delay: number): number => {
  const jitterAmount = delay * 0.1; // 10% jitter
  const randomJitter = (Math.random() - 0.5) * 2 * jitterAmount;
  return Math.max(0, delay + randomJitter);
};

/**
 * Waits for specified delay
 */
const waitForDelay = (delayMs: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, delayMs));
};

/**
 * Logs successful retry completion
 */
const logRetrySuccess = (attempt: number, startTime: number): void => {
  const elapsed = Date.now() - startTime;
  logger.debug(`Operation succeeded on attempt ${attempt} after ${elapsed}ms`);
};

/**
 * Logs retry failure
 */
const logRetryFailure = (
  attempt: number,
  maxAttempts: number,
  error: unknown
): void => {
  logger.error(`Operation failed after ${attempt}/${maxAttempts} attempts:`, error);
};

/**
 * Retry manager class for stateful retry operations
 */
export class RetryManager {
  private readonly config: FrontendRetryConfig;
  private currentAttempt: number = 0;
  private startTime: number = 0;

  constructor(config: Partial<FrontendRetryConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Starts new retry session
   */
  startSession(): void {
    this.currentAttempt = 0;
    this.startTime = Date.now();
  }

  /**
   * Gets next retry delay
   */
  getNextDelay(): number {
    this.currentAttempt++;
    return calculateDelay(this.currentAttempt, this.config);
  }

  /**
   * Checks if can retry
   */
  canRetry(): boolean {
    return this.currentAttempt < this.config.maxAttempts;
  }

  /**
   * Gets current attempt info
   */
  getAttemptInfo(): RetryAttempt {
    return {
      attempt: this.currentAttempt,
      delay: calculateDelay(this.currentAttempt, this.config),
      totalElapsed: Date.now() - this.startTime,
      success: false
    };
  }
}

/**
 * Creates retry manager with config
 */
export const createRetryManager = (config?: Partial<FrontendRetryConfig>): RetryManager => {
  return new RetryManager(config);
};