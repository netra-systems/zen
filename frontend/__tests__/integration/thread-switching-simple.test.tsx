/**
 * Simple Thread Switching Test
 * Tests basic thread switching functionality
 */

import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';

// Mock the unified chat store
jest.mock('@/store/unified-chat', () => require('../../__mocks__/store/unified-chat'));

// Import the mocked store
import { useUnifiedChatStore, resetMockState } from '@/store/unified-chat';
import { threadLoadingService } from '@/services/threadLoadingService';

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

describe('Thread Switching Basic Tests', () => {
  beforeEach(() => {
    // Don't use jest.clearAllMocks() as it clears mock implementations
    // Instead, reset specific mocks we need to reset
    
    // Reset the mock store to initial state
    if (typeof resetMockState === 'function') {
      resetMockState();
    }
    
    // Reset only the calls, not the implementation
    const { threadLoadingService } = require('@/services/threadLoadingService');
    threadLoadingService.loadThread.mockClear();
    
    // Re-set up retry manager mock implementation
    const { executeWithRetry } = require('@/lib/retry-manager');
    executeWithRetry.mockClear();
    executeWithRetry.mockImplementation(async (fn, options) => {
      const result = await fn();
      return result;
    });
  });

  it('should switch to a thread successfully', async () => {
    const mockMessages = [
      { id: 'msg-1', content: 'Test message', role: 'user', timestamp: Date.now() }
    ];
    
    // Set up the mock response
    (threadLoadingService.loadThread as jest.Mock).mockResolvedValue({
      success: true,
      threadId: 'thread-1',
      messages: mockMessages
    });

    const { result } = renderHook(() => useThreadSwitching());

    expect(result.current.state.isLoading).toBe(false);
    expect(result.current.state.loadingThreadId).toBeNull();

    let switchResult;
    await act(async () => {
      switchResult = await result.current.switchToThread('thread-1');
    });

    // Debug: Log what actually happened
    console.log('Switch result:', switchResult);
    console.log('Loading service mock calls:', (threadLoadingService.loadThread as jest.Mock).mock.calls);
    console.log('Store state:', useUnifiedChatStore.getState());

    expect(switchResult).toBe(true);
    expect(result.current.state.isLoading).toBe(false);
    expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
    
    const storeState = useUnifiedChatStore.getState();
    expect(storeState.activeThreadId).toBe('thread-1');
    expect(storeState.messages).toEqual(mockMessages);
    
    // Verify the service was called correctly
    expect(threadLoadingService.loadThread).toHaveBeenCalledWith('thread-1');
  });

  it('should handle loading errors', async () => {
    (threadLoadingService.loadThread as jest.Mock).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useThreadSwitching());

    let switchResult;
    await act(async () => {
      switchResult = await result.current.switchToThread('thread-1');
    });

    expect(switchResult).toBe(false);
    
    // Wait for error state to be set
    await waitFor(() => {
      expect(result.current.state.error).toBeTruthy();
    });
    
    // Check that error message contains expected text (may be wrapped in thread error)
    const errorMessage = result.current.state.error?.message || '';
    expect(errorMessage).toMatch(/Thread loading failed|Network error/);
    
    const storeState = useUnifiedChatStore.getState();
    expect(storeState.activeThreadId).toBeNull(); // Should not change on error
  });

  it('should prevent concurrent switches', async () => {
    const { threadLoadingService } = require('@/services/threadLoadingService');
    
    const resolvers: { [key: string]: any } = {};
    
    threadLoadingService.loadThread.mockImplementation((threadId: string) => {
      return new Promise(resolve => { 
        resolvers[threadId] = resolve; 
      });
    });

    const { result } = renderHook(() => useThreadSwitching());

    // Start first switch and wait for loading state
    await act(async () => {
      result.current.switchToThread('thread-1');
      // Give operation a chance to start
      await new Promise(resolve => setTimeout(resolve, 0));
    });

    // Wait for loading state to be set
    await waitFor(() => {
      expect(result.current.state.isLoading).toBe(true);
      expect(result.current.state.loadingThreadId).toBe('thread-1');
    });

    // Try second switch while first is loading - this should cancel the first
    await act(async () => {
      result.current.switchToThread('thread-2');
      // Give operation a chance to start
      await new Promise(resolve => setTimeout(resolve, 0));
    });

    // Wait for the loading thread to change to thread-2 
    await waitFor(() => {
      expect(result.current.state.loadingThreadId).toBe('thread-2');
    });

    // Resolve the second switch
    await act(async () => {
      if (resolvers['thread-2']) {
        resolvers['thread-2']({
          success: true,
          threadId: 'thread-2',
          messages: []
        });
      }
      await waitFor(() => !result.current.state.isLoading);
    });

    // Should end up on thread-2
    await waitFor(() => {
      expect(result.current.state.lastLoadedThreadId).toBe('thread-2');
      expect(useUnifiedChatStore.getState().activeThreadId).toBe('thread-2');
    });
  });

  it('should clear messages when requested', async () => {
    const { threadLoadingService } = require('@/services/threadLoadingService');
    
    // Set initial messages
    useUnifiedChatStore.setState({
      messages: [
        { id: 'old-1', content: 'Old message', role: 'user', timestamp: Date.now() }
      ]
    });

    threadLoadingService.loadThread.mockResolvedValue({
      success: true,
      threadId: 'thread-1',
      messages: [
        { id: 'new-1', content: 'New message', role: 'user', timestamp: Date.now() }
      ]
    });

    const { result } = renderHook(() => useThreadSwitching());

    await act(async () => {
      await result.current.switchToThread('thread-1', { clearMessages: true });
    });

    // Wait for state to stabilize
    await waitFor(() => {
      const clearMessages = useUnifiedChatStore.getState().clearMessages as jest.Mock;
      expect(clearMessages).toHaveBeenCalled();
    });
  });

  it('should update URL when enabled', async () => {
    const { threadLoadingService } = require('@/services/threadLoadingService');
    const updateUrl = jest.fn();
    
    // Mock the urlSyncService at the module level
    const urlSyncModule = require('@/services/urlSyncService');
    jest.spyOn(urlSyncModule, 'useURLSync').mockReturnValue({ updateUrl });
    
    threadLoadingService.loadThread.mockResolvedValue({
      success: true,
      threadId: 'thread-1',
      messages: []
    });

    const { result } = renderHook(() => useThreadSwitching());

    await act(async () => {
      await result.current.switchToThread('thread-1', { updateUrl: true });
    });

    // Wait for the URL update to be called
    await waitFor(() => {
      expect(updateUrl).toHaveBeenCalledWith('thread-1');
    });
  });

  it('should handle retry after failure', async () => {
    const { threadLoadingService } = require('@/services/threadLoadingService');
    
    // First attempt fails
    threadLoadingService.loadThread.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useThreadSwitching());

    await act(async () => {
      await result.current.switchToThread('thread-1');
    });

    expect(result.current.state.error).toBeTruthy();

    // Setup success for retry
    threadLoadingService.loadThread.mockResolvedValueOnce({
      success: true,
      threadId: 'thread-1',
      messages: []
    });

    let retryResult;
    await act(async () => {
      retryResult = await result.current.retryLastFailed();
    });

    // Wait for state to stabilize
    await waitFor(() => {
      expect(result.current.state.error).toBeNull();
    });

    expect(retryResult).toBe(true);
    expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
  });
});