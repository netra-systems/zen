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

// Mock dependencies
jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: {
    loadThread: jest.fn()
  }
}));

jest.mock('@/lib/retry-manager', () => ({
  executeWithRetry: jest.fn((fn) => fn())
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
    jest.clearAllMocks();
    
    // Reset the mock store to initial state
    if (typeof resetMockState === 'function') {
      resetMockState();
    }
  });

  it('should switch to a thread successfully', async () => {
    const { threadLoadingService } = require('@/services/threadLoadingService');
    
    const mockMessages = [
      { id: 'msg-1', content: 'Test message', role: 'user', timestamp: Date.now() }
    ];
    
    threadLoadingService.loadThread.mockResolvedValue({
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

    expect(switchResult).toBe(true);
    expect(result.current.state.isLoading).toBe(false);
    expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
    
    const storeState = useUnifiedChatStore.getState();
    expect(storeState.activeThreadId).toBe('thread-1');
    expect(storeState.messages).toEqual(mockMessages);
  });

  it('should handle loading errors', async () => {
    const { threadLoadingService } = require('@/services/threadLoadingService');
    
    threadLoadingService.loadThread.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useThreadSwitching());

    let switchResult;
    await act(async () => {
      switchResult = await result.current.switchToThread('thread-1');
    });

    expect(switchResult).toBe(false);
    expect(result.current.state.error).toBeTruthy();
    expect(result.current.state.error?.message).toContain('Network error');
    
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

    // Start first switch
    act(() => {
      result.current.switchToThread('thread-1');
    });

    expect(result.current.state.isLoading).toBe(true);
    expect(result.current.state.loadingThreadId).toBe('thread-1');

    // Try second switch while first is loading - this should cancel the first
    await act(async () => {
      result.current.switchToThread('thread-2');
    });

    // The loading thread should now be thread-2 
    expect(result.current.state.loadingThreadId).toBe('thread-2');

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
    expect(result.current.state.lastLoadedThreadId).toBe('thread-2');
    expect(useUnifiedChatStore.getState().activeThreadId).toBe('thread-2');
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

    const clearMessages = useUnifiedChatStore.getState().clearMessages as jest.Mock;
    expect(clearMessages).toHaveBeenCalled();
  });

  it('should update URL when enabled', async () => {
    const { threadLoadingService } = require('@/services/threadLoadingService');
    const updateUrl = jest.fn();
    
    jest.spyOn(require('@/services/urlSyncService'), 'useURLSync').mockReturnValue({ updateUrl });
    
    threadLoadingService.loadThread.mockResolvedValue({
      success: true,
      threadId: 'thread-1',
      messages: []
    });

    const { result } = renderHook(() => useThreadSwitching());

    await act(async () => {
      await result.current.switchToThread('thread-1', { updateUrl: true });
    });

    expect(updateUrl).toHaveBeenCalledWith('thread-1');
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

    expect(retryResult).toBe(true);
    expect(result.current.state.error).toBeNull();
    expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
  });
});