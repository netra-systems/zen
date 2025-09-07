/**
 * Reproducible Test for Thread Switching State Synchronization Bug
 * 
 * This test demonstrates the exact bug where hook state and store state
 * get out of sync during thread switching operations.
 */

import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import { useUnifiedChatStore, resetMockState } from '@/store/unified-chat';

// Mock the unified chat store and ThreadOperationManager
jest.mock('@/store/unified-chat', () => require('../../__mocks__/store/unified-chat'));
jest.mock('@/lib/thread-operation-manager', () => require('../../__mocks__/lib/thread-operation-manager'));

// Mock services with specific bug-reproducing behavior
jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: {
    loadThread: jest.fn()
  }
}));

jest.mock('@/lib/retry-manager', () => ({
  executeWithRetry: jest.fn(async (fn) => await fn())
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

describe('BUG REPRODUCTION: Thread State Synchronization', () => {
  beforeEach(() => {
    // Don't use jest.clearAllMocks() as it clears mock implementations
    // Instead, reset specific mocks we need to reset
    resetMockState();
    
    // Reset ThreadOperationManager
    const { ThreadOperationManager } = require('@/lib/thread-operation-manager');
    if (ThreadOperationManager?.reset) {
      ThreadOperationManager.reset();
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

  it('BUG: Hook state and store state get out of sync', async () => {
    // Set up the bug-reproducing mock behavior
    const { threadLoadingService } = require('@/services/threadLoadingService');
    
    // This mock will return a DIFFERENT threadId than requested
    // This simulates the actual bug where the mock returns inconsistent data
    threadLoadingService.loadThread.mockImplementation((requestedThreadId) => {
      const buggyThreadId = requestedThreadId === 'thread-1' ? 'thread-2' : 'thread-1';
      return Promise.resolve({
        success: true,
        threadId: buggyThreadId,  // BUG: Returns different threadId!
        messages: [{ id: `msg-${buggyThreadId}`, content: `Message from ${buggyThreadId}` }]
      });
    });

    const { result } = renderHook(() => useThreadSwitching());

    // Attempt to switch to thread-1
    let switchResult: boolean;
    await act(async () => {
      switchResult = await result.current.switchToThread('thread-1');
    });

    // The operation should succeed from the hook's perspective
    expect(switchResult).toBe(true);
    
    // BUG REPRODUCTION: Hook state and store state are now inconsistent
    const hookState = result.current.state;
    const storeState = useUnifiedChatStore.getState();
    
    console.log('BUG DETECTED:');
    console.log('Hook lastLoadedThreadId:', hookState.lastLoadedThreadId);
    console.log('Store activeThreadId:', storeState.activeThreadId);
    
    // This should pass but will fail due to the bug
    expect(hookState.lastLoadedThreadId).toBe('thread-1'); // Will be 'thread-2'
    expect(storeState.activeThreadId).toBe('thread-1');    // Will be 'thread-2'
    expect(hookState.lastLoadedThreadId).toBe(storeState.activeThreadId); // Should be equal but won't be
  });

  it('BUG: Loading states get out of sync between hook and store', async () => {
    const { threadLoadingService } = require('@/services/threadLoadingService');
    
    let resolveLoading: any;
    threadLoadingService.loadThread.mockImplementation(() => 
      new Promise(resolve => { 
        resolveLoading = resolve; 
      })
    );

    const { result } = renderHook(() => useThreadSwitching());
    
    // Track loading state changes
    const loadingStates: Array<{hook: boolean, store: boolean}> = [];
    
    act(() => {
      result.current.switchToThread('thread-1');
    });

    // Record initial loading states
    loadingStates.push({
      hook: result.current.state.isLoading,
      store: useUnifiedChatStore.getState().threadLoading
    });

    // DEBUG: Log both states to understand the issue
    console.log('Hook isLoading:', result.current.state.isLoading);
    console.log('Store threadLoading:', useUnifiedChatStore.getState().threadLoading);
    console.log('Hook loadingThreadId:', result.current.state.loadingThreadId);
    console.log('Store activeThreadId:', useUnifiedChatStore.getState().activeThreadId);

    // BUG REPRODUCTION: States might not be in sync
    expect(result.current.state.isLoading).toBe(useUnifiedChatStore.getState().threadLoading);
    
    // Complete the loading
    await act(async () => {
      resolveLoading({ success: true, messages: [], threadId: 'thread-1' });
      await waitFor(() => !result.current.state.isLoading);
    });

    // Record final loading states
    loadingStates.push({
      hook: result.current.state.isLoading,
      store: useUnifiedChatStore.getState().threadLoading
    });

    // Both should be false now, but might not be due to race conditions
    expect(result.current.state.isLoading).toBe(false);
    expect(useUnifiedChatStore.getState().threadLoading).toBe(false);
    expect(result.current.state.isLoading).toBe(useUnifiedChatStore.getState().threadLoading);
  });

  it('BUG: Rapid thread switching causes state confusion', async () => {
    const { threadLoadingService } = require('@/services/threadLoadingService');
    
    // Mock varying response times to simulate race conditions
    threadLoadingService.loadThread.mockImplementation((threadId) => {
      const delay = threadId === 'thread-1' ? 100 : 50;
      return new Promise(resolve => {
        setTimeout(() => {
          resolve({
            success: true,
            threadId,
            messages: [{ id: `msg-${threadId}`, content: `Message from ${threadId}` }]
          });
        }, delay);
      });
    });

    const { result } = renderHook(() => useThreadSwitching());

    // Rapidly switch between threads
    act(() => {
      result.current.switchToThread('thread-1');
      result.current.switchToThread('thread-2');
      result.current.switchToThread('thread-3');
    });

    await waitFor(() => {
      const state = useUnifiedChatStore.getState();
      expect(state.threadLoading).toBe(false);
    }, { timeout: 3000 });
    
    // CRITICAL: Also wait for hook state to be properly updated
    // React setState is async, so we need to wait for the hook to reflect the final thread
    await waitFor(() => {
      expect(result.current.state.lastLoadedThreadId).toBe('thread-3');
    }, { timeout: 1000 });

    // BUG REPRODUCTION: Final state should be thread-3 consistently
    const finalHookState = result.current.state;
    const finalStoreState = useUnifiedChatStore.getState();
    
    console.log('RAPID SWITCHING BUG:');
    console.log('Hook lastLoadedThreadId:', finalHookState.lastLoadedThreadId);
    console.log('Store activeThreadId:', finalStoreState.activeThreadId);
    
    // Should both be 'thread-3' but might be different due to race conditions
    expect(finalHookState.lastLoadedThreadId).toBe('thread-3');
    expect(finalStoreState.activeThreadId).toBe('thread-3');
    expect(finalHookState.lastLoadedThreadId).toBe(finalStoreState.activeThreadId);
  });
});