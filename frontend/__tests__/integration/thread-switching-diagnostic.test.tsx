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

// DISABLE the global useThreadSwitching mock for this test
jest.unmock('@/hooks/useThreadSwitching');

// Mock the unified chat store and ThreadOperationManager
jest.mock('@/store/unified-chat', () => require('../../__mocks__/store/unified-chat'));
jest.mock('@/lib/thread-operation-manager', () => require('../../__mocks__/lib/thread-operation-manager'));

// Import the mocked store
import { useUnifiedChatStore, resetMockState } from '@/store/unified-chat';

// Mock modules - create the mock function inline
jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: {
    loadThread: jest.fn()
  }
}));
jest.mock('@/lib/retry-manager', () => ({
  executeWithRetry: jest.fn(async (fn, options) => {
    // Actually execute the function passed to it and return the result
    console.log('executeWithRetry: Executing function:', fn.toString().slice(0, 100) + '...');
    const result = await fn();
    console.log('executeWithRetry: Got result:', result);
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
    // Don't use jest.clearAllMocks() as it clears mock implementations
    // Instead, reset specific mocks we need to reset
    
    // Reset the mock store to initial state
    if (typeof resetMockState === 'function') {
      resetMockState();
    }
    
    // Reset ThreadOperationManager
    const { ThreadOperationManager } = require('@/lib/thread-operation-manager');
    if (ThreadOperationManager?.reset) {
      ThreadOperationManager.reset();
    }
    
    // Set up default mock behavior for threadLoadingService
    const { threadLoadingService } = require('@/services/threadLoadingService');
    
    // Reset only the calls, not the implementation
    threadLoadingService.loadThread.mockClear();
    threadLoadingService.loadThread.mockResolvedValue({
      success: true,
      threadId: 'default',
      messages: []
    });
    
    // Re-set up retry manager mock implementation
    const { executeWithRetry } = require('@/lib/retry-manager');
    executeWithRetry.mockClear();
    executeWithRetry.mockImplementation(async (fn, options) => {
      const result = await fn();
      return result;
    });
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
      
      // Set up the mock using require to get the mocked module
      const { threadLoadingService } = require('@/services/threadLoadingService');
      threadLoadingService.loadThread.mockResolvedValue({
        success: true,
        threadId: 'thread-1',
        messages: [{ id: 'msg-1', content: 'Test message' }]
      });

      // Wait for the thread switch to complete
      await act(async () => {
        await result.current.switchToThread('thread-1');
      });

      // Wait for state to stabilize
      await waitFor(() => {
        expect(result.current.state.isLoading).toBe(false);
        expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
      });

      // Check hook state
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

      // Start the thread switch and wait for loading state to be set
      await act(async () => {
        result.current.switchToThread('thread-1');
        // Give the promise a chance to start and set loading state
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      // Wait for loading state to be true
      await waitFor(() => {
        expect(result.current.state.isLoading).toBe(true);
        expect(useUnifiedChatStore.getState().threadLoading).toBe(true);
      });

      // Complete loading
      await act(async () => {
        resolveLoad({ success: true, messages: [], threadId: 'thread-1' });
        await waitFor(() => !result.current.state.isLoading);
      });

      // Wait for states to stabilize
      await waitFor(() => {
        expect(result.current.state.isLoading).toBe(false);
        expect(useUnifiedChatStore.getState().threadLoading).toBe(false);
      });

      // Verify state transition sequence - at minimum we should have gotten true at some point
      expect(loadingStates.some(state => state === true)).toBe(true);
      expect(loadingStates[loadingStates.length - 1]).toBe(false); // Should end with false
      
      unsubscribe();
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      const { threadLoadingService: service } = require('@/services/threadLoadingService');
      
      service.loadThread.mockRejectedValue(new Error('Network error'));

      let success: boolean = true;
      await act(async () => {
        success = await result.current.switchToThread('thread-1');
      });

      expect(success).toBe(false);
      
      // Wait for error state to be set
      await waitFor(() => {
        expect(result.current.state.error).toBeTruthy();
      });
      
      // Check that error message contains expected text (may be wrapped in thread error)
      const errorMessage = result.current.state.error?.message || '';
      expect(errorMessage).toMatch(/Thread loading failed|Network error/);
      
      // Should not change active thread on error
      const storeState = useUnifiedChatStore.getState();
      expect(storeState.activeThreadId).toBeNull();
    });

    it('should retry failed operations', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      const { threadLoadingService: service } = require('@/services/threadLoadingService');
      
      // First call fails
      service.loadThread.mockRejectedValueOnce(new Error('Network error'));
      
      // Initial failed attempt
      await act(async () => {
        await result.current.switchToThread('thread-1');
      });

      // Wait for error state
      await waitFor(() => {
        expect(result.current.state.error).toBeTruthy();
      });

      // Setup success for retry
      service.loadThread.mockResolvedValueOnce({
        success: true,
        threadId: 'thread-1',
        messages: []
      });

      let retrySuccess: boolean = false;
      await act(async () => {
        retrySuccess = await result.current.retryLastFailed();
      });

      expect(retrySuccess).toBe(true);
      
      // Wait for success state
      await waitFor(() => {
        expect(result.current.state.error).toBeNull();
        expect(useUnifiedChatStore.getState().activeThreadId).toBe('thread-1');
      });
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

      await act(async () => {
        result.current.switchToThread('thread-1');
        // Give operation a chance to start
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      // Unmount while loading
      unmount();

      // The cleanup should be called eventually (may be immediate due to unmount)
      expect(globalCleanupManager.cleanupThread).toHaveBeenCalled();
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

      // Wait for events to be emitted
      await waitFor(() => {
        const storeState = useUnifiedChatStore.getState();
        expect(storeState.handleWebSocketEvent).toHaveBeenCalledWith(
          expect.objectContaining({ type: 'thread_loading', threadId: 'thread-1' })
        );
      });
      
      await waitFor(() => {
        const storeState = useUnifiedChatStore.getState();
        expect(storeState.handleWebSocketEvent).toHaveBeenCalledWith(
          expect.objectContaining({ type: 'thread_loaded', threadId: 'thread-1' })
        );
      });
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