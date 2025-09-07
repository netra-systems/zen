/**
 * Diagnostic Test Suite for Thread Switching
 * 
 * Identifies specific issues causing glitchy behavior
 */

import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { render, fireEvent, screen } from '@testing-library/react';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import * as threadLoadingService from '@/services/threadLoadingService';
import { ChatSidebar } from '@/components/chat/ChatSidebar';

// Mock the unified chat store and ThreadOperationManager
jest.mock('@/store/unified-chat', () => require('../../__mocks__/store/unified-chat'));
jest.mock('@/lib/thread-operation-manager', () => require('../../__mocks__/lib/thread-operation-manager'));

// Import the mocked store
import { useUnifiedChatStore, resetMockState } from '@/store/unified-chat';
// Mock modules
jest.mock('@/services/threadLoadingService');
jest.mock('@/lib/retry-manager', () => ({
  executeWithRetry: jest.fn(async (fn) => {
    // Actually execute the function passed to it
    return await fn();
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

describe('Thread Switching Diagnostics', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset the mock store to initial state
    if (typeof resetMockState === 'function') {
      resetMockState();
    }
    
    // Reset ThreadOperationManager
    const { ThreadOperationManager } = require('@/lib/thread-operation-manager');
    if (ThreadOperationManager?.reset) {
      ThreadOperationManager.reset();
    }
  });

  describe('Race Condition Detection', () => {
    it('should handle rapid consecutive thread switches without race conditions', async () => {
      const { threadLoadingService: service } = require('@/services/threadLoadingService');
      let callCount = 0;
      
      // Simulate varying response times
      service.loadThread.mockImplementation((threadId) => {
        callCount++;
        const delay = threadId === 'thread-1' ? 100 : 50;
        return new Promise(resolve => {
          setTimeout(() => {
            resolve({
              success: true,
              threadId,
              messages: [{ id: `msg-${callCount}`, content: `Message ${callCount}` }]
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
        // Should end up on thread-3, not thread-1 (even though it has longer delay)
        expect(state.activeThreadId).toBe('thread-3');
      }, { timeout: 3000 });

      // Verify only the last thread's messages are loaded
      const finalState = useUnifiedChatStore.getState();
      expect(finalState.messages).toHaveLength(1);
      expect(finalState.messages[0].content).toContain('Message');
    });

    it('should cancel previous operations when switching threads', async () => {
      const abortSpy = jest.spyOn(AbortController.prototype, 'abort');
      const { result } = renderHook(() => useThreadSwitching());

      const { threadLoadingService: service } = require('@/services/threadLoadingService');
      service.loadThread.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({ success: true, messages: [], threadId: 'test' }), 100))
      );

      // Start first switch
      act(() => {
        result.current.switchToThread('thread-1');
      });

      // Switch to another thread before first completes
      act(() => {
        result.current.switchToThread('thread-2');
      });

      await waitFor(() => {
        expect(abortSpy).toHaveBeenCalled();
      });

      abortSpy.mockRestore();
    });
  });

  describe('State Synchronization Issues', () => {
    it('should maintain consistent state between hook and store', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      const { threadLoadingService: service } = require('@/services/threadLoadingService');
      
      service.loadThread.mockResolvedValue({
        success: true,
        threadId: 'thread-1',
        messages: [{ id: 'msg-1', content: 'Test message' }]
      });

      await act(async () => {
        await result.current.switchToThread('thread-1');
      });

      // Check hook state
      expect(result.current.state.isLoading).toBe(false);
      expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
      expect(result.current.state.error).toBeNull();

      // Check store state
      const storeState = useUnifiedChatStore.getState();
      expect(storeState.activeThreadId).toBe('thread-1');
      expect(storeState.threadLoading).toBe(false);
      expect(storeState.messages).toHaveLength(1);
    });

    it('should handle loading state transitions correctly', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      const { threadLoadingService: service } = require('@/services/threadLoadingService');
      
      let resolveLoad: any;
      service.loadThread.mockImplementation(() => 
        new Promise(resolve => { resolveLoad = resolve; })
      );

      const loadingStates: boolean[] = [];
      
      // Track loading state changes
      const unsubscribe = useUnifiedChatStore.subscribe(
        state => state.threadLoading,
        (loading) => loadingStates.push(loading)
      );

      act(() => {
        result.current.switchToThread('thread-1');
      });

      // Should start loading
      expect(result.current.state.isLoading).toBe(true);
      expect(useUnifiedChatStore.getState().threadLoading).toBe(true);

      // Complete loading
      await act(async () => {
        resolveLoad({ success: true, messages: [], threadId: 'thread-1' });
        await waitFor(() => !result.current.state.isLoading);
      });

      // Should finish loading
      expect(result.current.state.isLoading).toBe(false);
      expect(useUnifiedChatStore.getState().threadLoading).toBe(false);

      // Verify state transition sequence
      expect(loadingStates).toEqual([true, false]);
      
      unsubscribe();
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      const { threadLoadingService: service } = require('@/services/threadLoadingService');
      
      service.loadThread.mockRejectedValue(new Error('Network error'));

      const success = await act(async () => {
        return await result.current.switchToThread('thread-1');
      });

      expect(success).toBe(false);
      expect(result.current.state.error).toBeTruthy();
      expect(result.current.state.error?.message).toContain('Network error');
      
      // Should not change active thread on error
      const storeState = useUnifiedChatStore.getState();
      expect(storeState.activeThreadId).toBeNull();
    });

    it('should retry failed operations', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      const { threadLoadingService: service } = require('@/services/threadLoadingService');
      
      // First call fails
      service.loadThread.mockRejectedValueOnce(new Error('Network error'));
      
      await act(async () => {
        await result.current.switchToThread('thread-1');
      });

      expect(result.current.state.error).toBeTruthy();

      // Setup success for retry
      service.loadThread.mockResolvedValueOnce({
        success: true,
        threadId: 'thread-1',
        messages: []
      });

      const retrySuccess = await act(async () => {
        return await result.current.retryLastFailed();
      });

      expect(retrySuccess).toBe(true);
      expect(result.current.state.error).toBeNull();
      expect(useUnifiedChatStore.getState().activeThreadId).toBe('thread-1');
    });
  });

  describe('Memory Leaks and Cleanup', () => {
    it('should cleanup resources on unmount', async () => {
      const { globalCleanupManager } = require('@/lib/operation-cleanup');
      const { result, unmount } = renderHook(() => useThreadSwitching());
      
      const { threadLoadingService: service } = require('@/services/threadLoadingService');
      service.loadThread.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({ success: true, messages: [], threadId: 'test' }), 100))
      );

      act(() => {
        result.current.switchToThread('thread-1');
      });

      // Unmount while loading
      unmount();

      await waitFor(() => {
        expect(globalCleanupManager.cleanupThread).toHaveBeenCalled();
      });
    });

    it('should not accumulate event listeners', async () => {
      const { result, rerender } = renderHook(() => useThreadSwitching());
      
      // Get initial listener count
      const initialListenerCount = process.listenerCount('uncaughtException');

      // Rerender multiple times
      for (let i = 0; i < 10; i++) {
        rerender();
      }

      // Listener count should not increase
      const finalListenerCount = process.listenerCount('uncaughtException');
      expect(finalListenerCount).toBe(initialListenerCount);
    });
  });

  describe('WebSocket Integration Issues', () => {
    it('should emit correct WebSocket events during thread switch', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      const { threadLoadingService: service } = require('@/services/threadLoadingService');
      
      service.loadThread.mockResolvedValue({
        success: true,
        threadId: 'thread-1',
        messages: [{ id: 'msg-1', content: 'Test' }]
      });

      await act(async () => {
        await result.current.switchToThread('thread-1');
      });

      // Should emit loading and loaded events
      const storeState = useUnifiedChatStore.getState();
      expect(storeState.handleWebSocketEvent).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'thread_loading', threadId: 'thread-1' })
      );
      expect(storeState.handleWebSocketEvent).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'thread_loaded', threadId: 'thread-1' })
      );
    });
  });

  describe('URL Synchronization', () => {
    it('should update URL when switching threads', async () => {
      const updateUrl = jest.fn();
      jest.spyOn(require('@/services/urlSyncService'), 'useURLSync').mockReturnValue({ updateUrl });
      
      const { result } = renderHook(() => useThreadSwitching());
      const { threadLoadingService: service } = require('@/services/threadLoadingService');
      
      service.loadThread.mockResolvedValue({
        success: true,
        threadId: 'thread-1',
        messages: []
      });

      await act(async () => {
        await result.current.switchToThread('thread-1', { updateUrl: true });
      });

      expect(updateUrl).toHaveBeenCalledWith('thread-1');
    });

    it('should not update URL when skipUrlUpdate is true', async () => {
      const updateUrl = jest.fn();
      jest.spyOn(require('@/services/urlSyncService'), 'useURLSync').mockReturnValue({ updateUrl });
      
      const { result } = renderHook(() => useThreadSwitching());
      const { threadLoadingService: service } = require('@/services/threadLoadingService');
      
      service.loadThread.mockResolvedValue({
        success: true,
        threadId: 'thread-1',
        messages: []
      });

      await act(async () => {
        await result.current.switchToThread('thread-1', { skipUrlUpdate: true });
      });

      expect(updateUrl).not.toHaveBeenCalled();
    });
  });
});