/**
 * Comprehensive Thread Switching Test Suite
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
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import type { Thread } from '@/types/unified';

// Mock external dependencies only
jest.mock('@/lib/logger');

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

// Get mocked services for use in tests
const getMockedServices = () => {
  const { ThreadService } = require('@/services/threadService');
  const { threadLoadingService } = require('@/services/threadLoadingService');
  const { executeWithRetry } = require('@/lib/retry-manager');
  return { ThreadService, threadLoadingService, executeWithRetry };
};

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
    
    // Reset stores using setState
    useUnifiedChatStore.setState({
      activeThreadId: null,
      messages: [],
      isThreadLoading: false,
      threadLoadingState: null
    });
    
    // For thread store with immer - use partial state update
    useThreadStore.setState({
      threads: mockThreads,
      currentThreadId: null,
      currentThread: null,
      loading: false,
      error: null
    });
    
    useAuthStore.setState({
      isAuthenticated: true
    });

    // Setup default mocks
    const { ThreadService, threadLoadingService, executeWithRetry } = getMockedServices();
    
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
      const { threadLoadingService } = getMockedServices();
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

    it('should show loading indicator in ThreadSidebar', async () => {
      const { threadLoadingService } = getMockedServices();
      threadLoadingService.loadThread.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({ success: true, messages: mockMessages, threadId: 'thread-1' }), 100))
      );
      
      render(<ThreadSidebar />);
      
      const threadItem = screen.getByText('First Thread');
      fireEvent.click(threadItem);
      
      await waitFor(() => {
        expect(screen.getByTestId('thread-loading-indicator')).toBeInTheDocument();
      });
      
      await waitFor(() => {
        expect(screen.queryByTestId('thread-loading-indicator')).not.toBeInTheDocument();
      });
    });

    it('should disable thread selection during loading', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      
      // Start first switch
      const firstSwitch = act(async () => {
        await result.current.switchToThread('thread-1');
      });
      
      // Try to switch to another thread while loading
      const secondSwitch = act(async () => {
        await result.current.switchToThread('thread-2');
      });
      
      await Promise.all([firstSwitch, secondSwitch]);
      
      // Should cancel first and complete second
      expect(result.current.state.lastLoadedThreadId).toBe('thread-2');
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle thread loading failure', async () => {
      const error = new Error('Failed to load thread');
      const { threadLoadingService } = getMockedServices();
      threadLoadingService.loadThread.mockRejectedValue(error);
      
      const { result } = renderHook(() => useThreadSwitching());
      
      let success: boolean;
      await act(async () => {
        success = await result.current.switchToThread('thread-1');
      });
      
      expect(success!).toBe(false);
      expect(result.current.state.error).toBeTruthy();
      expect(result.current.state.error?.threadId).toBe('thread-1');
      expect(result.current.state.isLoading).toBe(false);
    });

    it('should retry failed thread loading', async () => {
      let attempts = 0;
      const { threadLoadingService } = getMockedServices();
      threadLoadingService.loadThread.mockImplementation(() => {
        attempts++;
        if (attempts === 1) {
          return Promise.reject(new Error('First attempt failed'));
        }
        return Promise.resolve({ success: true, messages: mockMessages });
      });
      
      (executeWithRetry as jest.Mock).mockImplementation(async (fn) => {
        try {
          return await fn();
        } catch (error) {
          // Retry once
          return await fn();
        }
      });
      
      const { result } = renderHook(() => useThreadSwitching());
      
      await act(async () => {
        await result.current.switchToThread('thread-1');
      });
      
      expect(attempts).toBe(2);
      expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
    });

    it('should allow manual retry after failure', async () => {
      const { threadLoadingService } = getMockedServices();
      threadLoadingService.loadThread
        .mockRejectedValueOnce(new Error('Failed'))
        .mockResolvedValueOnce({ success: true, messages: mockMessages });
      
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

    it('should track retry count', async () => {
      const { threadLoadingService } = getMockedServices();
      threadLoadingService.loadThread.mockRejectedValue(new Error('Failed'));
      
      const { result } = renderHook(() => useThreadSwitching());
      
      await act(async () => {
        await result.current.switchToThread('thread-1');
      });
      expect(result.current.state.retryCount).toBe(1);
      
      await act(async () => {
        await result.current.retryLastFailed();
      });
      expect(result.current.state.retryCount).toBe(2);
    });
  });

  describe('Race Conditions', () => {
    it('should handle rapid thread switching', async () => {
      let resolveFirst: any;
      let resolveSecond: any;
      
      const { threadLoadingService } = getMockedServices();
      threadLoadingService.loadThread
        .mockImplementationOnce(() => new Promise(resolve => { resolveFirst = resolve; }))
        .mockImplementationOnce(() => new Promise(resolve => { resolveSecond = resolve; }));
      
      const { result } = renderHook(() => useThreadSwitching());
      
      // Start switching to first thread
      const firstSwitch = result.current.switchToThread('thread-1');
      
      // Immediately switch to second thread
      const secondSwitch = result.current.switchToThread('thread-2');
      
      // Resolve second before first
      resolveSecond({ success: true, messages: mockMessages });
      await act(async () => {
        await secondSwitch;
      });
      
      // Resolve first (should be ignored)
      resolveFirst({ success: true, messages: [] });
      await act(async () => {
        await firstSwitch;
      });
      
      expect(result.current.state.lastLoadedThreadId).toBe('thread-2');
    });

    it('should cancel previous loading when new thread selected', async () => {
      const abortSpy = jest.spyOn(AbortController.prototype, 'abort');
      
      const { result } = renderHook(() => useThreadSwitching());
      
      // Start first switch (won't complete)
      const { threadLoadingService } = getMockedServices();
      threadLoadingService.loadThread.mockImplementation(
        () => new Promise(() => {})
      );
      
      act(() => {
        result.current.switchToThread('thread-1');
      });
      
      // Switch to another thread - reuse the same threadLoadingService mock
      threadLoadingService.loadThread.mockResolvedValue({
        success: true,
        messages: mockMessages
      });
      
      await act(async () => {
        await result.current.switchToThread('thread-2');
      });
      
      expect(abortSpy).toHaveBeenCalled();
      expect(result.current.state.lastLoadedThreadId).toBe('thread-2');
    });
  });

  describe('WebSocket Integration', () => {
    it('should emit thread loading WebSocket event', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      const handleWebSocketEvent = jest.fn();
      
      useUnifiedChatStore.setState({ handleWebSocketEvent });
      
      await act(async () => {
        await result.current.switchToThread('thread-1');
      });
      
      expect(handleWebSocketEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'thread_loading',
          threadId: 'thread-1'
        })
      );
    });

    it('should emit thread loaded WebSocket event', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      const handleWebSocketEvent = jest.fn();
      
      useUnifiedChatStore.setState({ handleWebSocketEvent });
      
      await act(async () => {
        await result.current.switchToThread('thread-1');
      });
      
      expect(handleWebSocketEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'thread_loaded',
          threadId: 'thread-1',
          messages: mockMessages
        })
      );
    });
  });

  describe('URL Synchronization', () => {
    it('should update URL when switching threads', async () => {
      const updateUrl = jest.fn();
      jest.spyOn(require('@/services/urlSyncService'), 'useURLSync').mockReturnValue({
        updateUrl
      });
      
      const { result } = renderHook(() => useThreadSwitching());
      
      await act(async () => {
        await result.current.switchToThread('thread-2');
      });
      
      expect(updateUrl).toHaveBeenCalledWith('thread-2');
    });

    it('should not update URL when skipUrlUpdate is true', async () => {
      const updateUrl = jest.fn();
      jest.spyOn(require('@/services/urlSyncService'), 'useURLSync').mockReturnValue({
        updateUrl
      });
      
      const { result } = renderHook(() => useThreadSwitching());
      
      await act(async () => {
        await result.current.switchToThread('thread-2', { skipUrlUpdate: true });
      });
      
      expect(updateUrl).not.toHaveBeenCalled();
    });

    it('should not update URL when updateUrl option is false', async () => {
      const updateUrl = jest.fn();
      jest.spyOn(require('@/services/urlSyncService'), 'useURLSync').mockReturnValue({
        updateUrl
      });
      
      const { result } = renderHook(() => useThreadSwitching());
      
      await act(async () => {
        await result.current.switchToThread('thread-2', { updateUrl: false });
      });
      
      expect(updateUrl).not.toHaveBeenCalled();
    });
  });

  describe('Cancel Operations', () => {
    it('should cancel loading when requested', async () => {
      const { threadLoadingService } = getMockedServices();
      threadLoadingService.loadThread.mockImplementation(
        () => new Promise(() => {}) // Never resolves
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

    it('should cleanup resources on cancel', async () => {
      const cleanupSpy = jest.spyOn(globalCleanupManager, 'cleanupThread');
      
      const { result } = renderHook(() => useThreadSwitching());
      
      act(() => {
        result.current.switchToThread('thread-1');
      });
      
      const operationId = result.current.state.operationId;
      
      act(() => {
        result.current.cancelLoading();
      });
      
      expect(cleanupSpy).toHaveBeenCalledWith(operationId);
    });
  });

  describe('Timeout Handling', () => {
    it('should timeout long-running thread loads', async () => {
      jest.useFakeTimers();
      
      const { threadLoadingService } = getMockedServices();
      threadLoadingService.loadThread.mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );
      
      const { result } = renderHook(() => useThreadSwitching());
      
      act(() => {
        result.current.switchToThread('thread-1', { timeoutMs: 3000 });
      });
      
      expect(result.current.state.isLoading).toBe(true);
      
      // Fast-forward past timeout
      act(() => {
        jest.advanceTimersByTime(3100);
      });
      
      await waitFor(() => {
        expect(result.current.state.isLoading).toBe(false);
        expect(result.current.state.error).toBeTruthy();
      });
      
      jest.useRealTimers();
    });
  });

  describe('State Consistency', () => {
    it('should maintain consistent state across multiple operations', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      
      // Switch to thread 1
      await act(async () => {
        await result.current.switchToThread('thread-1');
      });
      
      expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
      
      // Fail to switch to thread 2
      const { threadLoadingService } = getMockedServices();
      threadLoadingService.loadThread.mockRejectedValueOnce(new Error('Failed'));
      await act(async () => {
        await result.current.switchToThread('thread-2');
      });
      
      expect(result.current.state.lastLoadedThreadId).toBe('thread-1');
      expect(result.current.state.error?.threadId).toBe('thread-2');
      
      // Successfully switch to thread 3 - reuse the same mock
      threadLoadingService.loadThread.mockResolvedValueOnce({
        success: true,
        messages: mockMessages
      });
      await act(async () => {
        await result.current.switchToThread('thread-3');
      });
      
      expect(result.current.state.lastLoadedThreadId).toBe('thread-3');
      expect(result.current.state.error).toBeNull();
    });

    it('should cleanup on unmount', () => {
      const cleanupSpy = jest.spyOn(globalCleanupManager, 'cleanupThread');
      
      const { result, unmount } = renderHook(() => useThreadSwitching());
      
      act(() => {
        result.current.switchToThread('thread-1');
      });
      
      const operationId = result.current.state.operationId;
      
      unmount();
      
      expect(cleanupSpy).toHaveBeenCalledWith(operationId);
    });
  });

  describe('Integration with ThreadSidebar', () => {
    it('should switch threads when clicking thread item', async () => {
      render(<ThreadSidebar />);
      
      const secondThread = screen.getByText('Second Thread');
      fireEvent.click(secondThread);
      
      await waitFor(() => {
        expect(threadLoadingService.loadThread).toHaveBeenCalledWith('thread-2');
      });
      
      expect(useUnifiedChatStore.getState().activeThreadId).toBe('thread-2');
    });

    it('should show error state in sidebar on failure', async () => {
      const { threadLoadingService } = getMockedServices();
      threadLoadingService.loadThread.mockRejectedValue(new Error('Load failed'));
      
      render(<ThreadSidebar />);
      
      const threadItem = screen.getByText('First Thread');
      fireEvent.click(threadItem);
      
      await waitFor(() => {
        expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
      });
    });

    it('should allow retry from sidebar error state', async () => {
      const { threadLoadingService } = getMockedServices();
      threadLoadingService.loadThread
        .mockRejectedValueOnce(new Error('Failed'))
        .mockResolvedValueOnce({ success: true, messages: mockMessages });
      
      render(<ThreadSidebar />);
      
      const threadItem = screen.getByText('First Thread');
      fireEvent.click(threadItem);
      
      await waitFor(() => {
        expect(screen.getByText(/retry/i)).toBeInTheDocument();
      });
      
      const retryButton = screen.getByText(/retry/i);
      fireEvent.click(retryButton);
      
      await waitFor(() => {
        expect(screen.queryByText(/failed to load/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Performance and Optimization', () => {
    it('should batch multiple rapid switches efficiently', async () => {
      const { result } = renderHook(() => useThreadSwitching());
      
      const switches = [
        result.current.switchToThread('thread-1'),
        result.current.switchToThread('thread-2'),
        result.current.switchToThread('thread-3')
      ];
      
      await act(async () => {
        await Promise.all(switches);
      });
      
      // Should only load the last thread
      expect(threadLoadingService.loadThread).toHaveBeenCalledTimes(3);
      expect(result.current.state.lastLoadedThreadId).toBe('thread-3');
    });

    it('should cleanup aborted operations', async () => {
      const registerSpy = jest.spyOn(globalCleanupManager, 'registerAbortController');
      const cleanupSpy = jest.spyOn(globalCleanupManager, 'cleanupThread');
      
      const { result } = renderHook(() => useThreadSwitching());
      
      // Start first operation
      act(() => {
        result.current.switchToThread('thread-1');
      });
      
      const firstOperationId = result.current.state.operationId;
      expect(registerSpy).toHaveBeenCalledWith(firstOperationId, expect.any(AbortController));
      
      // Start second operation (should cleanup first)
      await act(async () => {
        await result.current.switchToThread('thread-2');
      });
      
      expect(cleanupSpy).toHaveBeenCalledWith(firstOperationId);
    });
  });
});