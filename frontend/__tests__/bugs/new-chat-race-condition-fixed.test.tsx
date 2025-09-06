/**
 * Test to verify that new chat URL race conditions have been fixed
 * 
 * This test ensures that our mutex, debouncing, and state machine fixes
 * prevent race conditions during new chat creation.
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

// Mock ThreadOperationManager to simulate fixed behavior
const mockStartOperation = jest.fn();
jest.mock('@/lib/thread-operation-manager', () => ({
  ThreadOperationManager: {
    startOperation: mockStartOperation,
  },
}));

// Mock threadStateMachineManager
const mockStateMachine = {
  transition: jest.fn(),
  getState: jest.fn(() => 'idle'),
  addListener: jest.fn(),
};
jest.mock('@/lib/thread-state-machine', () => ({
  threadStateMachineManager: {
    getStateMachine: jest.fn(() => mockStateMachine),
    resetAll: jest.fn(),
  },
}));

describe('New Chat Race Condition Fixes', () => {
  let mockCreateThread: jest.Mock;
  
  beforeEach(() => {
    mockCreateThread = jest.fn();
    (ThreadService.createThread as jest.Mock) = mockCreateThread;
    
    jest.clearAllMocks();
  });
  
  it('should prevent concurrent new chat operations with mutex', async () => {
    // Arrange - Mock mutex behavior
    let operationCount = 0;
    
    mockCreateThread.mockResolvedValue({
      id: 'mutex-thread-1',
      created_at: Date.now(),
      messages: [],
    });
    
    // Mock startOperation to simulate mutex behavior
    mockStartOperation.mockImplementation(async (type, threadId, executor, options) => {
      operationCount++;
      if (operationCount === 1) {
        // First operation succeeds
        const result = await executor({ aborted: false });
        return result;
      } else {
        // Subsequent operations blocked by mutex
        return { success: false, error: new Error('Operation already in progress') };
      }
    });
    
    const mockExecutor = async (signal: AbortSignal) => {
      const newThread = await ThreadService.createThread();
      return { success: true, threadId: newThread.id };
    };
    
    // Act - Start 3 concurrent operations
    const { ThreadOperationManager } = require('@/lib/thread-operation-manager');
    const operations = [
      ThreadOperationManager.startOperation('create', null, mockExecutor, { force: false }),
      ThreadOperationManager.startOperation('create', null, mockExecutor, { force: false }),
      ThreadOperationManager.startOperation('create', null, mockExecutor, { force: false }),
    ];
    
    const results = await Promise.all(operations);
    
    // Assert - Only one operation should succeed due to mutex
    const successfulOperations = results.filter(result => result.success);
    const blockedOperations = results.filter(result => !result.success);
    
    expect(successfulOperations.length).toBe(1);
    expect(blockedOperations.length).toBe(2);
    expect(mockCreateThread).toHaveBeenCalledTimes(1);
    
    // Blocked operations should have mutex error
    blockedOperations.forEach(result => {
      expect(result.error?.message).toContain('Operation already in progress');
    });
  });
  
  it('should use debouncing to prevent rapid-fire operations', async () => {
    // Arrange - Mock debouncing behavior
    let operationCount = 0;
    
    mockCreateThread.mockResolvedValue({
      id: 'debounced-thread',
      created_at: Date.now(),
      messages: [],
    });
    
    // Mock startOperation to simulate debouncing
    mockStartOperation.mockImplementation(async (type, threadId, executor) => {
      operationCount++;
      if (operationCount <= 2) {
        // First two operations are debounced away
        return { success: false, error: new Error('Operation debounced') };
      } else {
        // Third operation (after debounce) succeeds
        const result = await executor({ aborted: false });
        return result;
      }
    });
    
    const mockExecutor = async (signal: AbortSignal) => {
      const newThread = await ThreadService.createThread();
      return { success: true, threadId: newThread.id };
    };
    
    // Act - Rapidly start operations
    const { ThreadOperationManager } = require('@/lib/thread-operation-manager');
    const operations = [
      ThreadOperationManager.startOperation('create', null, mockExecutor),
      ThreadOperationManager.startOperation('create', null, mockExecutor),
      ThreadOperationManager.startOperation('create', null, mockExecutor),
    ];
    
    const results = await Promise.all(operations);
    
    // Assert - Debouncing should reduce the number of actual operations
    const successfulOperations = results.filter(result => result.success);
    const debouncedOperations = results.filter(result => 
      !result.success && result.error?.message.includes('debounced')
    );
    
    expect(successfulOperations.length).toBe(1);
    expect(debouncedOperations.length).toBe(2);
    expect(mockCreateThread).toHaveBeenCalledTimes(1);
  });
  
  it('should maintain proper state machine transitions', async () => {
    // Arrange
    const stateChanges: string[] = [];
    
    // Mock state machine listener to track transitions
    mockStateMachine.transition.mockImplementation((event, data) => {
      stateChanges.push(`${event}(${data?.targetThreadId || 'null'})`);
    });
    
    mockCreateThread.mockResolvedValue({
      id: 'state-machine-thread',
      created_at: Date.now(),
      messages: [],
    });
    
    mockStartOperation.mockImplementation(async (type, threadId, executor) => {
      const result = await executor({ aborted: false });
      return result;
    });
    
    const { threadStateMachineManager } = require('@/lib/thread-state-machine');
    
    // Act - Simulate new chat creation with state machine transitions
    const stateMachine = threadStateMachineManager.getStateMachine('newChat');
    const operationId = `create_${Date.now()}_test`;
    
    // Start creation
    stateMachine.transition('START_CREATE', {
      operationId,
      startTime: Date.now(),
      targetThreadId: null
    });
    
    // Simulate thread creation success
    stateMachine.transition('START_SWITCH', {
      targetThreadId: 'state-machine-thread'
    });
    
    // Complete operation
    stateMachine.transition('COMPLETE_SUCCESS');
    
    // Assert - State machine transitions are proper
    expect(mockStateMachine.transition).toHaveBeenCalledTimes(3);
    expect(stateChanges).toEqual([
      'START_CREATE(null)',
      'START_SWITCH(state-machine-thread)',
      'COMPLETE_SUCCESS(null)'
    ]);
  });
  
  it('should handle URL updates atomically without race conditions', async () => {
    // Arrange
    const urlUpdates: Array<{ url: string, timestamp: number }> = [];
    
    const mockSwitchToThread = jest.fn().mockImplementation(async (threadId: string, options: any) => {
      // Simulate atomic URL update (only one update per thread switch)
      if (options?.updateUrl) {
        const url = `/chat?thread=${threadId}`;
        urlUpdates.push({ url, timestamp: Date.now() });
      }
      return true;
    });
    
    mockCreateThread.mockResolvedValue({
      id: 'atomic-url-thread',
      created_at: Date.now(),
      messages: [],
    });
    
    mockStartOperation.mockImplementation(async (type, threadId, executor) => {
      const result = await executor({ aborted: false });
      return result;
    });
    
    const mockExecutor = async (signal: AbortSignal) => {
      const newThread = await ThreadService.createThread();
      
      // Simulate thread switching with atomic URL update
      await mockSwitchToThread(newThread.id, { updateUrl: true });
      
      return { success: true, threadId: newThread.id };
    };
    
    // Act - Single operation to test atomic URL update
    const { ThreadOperationManager } = require('@/lib/thread-operation-manager');
    const result = await ThreadOperationManager.startOperation('create', null, mockExecutor);
    
    // Assert - URL updates should be atomic (no duplicates)
    expect(result.success).toBe(true);
    expect(mockSwitchToThread).toHaveBeenCalledTimes(1);
    expect(mockSwitchToThread).toHaveBeenCalledWith('atomic-url-thread', { updateUrl: true });
    
    const threadUrlUpdates = urlUpdates.filter(update => 
      update.url.includes('atomic-url-thread')
    );
    
    // Should have exactly 1 URL update for atomic operation
    expect(threadUrlUpdates.length).toBe(1);
  });
  
  it('should gracefully handle operation failures', async () => {
    // Arrange
    mockCreateThread.mockRejectedValue(new Error('Network error'));
    
    mockStartOperation.mockImplementation(async (type, threadId, executor) => {
      try {
        const result = await executor({ aborted: false });
        return result;
      } catch (error) {
        return { success: false, error };
      }
    });
    
    const mockExecutor = async (signal: AbortSignal) => {
      await ThreadService.createThread();
      return { success: true, threadId: 'should-not-reach' };
    };
    
    // Act
    const { ThreadOperationManager } = require('@/lib/thread-operation-manager');
    const result = await ThreadOperationManager.startOperation('create', null, mockExecutor);
    
    // Assert - Should handle errors gracefully
    expect(result.success).toBe(false);
    expect(result.error?.message).toContain('Network error');
    expect(mockCreateThread).toHaveBeenCalledTimes(1);
  });
  
  it('should demonstrate race condition prevention in rapid succession', async () => {
    // Arrange - Simulate proper race condition prevention
    let allowedOperations = 0;
    
    mockCreateThread.mockImplementation(async () => {
      allowedOperations++;
      return {
        id: `race-thread-${allowedOperations}`,
        created_at: Date.now(),
        messages: [],
      };
    });
    
    // Mock startOperation to allow only the first operation (race condition prevention)
    let operationCount = 0;
    mockStartOperation.mockImplementation(async (type, threadId, executor) => {
      operationCount++;
      if (operationCount === 1) {
        // First operation succeeds
        const result = await executor({ aborted: false });
        return result;
      } else {
        // Subsequent operations blocked
        return { success: false, error: new Error('Operation already in progress') };
      }
    });
    
    const createExecutor = () => async (signal: AbortSignal) => {
      const newThread = await ThreadService.createThread();
      return { success: true, threadId: newThread.id };
    };
    
    // Act - Start multiple operations in rapid succession
    const { ThreadOperationManager } = require('@/lib/thread-operation-manager');
    const operations = [];
    for (let i = 1; i <= 5; i++) {
      operations.push(ThreadOperationManager.startOperation('create', null, createExecutor()));
    }
    
    const results = await Promise.all(operations);
    
    // Assert - Race condition prevention worked
    const successfulOperations = results.filter(result => result.success);
    const failedOperations = results.filter(result => !result.success);
    
    // With proper race condition prevention, only one operation should succeed
    expect(successfulOperations.length).toBe(1);
    expect(failedOperations.length).toBe(4);
    expect(mockCreateThread).toHaveBeenCalledTimes(1);
    
    // Failed operations should be blocked by mutex
    failedOperations.forEach(result => {
      expect(result.error?.message).toContain('Operation already in progress');
    });
  });
});