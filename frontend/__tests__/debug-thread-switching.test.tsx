/**
 * Debug Thread Switching Test
 * 
 * Minimal test to debug thread switching issues
 */

import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';

// Mock the unified chat store
jest.mock('@/store/unified-chat', () => require('../__mocks__/store/unified-chat'));

// Import the mocked store
import { useUnifiedChatStore, resetMockState } from '@/store/unified-chat';

// Mock dependencies
jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: {
    loadThread: jest.fn()
  }
}));

jest.mock('@/lib/retry-manager', () => ({
  executeWithRetry: jest.fn(async (fn) => {
    console.log('executeWithRetry called with:', fn.toString());
    const result = await fn();
    console.log('executeWithRetry result:', result);
    return result;
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

jest.mock('@/lib/thread-operation-manager', () => ({
  ThreadOperationManager: {
    startOperation: jest.fn().mockImplementation(async (type, threadId, fn, options) => {
      console.log(`🔧 ThreadOperationManager.startOperation MOCK EXECUTING:`, { type, threadId });
      
      // For debugging, let's just return a simple success result without calling the executor
      console.log('🔧 Returning simple success result');
      return { success: true, threadId };
    })
  }
}));

describe('Debug Thread Switching', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset the mock store to initial state
    if (typeof resetMockState === 'function') {
      resetMockState();
    }
    
    console.log('=== BEFORE EACH ===');
    console.log('Mock store state:', useUnifiedChatStore.getState());
    console.log('Mock store functions:', Object.keys(useUnifiedChatStore.getState()));
  });

  it('should debug store and hook interaction', async () => {
    console.log('=== STARTING DEBUG TEST ===');
    
    const mockMessages = [
      { id: 'msg-1', content: 'Test message', role: 'user', timestamp: Date.now() }
    ];
    
    // Set up the mock response
    const { threadLoadingService } = require('@/services/threadLoadingService');
    threadLoadingService.loadThread.mockResolvedValue({
      success: true,
      threadId: 'thread-1',
      messages: mockMessages
    });
    
    console.log('Mock threadLoadingService.loadThread set up');

    const { result } = renderHook(() => useThreadSwitching());
    
    console.log('Hook rendered, initial state:', result.current.state);

    expect(result.current.state.isLoading).toBe(false);
    expect(result.current.state.loadingThreadId).toBeNull();

    console.log('About to call switchToThread...');
    
    let switchResult;
    let switchError;
    await act(async () => {
      try {
        console.log('🔎 Calling result.current.switchToThread...');
        switchResult = await result.current.switchToThread('thread-1');
        console.log('🔎 switchToThread returned:', switchResult);
      } catch (error) {
        console.log('🔴 switchToThread threw error:', error);
        switchError = error;
      }
    });

    console.log('switchToThread completed, result:', switchResult);
    console.log('switchToThread error:', switchError);
    console.log('Hook state after switch:', result.current.state);
    console.log('Store state after switch:', useUnifiedChatStore.getState());
    console.log('ThreadOperationManager mock calls:', require('@/lib/thread-operation-manager').ThreadOperationManager.startOperation.mock.calls);
    console.log('Loading service mock calls:', threadLoadingService.loadThread.mock.calls);
    
    if (switchError) {
      throw switchError;
    }
    
    // Check if the hook state was updated
    expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
    expect(result.current.state.isLoading).toBe(false);
    
    // Check if store state was updated
    const storeState = useUnifiedChatStore.getState();
    expect(storeState.activeThreadId).toBe('thread-1');
    expect(storeState.messages).toEqual(mockMessages);
    
    // Verify the service was called correctly
    expect(threadLoadingService.loadThread).toHaveBeenCalledWith('thread-1');
  });
});