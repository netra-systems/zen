/**
 * Thread Timeout Manager
 * 
 * Manages timeouts for thread loading operations to prevent hanging states.
 * Provides automatic cleanup and error recovery for failed thread loads.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed timeout management
 */

/**
 * Thread timeout configuration
 */
export interface ThreadTimeoutConfig {
  readonly timeoutMs: number;
  readonly retryCount: number;
  readonly onTimeout: (threadId: string) => void;
  readonly onRetryExhausted: (threadId: string) => void;
}

/**
 * Active timeout tracking
 */
interface ActiveTimeout {
  readonly threadId: string;
  readonly timeoutId: number;
  readonly startTime: number;
  readonly retryCount: number;
}

/**
 * Default timeout configuration
 */
const DEFAULT_CONFIG: ThreadTimeoutConfig = {
  timeoutMs: 10000, // 10 seconds
  retryCount: 2,
  onTimeout: () => {},
  onRetryExhausted: () => {}
};

/**
 * Thread timeout manager class
 */
export class ThreadTimeoutManager {
  private readonly config: ThreadTimeoutConfig;
  private readonly activeTimeouts: Map<string, ActiveTimeout>;

  constructor(config: Partial<ThreadTimeoutConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.activeTimeouts = new Map();
  }

  /**
   * Starts timeout tracking for thread
   */
  startTimeout(threadId: string): void {
    this.clearExistingTimeout(threadId);
    const timeoutId = this.createTimeout(threadId);
    this.trackActiveTimeout(threadId, timeoutId);
  }

  /**
   * Clears timeout for thread
   */
  clearTimeout(threadId: string): void {
    const timeout = this.activeTimeouts.get(threadId);
    if (timeout) {
      window.clearTimeout(timeout.timeoutId);
      this.activeTimeouts.delete(threadId);
    }
  }

  /**
   * Checks if thread has active timeout
   */
  hasActiveTimeout(threadId: string): boolean {
    return this.activeTimeouts.has(threadId);
  }

  /**
   * Gets timeout duration for thread
   */
  getTimeoutDuration(threadId: string): number {
    const timeout = this.activeTimeouts.get(threadId);
    if (!timeout) return 0;
    
    return Date.now() - timeout.startTime;
  }

  /**
   * Clears existing timeout if present
   */
  private clearExistingTimeout(threadId: string): void {
    this.clearTimeout(threadId);
  }

  /**
   * Creates new timeout for thread
   */
  private createTimeout(threadId: string): number {
    return window.setTimeout(() => {
      this.handleTimeout(threadId);
    }, this.config.timeoutMs);
  }

  /**
   * Tracks active timeout in map
   */
  private trackActiveTimeout(threadId: string, timeoutId: number): void {
    const timeout: ActiveTimeout = {
      threadId,
      timeoutId,
      startTime: Date.now(),
      retryCount: 0
    };
    this.activeTimeouts.set(threadId, timeout);
  }

  /**
   * Handles timeout expiration
   */
  private handleTimeout(threadId: string): void {
    const timeout = this.activeTimeouts.get(threadId);
    if (!timeout) return;

    if (this.shouldRetry(timeout)) {
      this.retryTimeout(threadId, timeout);
    } else {
      this.exhaustRetries(threadId);
    }
  }

  /**
   * Checks if should retry timeout
   */
  private shouldRetry(timeout: ActiveTimeout): boolean {
    return timeout.retryCount < this.config.retryCount;
  }

  /**
   * Retries timeout with incremented count
   */
  private retryTimeout(threadId: string, timeout: ActiveTimeout): void {
    this.config.onTimeout(threadId);
    
    const newTimeoutId = this.createTimeout(threadId);
    const updatedTimeout: ActiveTimeout = {
      ...timeout,
      timeoutId: newTimeoutId,
      retryCount: timeout.retryCount + 1
    };
    
    this.activeTimeouts.set(threadId, updatedTimeout);
  }

  /**
   * Handles retry exhaustion
   */
  private exhaustRetries(threadId: string): void {
    this.clearTimeout(threadId);
    this.config.onRetryExhausted(threadId);
  }
}

/**
 * Creates thread timeout manager with config
 */
export const createThreadTimeoutManager = (
  config?: Partial<ThreadTimeoutConfig>
): ThreadTimeoutManager => {
  return new ThreadTimeoutManager(config);
};

/**
 * Default thread timeout manager instance
 */
export const defaultThreadTimeoutManager = createThreadTimeoutManager();