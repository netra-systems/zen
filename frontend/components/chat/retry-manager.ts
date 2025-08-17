import type { RetryConfig, TransientErrorConfig } from './error-boundary-types';
import { DEFAULT_RETRY_CONFIG, DEFAULT_TRANSIENT_ERRORS } from './error-boundary-types';

export class RetryManager {
  private retryTimeouts: Set<NodeJS.Timeout> = new Set();
  private config: RetryConfig;
  private transientConfig: TransientErrorConfig;

  constructor(
    config: Partial<RetryConfig> = {},
    transientErrors = DEFAULT_TRANSIENT_ERRORS
  ) {
    this.config = { ...DEFAULT_RETRY_CONFIG, ...config };
    this.transientConfig = {
      errorTypes: transientErrors,
      shouldAutoRetry: this.createAutoRetryChecker(transientErrors)
    };
  }

  private createAutoRetryChecker(errorTypes: string[]) {
    return (error: Error): boolean => {
      return errorTypes.some(errorType => 
        error.name.includes(errorType) || error.message.includes(errorType)
      );
    };
  }

  shouldRetry(error: Error, errorCount: number): boolean {
    return this.transientConfig.shouldAutoRetry(error) 
      && errorCount < this.config.maxRetries;
  }

  calculateRetryDelay(errorCount: number): number {
    if (!this.config.useExponentialBackoff) {
      return this.config.retryDelay;
    }
    return this.config.retryDelay * Math.pow(2, errorCount);
  }

  scheduleRetry(callback: () => void, errorCount: number): void {
    const delay = this.calculateRetryDelay(errorCount);
    const timeout = setTimeout(() => {
      callback();
      this.retryTimeouts.delete(timeout);
    }, delay);
    this.retryTimeouts.add(timeout);
  }

  clearAllRetries(): void {
    this.retryTimeouts.forEach(timeout => clearTimeout(timeout));
    this.retryTimeouts.clear();
  }

  getActiveRetryCount(): number {
    return this.retryTimeouts.size;
  }
}