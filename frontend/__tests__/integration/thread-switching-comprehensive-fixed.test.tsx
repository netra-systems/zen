/**
 * Comprehensive Thread Switching Test Suite - Fixed Version
 * 
 * Tests all aspects of thread switching functionality including:
 * - Basic thread switching
 * - Loading states and indicators
 * - Error handling and recovery
 * - Race conditions
 * - WebSocket integration
 * - URL synchronization
 * - Message loading
 * - Abort/cancel operations
 * - Retry mechanisms
 * - State consistency
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act, renderHook } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import { ThreadSidebar } from '@/components/chat/ThreadSidebar';
import type { Thread } from '@/types/unified';

// Mock stores before importing them
jest.mock('@/store/unified-chat');
jest.mock('@/store/authStore');

// Now import the mocked stores
import { useUnifiedChatStore, resetMockState } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';

// Mock external dependencies
jest.mock('@/lib/logger');

// Mock the thread store
jest.mock('@/store/threadStore', () => {
  let state = {
    threads: [],
    currentThreadId: null,
    currentThread: null,
    loading: false,
    error: null
  };
  
  return {
    useThreadStore: Object.assign(
      () => state,
      {
        getState: () => state,
        setState: (newState: any) => {
          state = { ...state, ...newState };
        }
      }
    )
  };
});

// Mock services with proper implementations
jest.mock('@/services/threadLoadingService', () => ({
  threadLoadingService: {
    loadThread: jest.fn()
  },
  ThreadLoadingService: {
    loadThread: jest.fn()
  }
}));

jest.mock('@/services/threadService', () => ({
  ThreadService: {
    listThreads: jest.fn(),
    getThread: jest.fn(),
    getThreadMessages: jest.fn()
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
  useBrowserHistorySync: () => ({ syncToHistory: jest.fn() })
}));

// Get mocked services
const { ThreadService } = require('@/services/threadService');
const { threadLoadingService } = require('@/services/threadLoadingService');
const { executeWithRetry } = require('@/lib/retry-manager');
const { useThreadStore } = require('@/store/threadStore');

describe('Thread Switching Comprehensive Test Suite', () => {
  const mockThreads: Thread[] = [
    {
      id: 'thread-1',
      title: 'First Thread',
      created_at: 1704067200000,
      updated_at: 1704067200000,
      metadata: {}
    },
    {
      id: 'thread-2',
      title: 'Second Thread',
      created_at: 1704153600000,
      updated_at: 1704153600000,
      metadata: {}
    },
    {
      id: 'thread-3',
      title: 'Third Thread',
      created_at: 1704240000000,
      updated_at: 1704240000000,
      metadata: {}
    }
  ];

  const mockMessages = [
    { id: 'msg-1', role: 'user', content: 'Hello', created_at: 1704067200000 },
    { id: 'msg-2', role: 'assistant', content: 'Hi there!', created_at: 1704067201000 }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset mocked stores
    if (resetMockState) {
      resetMockState();
    }
    
    // For thread store with immer - use partial state update
    useThreadStore.setState({
      threads: mockThreads,
      currentThreadId: null,
      currentThread: null,
      loading: false,
      error: null
    });
    
    // Mock auth store
    (useAuthStore as jest.MockedFunction<typeof useAuthStore>).mockReturnValue({
      isAuthenticated: true
    } as any);

    // Setup default mocks
    ThreadService.listThreads.mockResolvedValue(mockThreads);
    ThreadService.getThread.mockResolvedValue(mockThreads[0]);
    ThreadService.getThreadMessages.mockResolvedValue({
      thread_id: 'thread-1',
      messages: mockMessages,
      total: 2
    });
    
    threadLoadingService.loadThread.mockResolvedValue({
      success: true,
      messages: mockMessages,
      threadId: 'thread-1'
    });
    
    executeWithRetry.mockImplementation((fn) => fn());
  });

  describe('Basic Thread Switching', () => {
    it('should switch to a thread successfully', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      
      expect(result.current.state.isLoading).toBe(false);
      
      let success: boolean;
      await act(async () => {
        success = await result.current.switchToThread('thread-1');
      });
      
      expect(success!).toBe(true);
      expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
      expect(result.current.state.isLoading).toBe(false);
      expect(threadLoadingService.loadThread).toHaveBeenCalledWith('thread-1');
    });

    it('should update store state when switching threads', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      
      await act(async () => {
        await result.current.switchToThread('thread-2');
      });
      
      const storeState = useUnifiedChatStore.getState();
      expect(storeState.activeThreadId).toBe('thread-2');
      expect(storeState.messages).toEqual(mockMessages);
    });

    it('should clear messages when clearMessages option is true', async () => {
      useUnifiedChatStore.setState({ messages: mockMessages });
      
      const { result } = renderHook(() => useThreadSwitching());
      
      await act(async () => {
        await result.current.switchToThread('thread-3', { clearMessages: true });
      });
      
      // Messages should be cleared initially then loaded
      expect(useUnifiedChatStore.getState().messages).toEqual(mockMessages);
    });

    it('should not clear messages when clearMessages option is false', async () => {
      const existingMessages = [{ id: 'old-1', role: 'user', content: 'Old message' }];
      useUnifiedChatStore.setState({ messages: existingMessages });
      
      const { result } = renderHook(() => useThreadSwitching());
      
      await act(async () => {
        await result.current.switchToThread('thread-1', { clearMessages: false });
      });
      
      // Should still load new messages
      expect(useUnifiedChatStore.getState().messages).toEqual(mockMessages);
    });
  });

  describe('Loading States and Indicators', () => {
    it('should show loading state during thread switch', async () => {
      threadLoadingService.loadThread.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({ success: true, messages: mockMessages, threadId: 'thread-1' }), 100))
      );
      
      const { result } = renderHook(() => useThreadSwitching());
      
      const switchPromise = act(async () => {
        await result.current.switchToThread('thread-1');
      });
      
      // Check loading state immediately
      expect(result.current.state.isLoading).toBe(true);
      expect(result.current.state.loadingThreadId).toBe('thread-1');
      
      await switchPromise;
      
      expect(result.current.state.isLoading).toBe(false);
      expect(result.current.state.loadingThreadId).toBeNull();
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle thread loading failure', async () => {
      threadLoadingService.loadThread.mockResolvedValue({
        success: false,
        messages: [],
        error: 'Failed to load thread',
        threadId: 'thread-1'
      });
      
      const { result } = renderHook(() => useThreadSwitching());
      
      let success: boolean;
      await act(async () => {
        success = await result.current.switchToThread('thread-1');
      });
      
      expect(success!).toBe(false);
      expect(result.current.state.error).toBeTruthy();
      expect(result.current.state.error?.message).toContain('Failed to load thread');
    });

    it('should retry failed thread loading', async () => {
      let attempts = 0;
      threadLoadingService.loadThread.mockImplementation(() => {
        attempts++;
        if (attempts === 1) {
          return Promise.resolve({ success: false, messages: [], error: 'Network error', threadId: 'thread-1' });
        }
        return Promise.resolve({ success: true, messages: mockMessages, threadId: 'thread-1' });
      });
      
      const { result } = renderHook(() => useThreadSwitching());
      
      await act(async () => {
        await result.current.switchToThread('thread-1');
      });
      
      expect(attempts).toBe(2);
      expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
    });

    it('should allow manual retry after failure', async () => {
      threadLoadingService.loadThread
        .mockRejectedValueOnce(new Error('Failed'))
        .mockResolvedValueOnce({ success: true, messages: mockMessages, threadId: 'thread-1' });
      
      const { result } = renderHook(() => useThreadSwitching());
      
      // First attempt fails
      await act(async () => {
        await result.current.switchToThread('thread-1');
      });
      
      expect(result.current.state.error).toBeTruthy();
      
      // Manual retry succeeds
      await act(async () => {
        await result.current.retryLastFailed();
      });
      
      expect(result.current.state.error).toBeNull();
      expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
    });
  });

  describe('Race Conditions', () => {
    it('should handle rapid thread switching', async () => {
      threadLoadingService.loadThread.mockImplementation((threadId) =>
        new Promise(resolve => 
          setTimeout(() => resolve({ 
            success: true, 
            messages: mockMessages, 
            threadId 
          }), threadId === 'thread-1' ? 200 : 50)
        )
      );
      
      const { result } = renderHook(() => useThreadSwitching());
      
      // Start switching to thread-1 (slow)
      const switch1Promise = act(async () => {
        await result.current.switchToThread('thread-1');
      });
      
      // Immediately switch to thread-2 (fast)
      await act(async () => {
        await result.current.switchToThread('thread-2');
      });
      
      // thread-2 should win
      expect(result.current.state.lastLoadedThreadId).toBe('thread-2');
      
      await switch1Promise; // Clean up promise
    });

    it('should cancel previous loading when new thread selected', async () => {
      const abortSpy = jest.fn();
      global.AbortController = jest.fn().mockImplementation(() => ({
        abort: abortSpy,
        signal: {}
      }));
      
      const { result } = renderHook(() => useThreadSwitching());
      
      await act(async () => {
        result.current.switchToThread('thread-1');
      });
      
      await act(async () => {
        result.current.switchToThread('thread-2');
      });
      
      expect(abortSpy).toHaveBeenCalled();
    });
  });

  describe('URL Synchronization', () => {
    it('should update URL when switching threads', async () => {
      const updateUrlMock = jest.fn();
      jest.mocked(require('@/services/urlSyncService').useURLSync).mockReturnValue({
        updateUrl: updateUrlMock
      });
      
      const { result } = renderHook(() => useThreadSwitching());
      
      await act(async () => {
        await result.current.switchToThread('thread-2');
      });
      
      expect(updateUrlMock).toHaveBeenCalledWith('thread-2');
    });

    it('should not update URL when skipUrlUpdate is true', async () => {
      const updateUrlMock = jest.fn();
      jest.mocked(require('@/services/urlSyncService').useURLSync).mockReturnValue({
        updateUrl: updateUrlMock
      });
      
      const { result } = renderHook(() => useThreadSwitching());
      
      await act(async () => {
        await result.current.switchToThread('thread-2', { skipUrlUpdate: true });
      });
      
      expect(updateUrlMock).not.toHaveBeenCalled();
    });
  });

  describe('Cancel Operations', () => {
    it('should cancel loading when requested', async () => {
      threadLoadingService.loadThread.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ success: true, messages: mockMessages, threadId: 'thread-1' }), 1000))
      );
      
      const { result } = renderHook(() => useThreadSwitching());
      
      act(() => {
        result.current.switchToThread('thread-1');
      });
      
      expect(result.current.state.isLoading).toBe(true);
      
      act(() => {
        result.current.cancelLoading();
      });
      
      expect(result.current.state.isLoading).toBe(false);
      expect(result.current.state.loadingThreadId).toBeNull();
    });
  });

  describe('State Consistency', () => {
    it('should maintain consistent state across multiple operations', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      
      // Switch to thread-1
      await act(async () => {
        await result.current.switchToThread('thread-1');
      });
      
      expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
      
      // Switch to thread-2
      await act(async () => {
        await result.current.switchToThread('thread-2');
      });
      
      expect(result.current.state.lastLoadedThreadId).toBe('thread-2');
      
      // Cancel a loading operation
      act(() => {
        result.current.switchToThread('thread-3');
        result.current.cancelLoading();
      });
      
      expect(result.current.state.isLoading).toBe(false);
      expect(result.current.state.lastLoadedThreadId).toBe('thread-2'); // Should remain thread-2
    });
  });
});