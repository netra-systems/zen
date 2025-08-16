/**
 * Operation Cleanup Manager
 * 
 * Manages cleanup of aborted thread operations to prevent memory leaks.
 * Ensures proper resource cleanup and state consistency.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed cleanup management
 */

/**
 * Cleanup operation function type
 */
export type CleanupOperation = () => void | Promise<void>;

/**
 * Cleanup registration options
 */
export interface CleanupOptions {
  readonly priority: 'high' | 'medium' | 'low';
  readonly timeout: number;
  readonly description?: string;
}

/**
 * Active cleanup registration
 */
interface CleanupRegistration {
  readonly id: string;
  readonly operation: CleanupOperation;
  readonly options: CleanupOptions;
  readonly registeredAt: number;
}

/**
 * Default cleanup options
 */
const DEFAULT_OPTIONS: CleanupOptions = {
  priority: 'medium',
  timeout: 5000,
  description: 'Generic cleanup operation'
};

/**
 * Operation cleanup manager
 */
export class OperationCleanupManager {
  private readonly cleanupOperations = new Map<string, CleanupRegistration>();
  private readonly abortControllers = new Map<string, AbortController>();
  private cleanupInProgress = false;

  /**
   * Registers cleanup operation for thread
   */
  registerCleanup(
    threadId: string,
    operation: CleanupOperation,
    options: Partial<CleanupOptions> = {}
  ): string {
    const cleanupId = generateCleanupId(threadId);
    const fullOptions = { ...DEFAULT_OPTIONS, ...options };
    
    this.cleanupOperations.set(cleanupId, {
      id: cleanupId,
      operation,
      options: fullOptions,
      registeredAt: Date.now()
    });
    
    return cleanupId;
  }

  /**
   * Registers abort controller for thread
   */
  registerAbortController(threadId: string, controller: AbortController): void {
    this.abortControllers.set(threadId, controller);
  }

  /**
   * Cleans up operations for specific thread
   */
  async cleanupThread(threadId: string): Promise<void> {
    const threadCleanups = this.getThreadCleanups(threadId);
    await this.executeCleanups(threadCleanups);
    this.removeThreadCleanups(threadId);
    this.abortThreadOperations(threadId);
  }

  /**
   * Cleans up all registered operations
   */
  async cleanupAll(): Promise<void> {
    if (this.cleanupInProgress) return;
    
    this.cleanupInProgress = true;
    
    try {
      const allCleanups = Array.from(this.cleanupOperations.values());
      await this.executeCleanups(allCleanups);
      this.clearAllRegistrations();
    } finally {
      this.cleanupInProgress = false;
    }
  }

  /**
   * Gets cleanup operations for thread
   */
  private getThreadCleanups(threadId: string): CleanupRegistration[] {
    return Array.from(this.cleanupOperations.values())
      .filter(cleanup => cleanup.id.includes(threadId));
  }

  /**
   * Executes cleanup operations by priority
   */
  private async executeCleanups(cleanups: CleanupRegistration[]): Promise<void> {
    const sortedCleanups = this.sortCleanupsByPriority(cleanups);
    
    for (const cleanup of sortedCleanups) {
      await this.executeCleanupSafely(cleanup);
    }
  }

  /**
   * Sorts cleanups by priority (high to low)
   */
  private sortCleanupsByPriority(cleanups: CleanupRegistration[]): CleanupRegistration[] {
    const priorityOrder = { high: 3, medium: 2, low: 1 };
    
    return cleanups.sort((a, b) => 
      priorityOrder[b.options.priority] - priorityOrder[a.options.priority]
    );
  }

  /**
   * Executes single cleanup operation safely
   */
  private async executeCleanupSafely(cleanup: CleanupRegistration): Promise<void> {
    try {
      const timeoutPromise = this.createTimeoutPromise(cleanup.options.timeout);
      const cleanupPromise = Promise.resolve(cleanup.operation());
      
      await Promise.race([cleanupPromise, timeoutPromise]);
    } catch (error) {
      console.warn(`Cleanup operation failed for ${cleanup.id}:`, error);
    }
  }

  /**
   * Creates timeout promise for cleanup operation
   */
  private createTimeoutPromise(timeoutMs: number): Promise<never> {
    return new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Cleanup timeout')), timeoutMs);
    });
  }

  /**
   * Removes cleanup operations for thread
   */
  private removeThreadCleanups(threadId: string): void {
    const keysToRemove = Array.from(this.cleanupOperations.keys())
      .filter(key => key.includes(threadId));
    
    for (const key of keysToRemove) {
      this.cleanupOperations.delete(key);
    }
  }

  /**
   * Aborts operations for thread
   */
  private abortThreadOperations(threadId: string): void {
    const controller = this.abortControllers.get(threadId);
    if (controller && !controller.signal.aborted) {
      controller.abort();
    }
    this.abortControllers.delete(threadId);
  }

  /**
   * Clears all registrations
   */
  private clearAllRegistrations(): void {
    this.cleanupOperations.clear();
    this.abortAllControllers();
  }

  /**
   * Aborts all active controllers
   */
  private abortAllControllers(): void {
    for (const controller of this.abortControllers.values()) {
      if (!controller.signal.aborted) {
        controller.abort();
      }
    }
    this.abortControllers.clear();
  }
}

/**
 * Generates unique cleanup ID
 */
const generateCleanupId = (threadId: string): string => {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substr(2, 9);
  return `cleanup_${threadId}_${timestamp}_${random}`;
};

/**
 * Global cleanup manager instance
 */
export const globalCleanupManager = new OperationCleanupManager();

/**
 * Creates cleanup manager for specific context
 */
export const createCleanupManager = (): OperationCleanupManager => {
  return new OperationCleanupManager();
};