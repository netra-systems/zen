/**
 * Mock for ThreadOperationManager
 * 
 * Provides a functional mock implementation that actually executes operations
 * and maintains proper state management for testing thread switching functionality.
 */

export type ThreadOperationType = 'create' | 'switch' | 'load' | 'delete';

export interface ThreadOperation {
  readonly id: string;
  readonly type: ThreadOperationType;
  readonly threadId: string | null;
  readonly startTime: number;
  readonly status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  readonly error?: Error;
  readonly abortController?: AbortController;
}

export interface ThreadOperationResult {
  readonly success: boolean;
  readonly threadId?: string;
  readonly error?: Error;
}

export interface ThreadOperationOptions {
  readonly timeoutMs?: number;
  readonly retryAttempts?: number;
  readonly skipDuplicateCheck?: boolean;
  readonly force?: boolean;
}

export type ThreadOperationListener = (operation: ThreadOperation) => void;

/**
 * Mock ThreadOperationManager implementation that actually executes operations
 */
class MockThreadOperationManagerImpl {
  public currentOperation: ThreadOperation | null = null;
  public operationHistory: ThreadOperation[] = [];
  public listeners = new Set<ThreadOperationListener>();
  public operationExecutionHistory: Array<{
    type: ThreadOperationType;
    threadId: string | null;
    options: ThreadOperationOptions;
    result: ThreadOperationResult;
  }> = [];

  /**
   * Mock implementation that actually executes the provided executor function
   */
  public async startOperation(
    type: ThreadOperationType,
    threadId: string | null,
    executor: (signal: AbortSignal) => Promise<ThreadOperationResult>,
    options: ThreadOperationOptions = {}
  ): Promise<ThreadOperationResult> {
    const operationId = this.generateOperationId(type, threadId);
    
    // Create operation
    const operation: ThreadOperation = {
      id: operationId,
      type,
      threadId,
      startTime: Date.now(),
      status: 'pending',
      abortController: new AbortController()
    };

    // Set as current operation
    this.currentOperation = operation;
    this.updateOperation(operationId, { status: 'running' });

    try {
      // Actually execute the provided function
      console.log('ThreadOperationManager: About to call executor function');
      const result = await executor(operation.abortController!.signal);
      console.log('ThreadOperationManager: Executor returned:', result);
      
      // Update operation status based on result
      this.updateOperation(operationId, { 
        status: result.success ? 'completed' : 'failed',
        error: result.error
      });

      // Add to history
      this.addToHistory(operation);

      // Track execution for test verification
      this.operationExecutionHistory.push({
        type,
        threadId,
        options,
        result
      });

      return result;
    } catch (error) {
      const errorObj = error as Error;
      
      this.updateOperation(operationId, { 
        status: 'failed',
        error: errorObj
      });

      this.addToHistory(operation);

      const result = {
        success: false,
        error: errorObj
      };

      this.operationExecutionHistory.push({
        type,
        threadId,
        options,
        result
      });

      return result;
    } finally {
      // Clear current operation if it matches
      if (this.currentOperation?.id === operationId) {
        this.currentOperation = null;
      }
    }
  }

  public async cancelCurrentOperation(): Promise<void> {
    if (!this.currentOperation) return;
    
    const operation = this.currentOperation;
    
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
  }

  public isOperationInProgress(type?: ThreadOperationType, threadId?: string): boolean {
    if (!this.currentOperation) return false;
    
    if (type && this.currentOperation.type !== type) return false;
    if (threadId && this.currentOperation.threadId !== threadId) return false;
    
    return this.currentOperation.status === 'running';
  }

  public getCurrentOperation(): ThreadOperation | null {
    return this.currentOperation;
  }

  public getOperationHistory(): ReadonlyArray<ThreadOperation> {
    return [...this.operationHistory];
  }

  public clearHistory(): void {
    this.operationHistory = [];
    this.operationExecutionHistory = [];
  }

  public addListener(listener: ThreadOperationListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  // Test helper methods
  public getExecutionHistory() {
    return [...this.operationExecutionHistory];
  }

  public getLastExecution() {
    return this.operationExecutionHistory[this.operationExecutionHistory.length - 1];
  }

  public reset() {
    this.currentOperation = null;
    this.operationHistory = [];
    this.listeners.clear();
    this.operationExecutionHistory = [];
  }

  private generateOperationId(type: ThreadOperationType, threadId: string | null): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substr(2, 9);
    return `${type}_${threadId || 'new'}_${timestamp}_${random}`;
  }

  private updateOperation(id: string, updates: Partial<ThreadOperation>): void {
    if (this.currentOperation?.id === id) {
      this.currentOperation = { ...this.currentOperation, ...updates };
      this.notifyListeners(this.currentOperation);
    }
  }

  private addToHistory(operation: ThreadOperation): void {
    this.operationHistory.unshift(operation);
    
    // Trim history if too large
    const MAX_HISTORY_SIZE = 50;
    if (this.operationHistory.length > MAX_HISTORY_SIZE) {
      this.operationHistory = this.operationHistory.slice(0, MAX_HISTORY_SIZE);
    }
  }

  private notifyListeners(operation: ThreadOperation): void {
    this.listeners.forEach(listener => {
      try {
        listener(operation);
      } catch (error) {
        console.error('Operation listener error:', error);
      }
    });
  }
}

// Create singleton mock instance
export const ThreadOperationManager = new MockThreadOperationManagerImpl();

// Hook that returns the mock
export const useThreadOperationManager = () => {
  return ThreadOperationManager;
};

// Export class for testing purposes
export { MockThreadOperationManagerImpl };