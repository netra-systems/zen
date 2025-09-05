/**
 * New Chat Transitions Test Suite
 * 
 * Comprehensive tests for new chat creation and thread switching
 * to ensure 10x more durability and prevent "bounce back" issues.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatSidebar } from '../ChatSidebar';
import { MainChat } from '../MainChat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ThreadOperationManager } from '@/lib/thread-operation-manager';
import { ThreadService } from '@/services/threadService';
import { useRouter } from 'next/navigation';

// Mock dependencies
jest.mock('@/store/unified-chat');
jest.mock('@/hooks/useWebSocket');
jest.mock('@/services/threadService');
jest.mock('next/navigation');
jest.mock('@/lib/thread-operation-manager');

describe('New Chat Transitions', () => {
  let mockStore: any;
  let mockWebSocket: any;
  let mockRouter: any;
  let mockThreadService: any;
  let mockOperationManager: any;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();

    // Setup mock store
    mockStore = {
      isProcessing: false,
      activeThreadId: null,
      messages: [],
      setActiveThread: jest.fn(),
      setThreadLoading: jest.fn(),
      startThreadLoading: jest.fn(),
      completeThreadLoading: jest.fn(),
      clearMessages: jest.fn(),
      handleWebSocketEvent: jest.fn()
    };
    (useUnifiedChatStore as jest.Mock).mockReturnValue(mockStore);

    // Setup mock WebSocket
    mockWebSocket = {
      sendMessage: jest.fn(),
      status: 'connected'
    };
    (useWebSocket as jest.Mock).mockReturnValue(mockWebSocket);

    // Setup mock router
    mockRouter = {
      push: jest.fn(),
      replace: jest.fn(),
      pathname: '/chat'
    };
    (useRouter as jest.Mock).mockReturnValue(mockRouter);

    // Setup mock ThreadService
    mockThreadService = {
      createThread: jest.fn().mockResolvedValue({ id: 'new-thread-123' }),
      loadThread: jest.fn().mockResolvedValue({ 
        success: true, 
        messages: [] 
      })
    };
    (ThreadService as any) = mockThreadService;

    // Setup mock ThreadOperationManager
    mockOperationManager = {
      startOperation: jest.fn(),
      isOperationInProgress: jest.fn().mockReturnValue(false),
      cancelCurrentOperation: jest.fn(),
      getCurrentOperation: jest.fn().mockReturnValue(null)
    };
    (ThreadOperationManager as any) = mockOperationManager;
  });

  describe('New Chat Creation', () => {
    it('should create new chat without bouncing back', async () => {
      // Setup operation manager to simulate successful creation
      mockOperationManager.startOperation.mockImplementation(
        async (type: string, threadId: string | null, executor: Function) => {
          const result = await executor({ aborted: false });
          return result;
        }
      );

      render(<ChatSidebar />);
      
      const newChatButton = screen.getByRole('button', { name: /new chat/i });
      
      await act(async () => {
        fireEvent.click(newChatButton);
      });

      await waitFor(() => {
        expect(mockThreadService.createThread).toHaveBeenCalled();
        expect(mockRouter.push).toHaveBeenCalledWith('/chat/new-thread-123');
      });

      // Verify no bounce back
      expect(mockStore.activeThreadId).toBe('new-thread-123');
      expect(mockRouter.push).toHaveBeenCalledTimes(1);
    });

    it('should prevent rapid double-clicks on new chat', async () => {
      // First click returns in-progress
      let clickCount = 0;
      mockOperationManager.startOperation.mockImplementation(async () => {
        clickCount++;
        if (clickCount === 1) {
          // First click proceeds
          return { success: true, threadId: 'new-thread-123' };
        }
        // Second click blocked
        return { success: false, error: new Error('Operation already in progress') };
      });

      render(<ChatSidebar />);
      
      const newChatButton = screen.getByRole('button', { name: /new chat/i });
      
      // Rapid double-click
      await act(async () => {
        fireEvent.click(newChatButton);
        fireEvent.click(newChatButton);
      });

      await waitFor(() => {
        expect(mockOperationManager.startOperation).toHaveBeenCalledTimes(2);
      });

      // Only one thread should be created
      expect(mockThreadService.createThread).toHaveBeenCalledTimes(1);
    });

    it('should handle new chat creation failure gracefully', async () => {
      mockOperationManager.startOperation.mockResolvedValue({
        success: false,
        error: new Error('Failed to create thread')
      });

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      render(<ChatSidebar />);
      
      const newChatButton = screen.getByRole('button', { name: /new chat/i });
      
      await act(async () => {
        fireEvent.click(newChatButton);
      });

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          'Failed to create new chat:',
          expect.any(Error)
        );
      });

      // Should not navigate on failure
      expect(mockRouter.push).not.toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    it('should cancel previous operation when forcing new chat', async () => {
      // Simulate ongoing operation
      mockOperationManager.isOperationInProgress.mockReturnValue(true);
      mockOperationManager.getCurrentOperation.mockReturnValue({
        type: 'switch',
        threadId: 'old-thread',
        status: 'running'
      });

      mockOperationManager.startOperation.mockImplementation(
        async (type, threadId, executor, options) => {
          if (options.force) {
            // Force should work
            return { success: true, threadId: 'new-thread-123' };
          }
          return { success: false, error: new Error('Operation in progress') };
        }
      );

      render(<ChatSidebar />);
      
      const newChatButton = screen.getByRole('button', { name: /new chat/i });
      
      await act(async () => {
        fireEvent.click(newChatButton);
      });

      await waitFor(() => {
        expect(mockOperationManager.startOperation).toHaveBeenCalledWith(
          'create',
          null,
          expect.any(Function),
          expect.objectContaining({ force: true })
        );
      });
    });
  });

  describe('Thread Switching', () => {
    it('should switch threads without bouncing back', async () => {
      const threadId = 'existing-thread-456';
      
      mockOperationManager.startOperation.mockResolvedValue({
        success: true,
        threadId
      });

      mockStore.activeThreadId = 'current-thread';

      render(<ChatSidebar />);
      
      // Simulate thread click
      const threadItem = screen.getByTestId(`thread-${threadId}`);
      
      await act(async () => {
        fireEvent.click(threadItem);
      });

      await waitFor(() => {
        expect(mockWebSocket.sendMessage).toHaveBeenCalledWith({
          type: 'switch_thread',
          payload: { thread_id: threadId }
        });
        expect(mockRouter.push).toHaveBeenCalledWith(`/chat/${threadId}`);
      });

      // Verify no bounce back
      expect(mockStore.setActiveThread).toHaveBeenCalledWith(threadId);
      expect(mockRouter.push).toHaveBeenCalledTimes(1);
    });

    it('should prevent switching to the same thread', async () => {
      const currentThreadId = 'current-thread';
      mockStore.activeThreadId = currentThreadId;

      render(<ChatSidebar />);
      
      const threadItem = screen.getByTestId(`thread-${currentThreadId}`);
      
      await act(async () => {
        fireEvent.click(threadItem);
      });

      // Should not trigger any operations
      expect(mockOperationManager.startOperation).not.toHaveBeenCalled();
      expect(mockWebSocket.sendMessage).not.toHaveBeenCalled();
    });

    it('should handle concurrent thread switches properly', async () => {
      let operationCount = 0;
      mockOperationManager.startOperation.mockImplementation(async () => {
        operationCount++;
        if (operationCount === 1) {
          // First operation takes time
          await new Promise(resolve => setTimeout(resolve, 100));
          return { success: true, threadId: 'thread-1' };
        }
        // Second operation queued
        return { success: true, threadId: 'thread-2' };
      });

      render(<ChatSidebar />);
      
      const thread1 = screen.getByTestId('thread-1');
      const thread2 = screen.getByTestId('thread-2');
      
      // Click both threads quickly
      await act(async () => {
        fireEvent.click(thread1);
        setTimeout(() => fireEvent.click(thread2), 10);
      });

      await waitFor(() => {
        expect(mockOperationManager.startOperation).toHaveBeenCalledTimes(2);
      });

      // Should end up on thread-2
      expect(mockStore.setActiveThread).toHaveBeenLastCalledWith('thread-2');
    });

    it('should retry failed thread switches', async () => {
      let attemptCount = 0;
      mockOperationManager.startOperation.mockImplementation(async () => {
        attemptCount++;
        if (attemptCount === 1) {
          // First attempt fails
          return { success: false, error: new Error('Network error') };
        }
        // Retry succeeds
        return { success: true, threadId: 'thread-123' };
      });

      render(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-123');
      
      await act(async () => {
        fireEvent.click(threadItem);
      });

      await waitFor(() => {
        expect(attemptCount).toBe(2);
        expect(mockStore.setActiveThread).toHaveBeenCalledWith('thread-123');
      });
    });
  });

  describe('Race Condition Prevention', () => {
    it('should handle URL changes during thread switch', async () => {
      mockOperationManager.startOperation.mockImplementation(
        async (type, threadId, executor) => {
          // Simulate URL change during execution
          mockRouter.pathname = `/chat/${threadId}`;
          const result = await executor({ aborted: false });
          return result;
        }
      );

      render(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-789');
      
      await act(async () => {
        fireEvent.click(threadItem);
      });

      await waitFor(() => {
        // Should complete without issues
        expect(mockStore.setActiveThread).toHaveBeenCalledWith('thread-789');
      });

      // Should not cause duplicate navigation
      expect(mockRouter.push).toHaveBeenCalledTimes(1);
    });

    it('should handle WebSocket events during transition', async () => {
      mockOperationManager.startOperation.mockImplementation(
        async (type, threadId, executor) => {
          // Simulate WebSocket event during transition
          mockStore.handleWebSocketEvent({
            type: 'thread_loaded',
            payload: { threadId: 'other-thread', messages: [] }
          });
          
          const result = await executor({ aborted: false });
          return result;
        }
      );

      render(<ChatSidebar />);
      
      const newChatButton = screen.getByRole('button', { name: /new chat/i });
      
      await act(async () => {
        fireEvent.click(newChatButton);
      });

      await waitFor(() => {
        // Should complete the new chat creation
        expect(mockThreadService.createThread).toHaveBeenCalled();
      });

      // Should end up on the new thread, not the WebSocket event thread
      expect(mockStore.setActiveThread).toHaveBeenLastCalledWith('new-thread-123');
    });

    it('should handle abort signals properly', async () => {
      mockOperationManager.startOperation.mockImplementation(
        async (type, threadId, executor) => {
          // Simulate abort during execution
          const result = await executor({ aborted: true });
          return result;
        }
      );

      render(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('thread-abc');
      
      await act(async () => {
        fireEvent.click(threadItem);
      });

      await waitFor(() => {
        expect(mockOperationManager.startOperation).toHaveBeenCalled();
      });

      // Should not complete the switch
      expect(mockStore.setActiveThread).not.toHaveBeenCalledWith('thread-abc');
    });
  });

  describe('State Synchronization', () => {
    it('should sync URL and state correctly', async () => {
      mockOperationManager.startOperation.mockResolvedValue({
        success: true,
        threadId: 'sync-thread-123'
      });

      render(<ChatSidebar />);
      
      const threadItem = screen.getByTestId('sync-thread-123');
      
      await act(async () => {
        fireEvent.click(threadItem);
      });

      await waitFor(() => {
        // State update should happen
        expect(mockStore.setActiveThread).toHaveBeenCalledWith('sync-thread-123');
        // URL update should happen
        expect(mockRouter.push).toHaveBeenCalledWith('/chat/sync-thread-123');
      });

      // Verify order - state before URL
      const setActiveThreadCall = mockStore.setActiveThread.mock.invocationCallOrder[0];
      const routerPushCall = mockRouter.push.mock.invocationCallOrder[0];
      expect(setActiveThreadCall).toBeLessThan(routerPushCall);
    });

    it('should maintain consistency during rapid transitions', async () => {
      const threads = ['thread-1', 'thread-2', 'thread-3'];
      let currentIndex = 0;

      mockOperationManager.startOperation.mockImplementation(async () => {
        const threadId = threads[currentIndex];
        currentIndex++;
        return { success: true, threadId };
      });

      render(<ChatSidebar />);
      
      // Rapid clicks on different threads
      for (const threadId of threads) {
        const threadItem = screen.getByTestId(threadId);
        await act(async () => {
          fireEvent.click(threadItem);
        });
      }

      await waitFor(() => {
        expect(mockOperationManager.startOperation).toHaveBeenCalledTimes(3);
      });

      // Should end up on the last thread
      expect(mockStore.setActiveThread).toHaveBeenLastCalledWith('thread-3');
      expect(mockRouter.push).toHaveBeenLastCalledWith('/chat/thread-3');
    });
  });
});