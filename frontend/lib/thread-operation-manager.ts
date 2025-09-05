/**
 * Thread Operation Manager
 * 
 * Singleton manager that ensures thread operations are atomic and prevents race conditions.
 * Handles new chat creation, thread switching, and cleanup with proper state management.
 * 
 * @compliance conventions.xml - Single responsibility, under 750 lines
 * @compliance type_safety.xml - Strongly typed with clear interfaces
 */

import { logger } from '@/lib/logger';

/**
 * Thread operation types
 */
export type ThreadOperationType = 'create' | 'switch' | 'load' | 'delete';

/**
 * Thread operation state
 */
export interface ThreadOperation {
  readonly id: string;
  readonly type: ThreadOperationType;
  readonly threadId: string | null;
  readonly startTime: number;
  readonly status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  readonly error?: Error;
  readonly abortController?: AbortController;
}

/**
 * Thread operation result
 */
export interface ThreadOperationResult {
  readonly success: boolean;
  readonly threadId?: string;
  readonly error?: Error;
}

/**
 * Thread operation options
 */
export interface ThreadOperationOptions {
  readonly timeoutMs?: number;
  readonly retryAttempts?: number;
  readonly skipDuplicateCheck?: boolean;
  readonly force?: boolean;
}

/**
 * Thread operation listener
 */
export type ThreadOperationListener = (operation: ThreadOperation) => void;

/**
 * Thread Operation Manager - Singleton
 */
class ThreadOperationManagerImpl {
  private currentOperation: ThreadOperation | null = null;
  private operationHistory: ThreadOperation[] = [];
  private listeners = new Set<ThreadOperationListener>();
  private operationQueue: Array<() => Promise<void>> = [];
  private isProcessingQueue = false;
  private readonly MAX_HISTORY_SIZE = 50;
  private readonly DEFAULT_TIMEOUT_MS = 10000;
  private readonly operationLocks = new Map<string, Promise<ThreadOperationResult>>();

  /**
   * Starts a new thread operation
   */
  public async startOperation(
    type: ThreadOperationType,
    threadId: string | null,
    executor: (signal: AbortSignal) => Promise<ThreadOperationResult>,
    options: ThreadOperationOptions = {}
  ): Promise<ThreadOperationResult> {
    const operationId = this.generateOperationId(type, threadId);
    
    // Check for duplicate operations unless skipped
    if (!options.skipDuplicateCheck && this.isDuplicateOperation(type, threadId)) {
      logger.warn(`Duplicate ${type} operation for thread ${threadId} - skipping`);
      return { success: false, error: new Error('Operation already in progress') };
    }
    
    // Force cancel current operation if requested
    if (options.force && this.currentOperation) {
      await this.cancelCurrentOperation();
    }
    
    // Wait for current operation if not forced
    if (this.currentOperation && !options.force) {
      return await this.queueOperation(type, threadId, executor, options);
    }
    
    // Check for existing lock on this thread
    const lockKey = `${type}:${threadId || 'new'}`;
    const existingLock = this.operationLocks.get(lockKey);
    if (existingLock) {
      logger.info(`Waiting for existing ${type} operation on thread ${threadId}`);
      return await existingLock;
    }
    
    // Create and execute operation
    const operation = this.createOperation(operationId, type, threadId);
    const promise = this.executeOperation(operation, executor, options);
    
    // Store lock
    this.operationLocks.set(lockKey, promise);
    
    // Clean up lock when done
    promise.finally(() => {
      this.operationLocks.delete(lockKey);
    });
    
    return await promise;
  }

  /**
   * Cancels the current operation
   */
  public async cancelCurrentOperation(): Promise<void> {
    if (!this.currentOperation) return;
    
    const operation = this.currentOperation;
    logger.info(`Cancelling ${operation.type} operation ${operation.id}`);
    
    // Abort the operation
    if (operation.abortController) {
      operation.abortController.abort();
    }
    
    // Update operation status
    this.updateOperation(operation.id, { 
      status: 'cancelled',
      error: new Error('Operation cancelled by user')
    });
    
    // Clear current operation
    this.currentOperation = null;
    
    // Process next queued operation
    await this.processQueue();
  }

  /**
   * Checks if an operation is currently running
   */
  public isOperationInProgress(type?: ThreadOperationType, threadId?: string): boolean {
    if (!this.currentOperation) return false;
    
    if (type && this.currentOperation.type !== type) return false;
    if (threadId && this.currentOperation.threadId !== threadId) return false;
    
    return this.currentOperation.status === 'running';
  }

  /**
   * Gets the current operation
   */
  public getCurrentOperation(): ThreadOperation | null {
    return this.currentOperation;
  }

  /**
   * Gets operation history
   */
  public getOperationHistory(): ReadonlyArray<ThreadOperation> {
    return [...this.operationHistory];
  }

  /**
   * Clears operation history
   */
  public clearHistory(): void {
    this.operationHistory = [];
  }

  /**
   * Adds an operation listener
   */
  public addListener(listener: ThreadOperationListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Creates a new operation
   */
  private createOperation(
    id: string,
    type: ThreadOperationType,
    threadId: string | null
  ): ThreadOperation {
    return {
      id,
      type,
      threadId,
      startTime: Date.now(),
      status: 'pending',
      abortController: new AbortController()
    };
  }

  /**
   * Executes an operation
   */
  private async executeOperation(
    operation: ThreadOperation,
    executor: (signal: AbortSignal) => Promise<ThreadOperationResult>,
    options: ThreadOperationOptions
  ): Promise<ThreadOperationResult> {
    // Set as current operation
    this.currentOperation = operation;
    this.updateOperation(operation.id, { status: 'running' });
    
    const timeoutMs = options.timeoutMs || this.DEFAULT_TIMEOUT_MS;
    const retryAttempts = options.retryAttempts || 0;
    
    try {
      // Execute with timeout
      const result = await this.executeWithTimeout(
        executor,
        operation.abortController!.signal,
        timeoutMs
      );
      
      // Handle retry if failed
      if (!result.success && retryAttempts > 0) {
        logger.info(`Retrying ${operation.type} operation (${retryAttempts} attempts left)`);
        return await this.executeOperation(
          operation,
          executor,
          { ...options, retryAttempts: retryAttempts - 1 }
        );
      }
      
      // Update operation status
      this.updateOperation(operation.id, { 
        status: result.success ? 'completed' : 'failed',
        error: result.error
      });
      
      // Add to history
      this.addToHistory(operation);
      
      return result;
    } catch (error) {
      logger.error(`Operation ${operation.id} failed:`, error);
      
      this.updateOperation(operation.id, { 
        status: 'failed',
        error: error as Error
      });
      
      this.addToHistory(operation);
      
      return {
        success: false,
        error: error as Error
      };
    } finally {
      // Clear current operation
      if (this.currentOperation?.id === operation.id) {
        this.currentOperation = null;
      }
      
      // Process next queued operation
      await this.processQueue();
    }
  }

  /**
   * Executes with timeout
   */
  private async executeWithTimeout(
    executor: (signal: AbortSignal) => Promise<ThreadOperationResult>,
    signal: AbortSignal,
    timeoutMs: number
  ): Promise<ThreadOperationResult> {
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error(`Operation timed out after ${timeoutMs}ms`));
      }, timeoutMs);
      
      executor(signal)
        .then(result => {
          clearTimeout(timeoutId);
          resolve(result);
        })
        .catch(error => {
          clearTimeout(timeoutId);
          reject(error);
        });
    });
  }

  /**
   * Queues an operation
   */
  private async queueOperation(
    type: ThreadOperationType,
    threadId: string | null,
    executor: (signal: AbortSignal) => Promise<ThreadOperationResult>,
    options: ThreadOperationOptions
  ): Promise<ThreadOperationResult> {
    return new Promise((resolve) => {
      this.operationQueue.push(async () => {
        const result = await this.startOperation(type, threadId, executor, {
          ...options,
          skipDuplicateCheck: true
        });
        resolve(result);
      });
      
      logger.info(`Queued ${type} operation for thread ${threadId}`);
    });
  }

  /**
   * Processes the operation queue
   */
  private async processQueue(): Promise<void> {
    if (this.isProcessingQueue || this.operationQueue.length === 0) {
      return;
    }
    
    this.isProcessingQueue = true;
    
    try {
      while (this.operationQueue.length > 0) {
        const operation = this.operationQueue.shift();
        if (operation) {
          await operation();
        }
      }
    } finally {
      this.isProcessingQueue = false;
    }
  }

  /**
   * Updates an operation
   */
  private updateOperation(id: string, updates: Partial<ThreadOperation>): void {
    if (this.currentOperation?.id === id) {
      this.currentOperation = { ...this.currentOperation, ...updates };
      this.notifyListeners(this.currentOperation);
    }
  }

  /**
   * Adds operation to history
   */
  private addToHistory(operation: ThreadOperation): void {
    this.operationHistory.unshift(operation);
    
    // Trim history if too large
    if (this.operationHistory.length > this.MAX_HISTORY_SIZE) {
      this.operationHistory = this.operationHistory.slice(0, this.MAX_HISTORY_SIZE);
    }
  }

  /**
   * Notifies listeners
   */
  private notifyListeners(operation: ThreadOperation): void {
    this.listeners.forEach(listener => {
      try {
        listener(operation);
      } catch (error) {
        logger.error('Operation listener error:', error);
      }
    });
  }

  /**
   * Checks for duplicate operations
   */
  private isDuplicateOperation(type: ThreadOperationType, threadId: string | null): boolean {
    if (!this.currentOperation) return false;
    
    return (
      this.currentOperation.type === type &&
      this.currentOperation.threadId === threadId &&
      this.currentOperation.status === 'running'
    );
  }

  /**
   * Generates operation ID
   */
  private generateOperationId(type: ThreadOperationType, threadId: string | null): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substr(2, 9);
    return `${type}_${threadId || 'new'}_${timestamp}_${random}`;
  }
}

// Export singleton instance
export const ThreadOperationManager = new ThreadOperationManagerImpl();

/**
 * Hook for using thread operation manager
 */
export const useThreadOperationManager = () => {
  return ThreadOperationManager;
};