/**
 * Simple unit test for useThreadSwitching hook
 * 
 * Tests basic hook functionality in isolation
 */

import { renderHook, act } from '@testing-library/react';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';

// Mock all dependencies
jest.mock('@/store/unified-chat', () => require('../../__mocks__/store/unified-chat'));
jest.mock('@/lib/thread-operation-manager', () => require('../../__mocks__/lib/thread-operation-manager'));

// Mock other dependencies  
jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: {
    loadThread: jest.fn().mockResolvedValue({
      success: true,
      threadId: 'test-123',
      messages: [{ id: 'msg-1', content: 'Test message' }]
    })
  }
}));

jest.mock('@/lib/retry-manager', () => ({
  executeWithRetry: jest.fn(async (fn, options) => {
    console.log('executeWithRetry called with fn:', typeof fn);
    try {
      const result = await fn();
      console.log('executeWithRetry result:', result);
      return result;
    } catch (error) {
      console.log('executeWithRetry error:', error);
      throw error;
    }
  })
}));

jest.mock('@/lib/operation-cleanup', () => ({
  globalCleanupManager: {
    registerAbortController: jest.fn(),
    cleanupThread: jest.fn()
  }
}));

jest.mock('@/services/urlSyncService', () => ({
  useURLSync: () => ({ updateUrl: jest.fn() }),
  useBrowserHistorySync: () => ({})
}));

jest.mock('@/utils/threadEventHandler', () => ({
  threadEventHandler: jest.fn(),
  createThreadLoadingEvent: jest.fn((id) => ({ type: 'thread_loading', threadId: id })),
  createThreadLoadedEvent: jest.fn((id, msgs) => ({ type: 'thread_loaded', threadId: id, messages: msgs }))
}));

jest.mock('@/utils/threadTimeoutManager', () => ({
  createThreadTimeoutManager: () => ({
    startTimeout: jest.fn(),
    clearTimeout: jest.fn()
  })
}));

jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn()
  }
}));

describe('useThreadSwitching Hook - Simple', () => {
  it('should initialize with correct state', () => {
    const { result } = renderHook(() => useThreadSwitching());

    expect(result.current.state.isLoading).toBe(false);
    expect(result.current.state.loadingThreadId).toBe(null);
    expect(result.current.state.error).toBe(null);
    expect(result.current.state.lastLoadedThreadId).toBe(null);
  });

  it('should have the required methods', () => {
    const { result } = renderHook(() => useThreadSwitching());

    expect(typeof result.current.switchToThread).toBe('function');
    expect(typeof result.current.cancelLoading).toBe('function');
    expect(typeof result.current.retryLastFailed).toBe('function');
  });

  it('should call ThreadOperationManager when switching threads', async () => {
    const { result } = renderHook(() => useThreadSwitching());
    const { ThreadOperationManager } = require('@/lib/thread-operation-manager');
    const { threadLoadingService } = require('@/services/threadLoadingService');

    const { executeWithRetry } = require('@/lib/retry-manager');
    
    ThreadOperationManager.reset();
    threadLoadingService.loadThread.mockClear();
    executeWithRetry.mockClear();

    let success;
    await act(async () => {
      success = await result.current.switchToThread('test-123');
    });

    const executions = ThreadOperationManager.getExecutionHistory();
    console.log('Executions:', executions);
    console.log('Success:', success);
    console.log('threadLoadingService.loadThread was called:', threadLoadingService.loadThread.mock.calls.length, 'times');
    console.log('executeWithRetry was called:', executeWithRetry.mock.calls.length, 'times');
    
    // Check if store functions exist
    const { useUnifiedChatStore } = require('@/store/unified-chat');
    const state = useUnifiedChatStore.getState();
    console.log('Store state has startThreadLoading?', typeof state.startThreadLoading);
    console.log('Store state has completeThreadLoading?', typeof state.completeThreadLoading);
    
    expect(executions).toHaveLength(1);
    expect(executions[0].type).toBe('switch');
    expect(executions[0].threadId).toBe('test-123');
    expect(threadLoadingService.loadThread).toHaveBeenCalledWith('test-123');
    expect(executions[0].result.success).toBe(true);
    expect(success).toBe(true);
  });
});