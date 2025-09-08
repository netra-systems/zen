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
  
  // Track the most recent successful operation to prevent out-of-order completions
  private lastCompletedOperationTime: number = 0;
  private lastCompletedThreadId: string | null = null;
  
  // High-resolution sequence counter for operations that happen in the same millisecond
  private operationSequence: number = 0;

  /**
   * Mock implementation that actually executes the provided executor function
   * and properly simulates store state updates for tests
   */
  public async startOperation(
    type: ThreadOperationType,
    threadId: string | null,
    executor: (signal: AbortSignal) => Promise<ThreadOperationResult>,
    options: ThreadOperationOptions = {}
  ): Promise<ThreadOperationResult> {
    const operationId = this.generateOperationId(type, threadId);
    
    // Cancel any existing operation if not the same thread or if force is enabled
    if (this.currentOperation && (this.currentOperation.threadId !== threadId || options.force)) {
      await this.cancelCurrentOperation();
    }
    
    // CRITICAL: Also abort any operations for different threads that might still be running
    // This handles the race condition where multiple operations start simultaneously
    if (threadId !== this.currentOperation?.threadId) {
      // Mark any previous operations for this thread as superseded
      this.operationHistory.forEach(op => {
        if (op.threadId !== threadId && op.status === 'running' && op.abortController) {
          op.abortController.abort();
        }
      });
    }
    
    // Create operation with high-resolution sequence number
    const startTime = Date.now() + (this.operationSequence++);
    const operation: ThreadOperation = {
      id: operationId,
      type,
      threadId,
      startTime,
      status: 'pending',
      abortController: new AbortController()
    };

    // console.log(`ThreadOperationManager: Starting operation ${operationId} for ${threadId} at ${operation.startTime} (seq: ${this.operationSequence - 1})`);

    // Set as current operation
    this.currentOperation = operation;
    this.updateOperation(operationId, { status: 'running' });
    
    // Add to history immediately so newer operations can check against it
    this.addToHistory(operation);
    
    // Note: Store state updates are handled by the hook's executor function itself

    try {
      // CRITICAL PRE-CHECK: Before executing, check if this operation is already superseded
      // This prevents any store updates from happening for superseded operations
      const checkForNewerOperations = () => {
        const newerOperations = this.operationHistory.filter(op => 
          op.id !== operationId && 
          op.startTime > operation.startTime
        );
        
        return newerOperations.some(op => 
          op.status === 'pending' || op.status === 'running' || op.status === 'completed'
        );
      };
      
      // Enhanced executor that checks for superseded operations before allowing updates
      const safeExecutor = async (signal: AbortSignal) => {
        // Double-check for superseded operations just before execution
        if (checkForNewerOperations()) {
          console.log(`Operation ${operationId} for ${threadId} superseded before execution, aborting`);
          return { success: false, threadId, error: new Error('Operation superseded before execution') };
        }
        
        return await executor(signal);
      };
      
      // Actually execute the provided function
      const result = await safeExecutor(operation.abortController!.signal);
      
      // Check if operation was aborted during execution
      if (operation.abortController!.signal.aborted) {
        this.updateOperation(operationId, { 
          status: 'cancelled',
          error: new Error('Operation aborted during execution')
        });
        return { success: false, error: new Error('Operation aborted during execution') };
      }
      
      // CRITICAL FINAL CHECK: After execution, check again for superseded operations
      // This catches operations that became superseded during execution
      if (result.success && checkForNewerOperations()) {
        console.log(`Operation for ${threadId} (${operationId}) completed but was superseded during execution, not updating state`);
        this.updateOperation(operationId, { 
          status: 'cancelled',
          error: new Error('Operation superseded during execution')
        });
        return { success: false, threadId, error: new Error('Operation superseded') };
      }
      
      // Update operation status based on result
      this.updateOperation(operationId, { 
        status: result.success ? 'completed' : 'failed',
        error: result.error
      });
      
      // If successful, update the completion tracking
      if (result.success) {
        this.lastCompletedOperationTime = Date.now();
        this.lastCompletedThreadId = threadId;
      }

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
    this.lastCompletedOperationTime = 0;
    this.lastCompletedThreadId = null;
    this.operationSequence = 0;
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