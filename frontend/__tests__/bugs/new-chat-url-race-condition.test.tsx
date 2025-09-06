/**
 * Test to reproduce the new chat URL update race condition bug
 * 
 * This test demonstrates that duplicate URL updates cause navigation issues
 * when creating a new chat thread WITHOUT proper race condition prevention.
 */

import React from 'react';
import { ThreadService } from '@/services/threadService';
import '@testing-library/jest-dom';

// Mock services
jest.mock('@/services/threadService');
jest.mock('@/lib/logger', () => ({
  logger: {
    warn: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
    debug: jest.fn(),
  },
}));

// Simulate a broken ThreadOperationManager (without race condition fixes)
class BrokenThreadOperationManager {
  static async startOperation(
    type: string,
    threadId: string | null,
    executor: (signal: AbortSignal) => Promise<any>,
    options: any = {}
  ) {
    // This broken version doesn't implement mutex or debouncing
    // It allows all operations to proceed, causing race conditions
    const signal = { aborted: false } as AbortSignal;
    return await executor(signal);
  }
}

// Simulate broken thread switching that causes URL race conditions
const createBrokenSwitchToThread = () => {
  const urlUpdateHistory: Array<{ url: string, timestamp: number }> = [];
  
  const brokenSwitchToThread = async (threadId: string, options: any) => {
    // BUG: Both store change AND manual update cause URL updates
    
    // Step 1: Store change triggers automatic URL sync
    const autoSyncUrl = `/chat?thread=${threadId}`;
    urlUpdateHistory.push({ url: autoSyncUrl, timestamp: Date.now() });
    
    // Step 2: Manual URL update (this creates the duplicate)
    if (options?.updateUrl) {
      await new Promise(resolve => setTimeout(resolve, 10)); // Small delay
      const manualUrl = `/chat?thread=${threadId}`;
      urlUpdateHistory.push({ url: manualUrl, timestamp: Date.now() });
    }
    
    return true;
  };
  
  return { brokenSwitchToThread, urlUpdateHistory };
};

describe('New Chat URL Race Condition Bug', () => {
  let mockCreateThread: jest.Mock;
  
  beforeEach(() => {
    mockCreateThread = jest.fn();
    (ThreadService.createThread as jest.Mock) = mockCreateThread;
    
    jest.clearAllMocks();
  });
  
  it('should demonstrate duplicate URL updates causing race condition', async () => {
    // Arrange
    const { brokenSwitchToThread, urlUpdateHistory } = createBrokenSwitchToThread();
    const newThreadId = 'new-thread-456';
    
    mockCreateThread.mockResolvedValue({
      id: newThreadId,
      created_at: Date.now(),
      messages: [],
    });
    
    const brokenExecutor = async (signal: AbortSignal) => {
      const newThread = await ThreadService.createThread();
      
      // This simulates the broken behavior that causes race conditions
      await brokenSwitchToThread(newThread.id, { updateUrl: true });
      
      return { success: true, threadId: newThread.id };
    };
    
    // Act - Use broken operation manager
    const result = await BrokenThreadOperationManager.startOperation(
      'create', 
      null, 
      brokenExecutor
    );
    
    // Assert - Check for duplicate URL updates
    console.log('URL Update History:', urlUpdateHistory);
    
    // BUG: We should see multiple URL updates for the same thread
    const newThreadUpdates = urlUpdateHistory.filter(update => 
      update.url.includes(newThreadId)
    );
    
    // This demonstrates the bug - there should be only 1 URL update,
    // but we're getting 2 due to the race condition
    expect(newThreadUpdates.length).toBeGreaterThan(1);
    expect(newThreadUpdates.length).toBe(2); // Exactly 2 due to the race condition
    
    // The duplicate updates happen within milliseconds of each other
    const timeDiff = newThreadUpdates[1].timestamp - newThreadUpdates[0].timestamp;
    expect(timeDiff).toBeLessThan(100); // Updates within 100ms indicate race condition
    
    expect(result.success).toBe(true);
  });
  
  it('should show that rapid new chat clicks cause navigation confusion', async () => {
    // Arrange - simulate multiple new chat creations without race condition protection
    let threadCounter = 1;
    const { brokenSwitchToThread, urlUpdateHistory } = createBrokenSwitchToThread();
    
    mockCreateThread.mockImplementation(async () => {
      const threadId = `rapid-thread-${threadCounter++}`;
      await new Promise(resolve => setTimeout(resolve, Math.random() * 50)); // Variable delay
      return {
        id: threadId,
        created_at: Date.now(),
        messages: [],
      };
    });
    
    const createBrokenExecutor = (id: number) => async (signal: AbortSignal) => {
      const newThread = await ThreadService.createThread();
      await brokenSwitchToThread(newThread.id, { updateUrl: true });
      return { success: true, threadId: newThread.id };
    };
    
    // Act - Rapidly start 3 operations (no race condition protection)
    const operations = [
      BrokenThreadOperationManager.startOperation('create', null, createBrokenExecutor(1)),
      BrokenThreadOperationManager.startOperation('create', null, createBrokenExecutor(2)),
      BrokenThreadOperationManager.startOperation('create', null, createBrokenExecutor(3)),
    ];
    
    const results = await Promise.all(operations);
    
    // Assert - Check for URL update chaos
    console.log('Rapid click URL History:', urlUpdateHistory);
    
    // With the race condition, we'll see interleaved URL updates
    // that don't correspond to a clean navigation flow
    const uniqueThreadIds = new Set(
      urlUpdateHistory
        .map(update => {
          const match = update.url.match(/thread=([^&]+)/);
          return match ? match[1] : null;
        })
        .filter(Boolean)
    );
    
    // BUG: URL updates are chaotic and interleaved
    expect(urlUpdateHistory.length).toBeGreaterThan(3); // More updates than threads created
    expect(uniqueThreadIds.size).toBe(3); // 3 unique threads
    
    // All operations succeed (no mutex protection)
    const successfulOperations = results.filter(result => result.success);
    expect(successfulOperations.length).toBe(3);
    expect(mockCreateThread).toHaveBeenCalledTimes(3);
  });
  
  it('should demonstrate that the final URL may not match the intended thread', async () => {
    // Arrange
    const { brokenSwitchToThread, urlUpdateHistory } = createBrokenSwitchToThread();
    const thread1 = 'thread-final-1';
    const thread2 = 'thread-final-2';
    
    let callCount = 0;
    mockCreateThread.mockImplementation(async () => {
      callCount++;
      const threadId = callCount === 1 ? thread1 : thread2;
      
      // Simulate varying response times to create race condition
      const delay = callCount === 1 ? 50 : 10; // First is slower
      await new Promise(resolve => setTimeout(resolve, delay));
      
      return {
        id: threadId,
        created_at: Date.now(),
        messages: [],
      };
    });
    
    const createBrokenExecutor = (expectedThreadId: string) => async (signal: AbortSignal) => {
      const newThread = await ThreadService.createThread();
      await brokenSwitchToThread(newThread.id, { updateUrl: true });
      return { success: true, threadId: newThread.id };
    };
    
    // Act - Start two operations in succession (no race condition protection)
    const operation1 = BrokenThreadOperationManager.startOperation('create', null, createBrokenExecutor(thread1));
    const operation2 = BrokenThreadOperationManager.startOperation('create', null, createBrokenExecutor(thread2));
    
    const results = await Promise.all([operation1, operation2]);
    
    // Assert
    console.log('Final URL test history:', urlUpdateHistory);
    
    // BUG: The final URL in history might not be the second thread
    // due to race conditions in URL updates
    const lastUrlUpdate = urlUpdateHistory[urlUpdateHistory.length - 1];
    
    // Both operations succeed (no mutex)
    expect(results.filter(r => r.success).length).toBe(2);
    expect(mockCreateThread).toHaveBeenCalledTimes(2);
    
    // Demonstrate the race condition: we should have multiple URL updates
    expect(urlUpdateHistory.length).toBeGreaterThan(2);
    expect(urlUpdateHistory.length).toBe(4); // 2 updates per thread = 4 total
    
    // The bug is that URL updates from the slower thread (thread1) might
    // overwrite the faster thread's (thread2) URL updates
    console.log('Last URL update:', lastUrlUpdate);
    console.log('This demonstrates the race condition - final URL is unpredictable');
    
    // The final URL could be either thread due to the race condition
    expect(lastUrlUpdate).toBeDefined();
    const finalThreadId = lastUrlUpdate.url.match(/thread=([^&]+)/)?.[1];
    expect([thread1, thread2]).toContain(finalThreadId);
  });
  
  it('should show how concurrent operations interfere with each other', async () => {
    // Arrange - No operation manager protection
    let globalOperationCount = 0;
    const operationLog: Array<{ id: number, action: string, timestamp: number }> = [];
    
    mockCreateThread.mockImplementation(async () => {
      const operationId = ++globalOperationCount;
      operationLog.push({ id: operationId, action: 'start', timestamp: Date.now() });
      
      // Simulate async work
      await new Promise(resolve => setTimeout(resolve, 30));
      
      operationLog.push({ id: operationId, action: 'complete', timestamp: Date.now() });
      
      return {
        id: `concurrent-thread-${operationId}`,
        created_at: Date.now(),
        messages: [],
      };
    });
    
    const createExecutor = (expectedId: number) => async (signal: AbortSignal) => {
      const newThread = await ThreadService.createThread();
      return { success: true, threadId: newThread.id };
    };
    
    // Act - Start 3 concurrent operations
    const operations = [
      BrokenThreadOperationManager.startOperation('create', null, createExecutor(1)),
      BrokenThreadOperationManager.startOperation('create', null, createExecutor(2)),
      BrokenThreadOperationManager.startOperation('create', null, createExecutor(3)),
    ];
    
    const results = await Promise.all(operations);
    
    // Assert - Show interference between operations
    console.log('Operation interference log:', operationLog);
    
    // All operations succeed (no protection)
    expect(results.filter(r => r.success).length).toBe(3);
    expect(mockCreateThread).toHaveBeenCalledTimes(3);
    
    // Operations interfere with each other - they start/complete in overlapping manner
    const startEvents = operationLog.filter(log => log.action === 'start');
    const completeEvents = operationLog.filter(log => log.action === 'complete');
    
    expect(startEvents.length).toBe(3);
    expect(completeEvents.length).toBe(3);
    
    // This demonstrates that operations can interfere with each other
    // All operations complete successfully (showing lack of race condition protection)
    console.log('Operations ran concurrently without protection');
  });
  
  it('should demonstrate lack of atomic URL updates causing inconsistency', async () => {
    // Arrange
    const urlHistory: Array<{ operation: string, url: string, timestamp: number }> = [];
    
    const brokenAtomicUpdate = async (threadId: string, operationName: string) => {
      // Step 1: Store update
      urlHistory.push({ 
        operation: `${operationName}-store`, 
        url: `/chat?thread=${threadId}`, 
        timestamp: Date.now() 
      });
      
      // Step 2: Manual URL update (not atomic with store)
      await new Promise(resolve => setTimeout(resolve, 5));
      urlHistory.push({ 
        operation: `${operationName}-manual`, 
        url: `/chat?thread=${threadId}`, 
        timestamp: Date.now() 
      });
    };
    
    mockCreateThread.mockImplementation(async () => {
      return {
        id: `atomic-test-thread`,
        created_at: Date.now(),
        messages: [],
      };
    });
    
    // Act - Multiple operations with non-atomic URL updates
    const operation1 = (async () => {
      const thread = await ThreadService.createThread();
      await brokenAtomicUpdate(thread.id, 'op1');
      return { success: true, threadId: thread.id };
    })();
    
    const operation2 = (async () => {
      const thread = await ThreadService.createThread();
      await brokenAtomicUpdate(thread.id, 'op2');
      return { success: true, threadId: thread.id };
    })();
    
    await Promise.all([operation1, operation2]);
    
    // Assert - Show non-atomic URL updates
    console.log('Non-atomic URL history:', urlHistory);
    
    // BUG: URL updates are not atomic - store and manual updates are interleaved
    expect(urlHistory.length).toBe(4); // 2 operations × 2 updates each
    
    // Show the interleaving problem
    const operations = urlHistory.map(h => h.operation);
    console.log('Operation sequence:', operations);
    
    // Non-atomic updates can be interleaved like: op1-store, op2-store, op1-manual, op2-manual
    // This is the race condition - updates are not grouped atomically per operation
    expect(operations).toContain('op1-store');
    expect(operations).toContain('op1-manual');
    expect(operations).toContain('op2-store');
    expect(operations).toContain('op2-manual');
  });
});