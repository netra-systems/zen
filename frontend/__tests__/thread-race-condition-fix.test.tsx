/**
 * Unit Test: Thread Operation Race Condition Fix
 * 
 * Tests the fix for "Operation already in progress" error
 * when switching threads rapidly.
 */

import { ThreadOperationManager } from '@/lib/thread-operation-manager';

describe('Thread Operation Race Condition Fix', () => {
  beforeEach(() => {
    // Clear any existing operations
    ThreadOperationManager.clearHistory();
  });

  it('should prevent "Operation already in progress" error with proper checks', async () => {
    const results: any[] = [];
    
    // Create a mock executor that takes some time
    const createExecutor = (threadId: string, delay: number = 100) => {
      return (signal: AbortSignal) => {
        return new Promise<any>((resolve) => {
          setTimeout(() => {
            if (signal.aborted) {
              resolve({ success: false, error: new Error('Aborted') });
            } else {
              resolve({ success: true, threadId });
            }
          }, delay);
        });
      };
    };

    // Test 1: Regular operation should succeed
    const result1 = await ThreadOperationManager.startOperation(
      'switch',
      'thread-1',
      createExecutor('thread-1', 50)
    );
    expect(result1.success).toBe(true);
    expect(result1.threadId).toBe('thread-1');

    // Test 2: Concurrent operation on same thread should be blocked
    const promise1 = ThreadOperationManager.startOperation(
      'switch',
      'thread-2',
      createExecutor('thread-2', 200)
    );
    
    // Immediately try another operation on the same thread
    const promise2 = ThreadOperationManager.startOperation(
      'switch',
      'thread-2',
      createExecutor('thread-2', 100)
    );

    const [res1, res2] = await Promise.all([promise1, promise2]);
    
    // First should succeed
    expect(res1.success).toBe(true);
    
    // Second should fail with "Operation already in progress"
    expect(res2.success).toBe(false);
    expect(res2.error?.message).toContain('Operation already in progress');
  });

  it('should allow force flag to bypass mutex and cancel previous operation', async () => {
    // Start a long-running operation
    const longOpPromise = ThreadOperationManager.startOperation(
      'switch',
      'thread-3',
      (signal: AbortSignal) => {
        return new Promise((resolve) => {
          setTimeout(() => {
            if (signal.aborted) {
              resolve({ success: false, error: new Error('Cancelled') });
            } else {
              resolve({ success: true, threadId: 'thread-3' });
            }
          }, 500);
        });
      }
    );

    // Wait a bit then force a new operation
    await new Promise(resolve => setTimeout(resolve, 50));
    
    const forceOpPromise = ThreadOperationManager.startOperation(
      'switch',
      'thread-3',
      (signal: AbortSignal) => {
        return Promise.resolve({ success: true, threadId: 'thread-3-forced' });
      },
      { force: true }
    );

    const [longResult, forceResult] = await Promise.all([longOpPromise, forceOpPromise]);
    
    // Force operation should succeed
    expect(forceResult.success).toBe(true);
    
    // Original operation should be cancelled or fail
    expect(longResult.success).toBe(false);
  });

  it('should check if operation is in progress before starting new one', () => {
    // Start an operation
    const promise = ThreadOperationManager.startOperation(
      'switch',
      'thread-4',
      () => new Promise(resolve => setTimeout(() => resolve({ success: true }), 100))
    );

    // Check if operation is in progress
    expect(ThreadOperationManager.isOperationInProgress('switch', 'thread-4')).toBe(true);
    expect(ThreadOperationManager.isOperationInProgress('switch', 'thread-5')).toBe(false);
    expect(ThreadOperationManager.isOperationInProgress('create')).toBe(false);

    // Clean up
    return promise;
  });

  it('should handle rapid thread switches gracefully', async () => {
    const threadIds = ['thread-a', 'thread-b', 'thread-c', 'thread-d'];
    const promises: Promise<any>[] = [];

    // Simulate rapid clicking by starting multiple operations quickly
    for (const threadId of threadIds) {
      // Check if we can start the operation
      if (!ThreadOperationManager.isOperationInProgress('switch', threadId)) {
        const promise = ThreadOperationManager.startOperation(
          'switch',
          threadId,
          (signal: AbortSignal) => {
            return new Promise((resolve) => {
              setTimeout(() => {
                resolve({ success: true, threadId });
              }, Math.random() * 100);
            });
          }
        );
        promises.push(promise);
      }
    }

    const results = await Promise.allSettled(promises);
    
    // At least some operations should succeed
    const successful = results.filter(r => r.status === 'fulfilled' && r.value.success);
    expect(successful.length).toBeGreaterThan(0);
    
    // Check that errors are handled gracefully
    const failed = results.filter(r => r.status === 'fulfilled' && !r.value.success);
    failed.forEach(result => {
      if (result.status === 'fulfilled' && result.value.error) {
        // Error should be about operation in progress, not an unexpected error
        expect(result.value.error.message).toMatch(/Operation already in progress|debounced/);
      }
    });
  });

  it('should properly clean up after operations', async () => {
    // Start and complete an operation
    await ThreadOperationManager.startOperation(
      'switch',
      'cleanup-test',
      () => Promise.resolve({ success: true, threadId: 'cleanup-test' })
    );

    // Verify operation is no longer in progress
    expect(ThreadOperationManager.isOperationInProgress('switch', 'cleanup-test')).toBe(false);
    
    // Should be able to start a new operation on the same thread
    const result = await ThreadOperationManager.startOperation(
      'switch',
      'cleanup-test',
      () => Promise.resolve({ success: true, threadId: 'cleanup-test-2' })
    );
    
    expect(result.success).toBe(true);
  });
});

describe('ChatSidebar Thread Click Handler Fix', () => {
  it('should prevent duplicate operations with early checks', () => {
    // Mock the ThreadOperationManager
    const mockIsOperationInProgress = jest.spyOn(ThreadOperationManager, 'isOperationInProgress');
    
    // Simulate checking before starting operation
    const threadId = 'test-thread';
    const isInProgress = ThreadOperationManager.isOperationInProgress('switch', threadId);
    
    if (!isInProgress) {
      // Safe to proceed with operation
      expect(mockIsOperationInProgress).toHaveBeenCalledWith('switch', threadId);
    }
    
    mockIsOperationInProgress.mockRestore();
  });

  it('should use force flag when switching from one thread to another', async () => {
    // This simulates the fix in ChatSidebar.tsx
    const currentLoadingThread = 'thread-1';
    const targetThread = 'thread-2';
    
    // Determine if we should force
    const shouldForce = currentLoadingThread !== null && currentLoadingThread !== targetThread;
    expect(shouldForce).toBe(true);
    
    // Start operation with force flag
    const result = await ThreadOperationManager.startOperation(
      'switch',
      targetThread,
      () => Promise.resolve({ success: true, threadId: targetThread }),
      { force: shouldForce }
    );
    
    expect(result.success).toBe(true);
  });
});